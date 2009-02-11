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

class PrisonerHandler(webapp.RequestHandler):

  def get(self):
    self.post()

  def post(self):
    istr = self.markup()
    if istr != None:
      temp = os.path.join(os.path.dirname(__file__), 'templates/body.htm')
      outstr = template.render(temp, {'output' : istr} )
      self.response.out.write(outstr)

  def markup(self):
    self.session = Session()
    lti = Context(self, self.session);
    
    if ( lti.complete ) : return

    return "HELLO PRISONER"
