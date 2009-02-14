import logging
import os
import pickle
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext import db

from util.sessions import Session
from core.tool import ToolRegistration
from imsglobal.lticontext import LTI_Context

# Return our Registration
def register():
   return ToolRegistration(AdminHandler, "Administration Tool", 
     """This application allows you to administer this system.""")

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
    lti = LTI_Context(self, self.session);

    if ( lti.complete ) : return

    if lti.isAdmin() : return "HELLO MASTER"
    else: return "YOU ARE NOT ADMIN"
