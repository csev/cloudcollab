import logging
import os
import pickle
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import memcache

from util.sessions import Session
from imsglobal.lti import LTI

playercount = 2

# Move this to LMS
class ToolRegistration():

  def __init__(self,path,handler,title,desc):
    self.path = path
    self.handler = handler
    self.title = title
    self.desc = desc

# Return our Registration
def freerider():
   return ToolRegistration('/freerider', FreeRiderHandler, "Free Rider", """This 
application allows you to play the "Free Rider" game as described by
James Surowiecki in the book "The Wisdom of Crowds".""")

class GameState():
   def __init__(self):
     self.players = list()
     self.chips = list()
     self.last = list()
     self.turn = -1
     self.current = 0
     self.pot = 0

def getactionpath(self, action="", forajax=False):
  basepath = "/freerider"
  str = self.request.path
  pos = str.find(basepath)
  newpath = str[0:pos+len(basepath)].strip()
  if len(action.strip()) > 0 :
    newpath = newpath + "/" + action
  if forajax : newpath = newpath.replace("/portal/","/")
  logging.info("New Path="+newpath)
  return newpath

def getaction(self):
  basepath = "/freerider"
  str = self.request.path
  pos = str.find(basepath)
  try: action = str[pos+len(basepath)+1:].strip()
  except: action = ""
  logging.info("Action="+action)
  return action

class FreeRiderHandler(webapp.RequestHandler):

  outStr = ""

  def getmodel(self, lti):
    freekey = "FreeRider-"+str(lti.course.key())
    logging.info("Loading Free key="+freekey)
    freerider =  memcache.get(freekey)
    if freerider == None:
      freerider = GameState()
      memcache.add(freekey, freerider, 3600)
    return freerider

  def putmodel(self, freerider, lti):
    freekey = "FreeRider-"+str(lti.course.key())
    logging.info("Storing Free key="+freekey)
    memcache.replace(freekey, freerider, 3600)

  def get(self):
    self.post()

  def post(self):
    istr = self.markup()
    if istr != None:
      temp = os.path.join(os.path.dirname(__file__), 'templates/body.htm')
      outstr = template.render(temp, {'output' : istr} )
      self.response.out.write(outstr)

  # All your base are belong to us!
  def mainscreen(self, lti, vars = { }):
    rendervars = {'username': lti.user.email, 
                  'course': lti.getCourseName(), 
                  'messagesaction' : getactionpath(self,"messages", True), 
                  'playaction' : getactionpath(self,"play"), 
                  'request': self.request}
    rendervars.update(vars)

    if lti.isInstructor() : 
      rendervars['resetaction'] = getactionpath(self,"reset")
      rendervars['instructor'] = "yes"

    data = self.getmodel(lti)
    if ( len(data.players) < 4 ) :
      rendervars['joinaction'] = getactionpath(self,"join")

    temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
    outstr = template.render(temp, rendervars)
    return outstr

  # This method returns tool output as a string
  def markup(self):
    self.session = Session()
    lti = LTI(self, self.session);
    
    if ( lti.complete ) : return

    # if we don't have a launch - we are not provisioned
    if ( not lti.launch ) :
      temp = os.path.join(os.path.dirname(__file__), 'templates/nolti.htm')
      outstr = template.render(temp, { })
      return outstr

    action = getaction(self)
    if action == "messages" : return self.action_messages(lti)
    if action == "join" : return self.action_join(lti)
    if action == "reset" : return self.action_reset(lti)
    if action == "play" : return self.action_play(lti)

    return self.mainscreen(lti)

  def action_reset(self,lti) :
    if not lti.isInstructor() :
      msg = "Only the instructor can reset!"
      return self.mainscreen(lti, {'msg' : msg})
    data = GameState()
    logging.info("Data = "+str(data))
    self.putmodel(data, lti)
    msg = "Game data reset"
    return self.mainscreen(lti, {'msg' : msg})

  def action_join(self,lti) :
    data = self.getmodel(lti)

    if not lti.user.email or len(lti.user.email) < 1:
      msg = "You must have an E-Mail to play"
      return self.mainscreen(lti, {'msg' : msg})
    
    if lti.user.email in data.players:
      msg = "You have already joined the game"
      return self.mainscreen(lti, {'msg' : msg})

    if len(data.players) >= playercount: 
      msg = "The game is closed - you can play next time"
      return self.mainscreen(lti, {'msg' : msg})

    data.players.append(lti.user.email)
    data.chips.append(20)
    data.last.append( list () )

    # Let the game begin!
    if len(data.players) >= playercount: 
       data.turn = 1
       data.current = 0
       
    self.putmodel(data, lti)

    msg = "Welcome to the game"
    return self.mainscreen(lti, {'msg' : msg})

  def action_play(self,lti) :
    data = self.getmodel(lti)

    if data.turn < 1 or data.turn > 4: 
      msg = "The game is not running!"
      return self.mainscreen(lti, {'msg' : msg})
    if not lti.user.email in data.players:
      msg = "You are not currently playing!"
      return self.mainscreen(lti, {'msg' : msg})
    if not lti.user.email == data.players[data.current] :
      msg = "It is not your turn!"
      return self.mainscreen(lti, {'msg' : msg})

    contrib = self.request.get('chips')
    try: contrib = int(contrib)
    except: contrib = -1
    
    if contrib > data.chips[data.current] : contrib = data.chips[data.current]

    if contrib < 0 :
      msg = "Please enter a real number"
      return self.mainscreen(lti, {'msg' : msg})

    data.pot = data.pot + contrib
    data.chips[data.current] = data.chips[data.current] - contrib
    data.last[data.current].append(contrib)
    data.current = data.current + 1
    if data.current >= playercount:
      data.current = 0
      data.turn = data.turn + 1
      # Split the pot
      each = int((data.pot * 1.6) / playercount) 
      for i in range(len(data.chips)):
        data.chips[i] = data.chips[i] + each
      data.pot = 0

    self.putmodel(data, lti)

    msg = "Thanks for your contribution!"
    return self.mainscreen(lti, {'msg' : msg})

  def action_messages(self,lti) :
    data = self.getmodel(lti)

    me = None
    for i in range(len(data.players)):
      if data.players[i] == lti.user.email : 
         me = i

    r = "<pre>\n"

    if data.turn > 0 and data.turn < 5 and lti.user.email == data.players[data.current]:
      r = r + '<font color="red">It is your turn</font>\n\n'

    if data.turn < 1:
      r = r + "Game has not started\n"
    elif data.turn > 4:
      r = r + "Game completed\n"
    else:
      r = r + "GAME ON! Current turn: "+str(data.turn)+"\n";

    r = r + "\n"
    if lti.user.email in data.players and not lti.isInstructor() :
      r = r + "Your pot: "+str(data.chips[me])+" Contribution History:"+str(data.last[me])+"\n"
      r = r + "Players: "+str(len(data.players))+"\n"
    else:
      r = r + "Current pot total: " + str(data.pot) + "\n"
      for i in range(len(data.players)):
         if data.current == i :
           r = r + "===> "
         else:
           r = r + "     "
         r = r + "(" + str(data.chips[i]) + " / " + str(data.last[i]) + ") " + data.players[i] + "\n"

    r = r + "</pre>\n"
    return r
