import logging
import os
import pickle
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext import db
from core import portlet
from context.slticontext import SLTI_Context
from context.blticontext import BLTI_Context
from util.sessions import Session

class LearningPortlet(portlet.Portlet):

  def __init__(self):
    portlet.Portlet.__init__(self)
    self.context = False

  def establishContext(self):
    return True

  def setup(self):

    portlet.Portlet.setup(self)

    self.context = False
    if self.establishContext() : 
      # Insist on a session
      if self.session is None: self.session = Session()
      self.context = BLTI_Context(self, self.session);
      if ( self.context.complete ) : return False

    return True

  def getUrlParms(self) :
    retval = portlet.Portlet.getUrlParms(self)
    if self.context != False and self.context.launch and not self.context.sessioncookie :
      retval['lti_launch_key'] = self.context.launch.key()
    return retval

  def getFormFields(self) :
    ret = portlet.Portlet.getFormFields(self)
    if self.context != False and self.context.launch and not self.context.sessioncookie :
      return ret + '<input type="hidden" name="lti_launch_key" value="%s">\n' % self.context.launch.key()
    else :
      return ret

