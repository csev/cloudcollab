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
   return ToolRegistration(FreeRiderHandler, "Free Rider", """This 
application allows you to play the "Free Rider" game as described by
James Surowiecki in the book "The Wisdom of Crowds".""")

class GameState():
   def __init__(self, playercount=2):
     self.playercount = playercount
     self.players = list()
     self.chips = list()
     self.last = list()
     self.turn = -1
     self.current = 0
     self.pot = 0

class FreeRiderHandler(webapp.RequestHandler):

  outStr = ""

  def getmodel(self, context):
    freekey = "FreeRider-"+str(context.course.key())
    logging.info("Loading Free key="+freekey)
    freerider =  memcache.get(freekey)
    # If we changed the program ignore old things in the cache
    if freerider == None or not isinstance(freerider, GameState):
      freerider = GameState()
      memcache.add(freekey, freerider, 3600)
    return freerider

  def putmodel(self, freerider, context):
    freekey = "FreeRider-"+str(context.course.key())
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
  def mainscreen(self, context, vars = { }):
    rendervars = {'context': context,
                  'messagesaction' : context.getGetPath("messages", direct=True), 
                  'playaction' : context.getGetPath("play"), 
                  'request': self.request}

    rendervars.update(vars)

    if context.isInstructor() : 
      rendervars['resetaction'] = context.getGetPath("reset")

    gm = self.getmodel(context)
    if ( len(gm.players) < 4 ) :
      rendervars['joinaction'] = context.getGetPath("join")

    temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
    outstr = template.render(temp, rendervars)
    return outstr

  # This method returns tool output as a string
  def markup(self):
    self.session = Session()
    context = Context(self, self.session);
    
    if ( context.complete ) : return

    # if we don't have a launch - we are not provisioned
    if ( not context.launch ) :
      temp = os.path.join(os.path.dirname(__file__), 'templates/nolti.htm')
      outstr = template.render(temp, { })
      return outstr

    (controller, action, resource) = context.parsePath()
    if action == "messages" : return self.action_messages(context)
    if action == "join" : return self.action_join(context)
    if action == "reset" : return self.action_reset(context)
    if action == "play" : return self.action_play(context)

    return self.mainscreen(context)

  def action_reset(self,context) :
    if not context.isInstructor() :
      msg = "Only the instructor can reset!"
      return self.mainscreen(context, {'msg' : msg})
    gm = GameState()
    self.putmodel(gm, context)
    msg = "Game reset"
    return self.mainscreen(context, {'msg' : msg})

  def action_join(self,context) :
    gm = self.getmodel(context)

    if not context.user.email or len(context.user.email) < 1:
      msg = "You must have an E-Mail to play"
      return self.mainscreen(context, {'msg' : msg})
    
    if context.user.email in gm.players:
      msg = "You have already joined the game"
      return self.mainscreen(context, {'msg' : msg})

    if len(gm.players) >= gm.playercount: 
      msg = "The game is closed - you can play next time"
      return self.mainscreen(context, {'msg' : msg})

    gm.players.append(context.user.email)
    gm.chips.append(20)
    gm.last.append( list () )

    # Let the game begin!
    if len(gm.players) >= gm.playercount: 
       gm.turn = 1
       gm.current = 0
       
    self.putmodel(gm, context)

    msg = "Welcome to the game"
    return self.mainscreen(context, {'msg' : msg})

  def action_play(self,context) :
    gm = self.getmodel(context)

    if gm.turn < 1 or gm.turn > 4: 
      msg = "The game is not running!"
      return self.mainscreen(context, {'msg' : msg})
    if not context.user.email in gm.players:
      msg = "You are not currently playing!"
      return self.mainscreen(context, {'msg' : msg})
    if not context.user.email == gm.players[gm.current] :
      msg = "It is not your turn!"
      return self.mainscreen(context, {'msg' : msg})

    contrib = self.request.get('chips')
    try: contrib = int(contrib)
    except: contrib = -1
    
    if contrib > gm.chips[gm.current] : contrib = gm.chips[gm.current]

    if contrib < 0 :
      msg = "Please enter a real number"
      return self.mainscreen(context, {'msg' : msg})

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

    self.putmodel(gm, context)

    msg = "Thanks for your contribution!"
    return self.mainscreen(context, {'msg' : msg})

  def action_messages(self,context) :
    gm = self.getmodel(context)

    me = None
    for i in range(len(gm.players)):
      if gm.players[i] == context.user.email : 
         me = i

    r = "<pre>\n"

    if gm.turn > 0 and gm.turn < 5 and context.user.email == gm.players[gm.current]:
      r = r + '<font color="red">It is your turn</font>\n\n'

    if gm.turn < 1:
      r = r + "Game has not started\n"
    elif gm.turn > 4:
      r = r + "Game completed\n"
    else:
      r = r + "GAME ON! Current turn: "+str(gm.turn)+"\n";

    r = r + "\n"
    if context.user.email in gm.players and not context.isInstructor() :
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
