import logging
import os
import pickle
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext import db

from util.sessions import Session
from imsglobal.lti import Context
from core.tool import ToolRegistration

# Return our Registration
def register():
   return ToolRegistration('/admin', AdminHandler, "Administration Tool", """This application allows
you to administer this system.""")

class AdminHandler(webapp.RequestHandler):

  outStr = ""

  def get(self):
    istr = self.markup()
    if ( istr != None ) : self.response.out.write(istr)

  def post(self):
    istr = self.markup()
    if ( istr != None ) : self.response.out.write(istr)

  # This method returns tool output as a string
  def markup(self):
    self.session = Session()
    lti = Context(self, self.session);

    if ( lti.complete ) : return

    if lti.isAdmin() : print "HELLO MASTER"
