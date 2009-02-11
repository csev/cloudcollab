import logging
import os
import pickle
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import memcache

from util.sessions import Session
from imsglobal.lti import Context
from core.tool import ToolRegistration

# Return our Registration
def register():
   return ToolRegistration('/prisoner', PrisonerHandler, "Prisoner's Dilemma", """This 
application allows you to play the "Prisoner's Dilemma" game.""")

class GameState():
   def __init__(self, playercount=2):
     self.playercount = playercount
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

class PrisonerHandler(webapp.RequestHandler):

  outStr = ""

  def getmodel(self, lti):
    freekey = "Prisoner-"+str(lti.course.key())
    logging.info("Loading Free key="+freekey)
    freerider =  memcache.get(freekey)
    # If we changed the program ignore old things in the cache
    if freerider == None or not isinstance(freerider, GameState):
      freerider = GameState()
      memcache.add(freekey, freerider, 3600)
    return freerider

  def putmodel(self, freerider, lti):
    freekey = "Prisoner-"+str(lti.course.key())
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

    gm = self.getmodel(lti)
    if ( len(gm.players) < 4 ) :
      rendervars['joinaction'] = getactionpath(self,"join")

    temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
    outstr = template.render(temp, rendervars)
    return outstr

  # This method returns tool output as a string
  def markup(self):
    self.session = Session()
    lti = Context(self, self.session);
    
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
    gm = GameState()
    self.putmodel(gm, lti)
    msg = "Game gm reset"
    return self.mainscreen(lti, {'msg' : msg})

  def action_join(self,lti) :
    gm = self.getmodel(lti)

    if not lti.user.email or len(lti.user.email) < 1:
      msg = "You must have an E-Mail to play"
      return self.mainscreen(lti, {'msg' : msg})
    
    if lti.user.email in gm.players:
      msg = "You have already joined the game"
      return self.mainscreen(lti, {'msg' : msg})

    if len(gm.players) >= gm.playercount: 
      msg = "The game is closed - you can play next time"
      return self.mainscreen(lti, {'msg' : msg})

    gm.players.append(lti.user.email)
    gm.chips.append(20)
    gm.last.append( list () )

    # Let the game begin!
    if len(gm.players) >= gm.playercount: 
       gm.turn = 1
       gm.current = 0
       
    self.putmodel(gm, lti)

    msg = "Welcome to the game"
    return self.mainscreen(lti, {'msg' : msg})

  def action_play(self,lti) :
    gm = self.getmodel(lti)

    if gm.turn < 1 or gm.turn > 4: 
      msg = "The game is not running!"
      return self.mainscreen(lti, {'msg' : msg})
    if not lti.user.email in gm.players:
      msg = "You are not currently playing!"
      return self.mainscreen(lti, {'msg' : msg})
    if not lti.user.email == gm.players[gm.current] :
      msg = "It is not your turn!"
      return self.mainscreen(lti, {'msg' : msg})

    contrib = self.request.get('chips')
    try: contrib = int(contrib)
    except: contrib = -1
    
    if contrib > gm.chips[gm.current] : contrib = gm.chips[gm.current]

    if contrib < 0 :
      msg = "Please enter a real number"
      return self.mainscreen(lti, {'msg' : msg})

    gm.pot = gm.pot + contrib
    gm.chips[gm.current] = gm.chips[gm.current] - contrib
    gm.last[gm.current].append(contrib)
    gm.current = gm.current + 1
    if gm.current >= gm.playercount:
      gm.current = 0
      gm.turn = gm.turn + 1
      # Split the pot
      each = int((gm.pot * 1.6) / gm.playercount) 
      for i in range(len(gm.chips)):
        gm.chips[i] = gm.chips[i] + each
      gm.pot = 0

    self.putmodel(gm, lti)

    msg = "Thanks for your contribution!"
    return self.mainscreen(lti, {'msg' : msg})

  def action_messages(self,lti) :
    gm = self.getmodel(lti)

    me = None
    for i in range(len(gm.players)):
      if gm.players[i] == lti.user.email : 
         me = i

    r = "<pre>\n"

    if gm.turn > 0 and gm.turn < 5 and lti.user.email == gm.players[gm.current]:
      r = r + '<font color="red">It is your turn</font>\n\n'

    if gm.turn < 1:
      r = r + "Game has not started\n"
    elif gm.turn > 4:
      r = r + "Game completed\n"
    else:
      r = r + "GAME ON! Current turn: "+str(gm.turn)+"\n";

    r = r + "\n"
    if lti.user.email in gm.players and not lti.isInstructor() :
      r = r + "Your pot: "+str(gm.chips[me])+" Contribution History:"+str(gm.last[me])+"\n"
      r = r + "Players: "+str(len(gm.players))+"\n"
    else:
      r = r + "Current pot total: " + str(gm.pot) + "\n"
      for i in range(len(gm.players)):
         if gm.current == i :
           r = r + "===> "
         else:
           r = r + "     "
         r = r + "(" + str(gm.chips[i]) + " / " + str(gm.last[i]) + ") " + gm.players[i] + "\n"

    r = r + "</pre>\n"
    return r
