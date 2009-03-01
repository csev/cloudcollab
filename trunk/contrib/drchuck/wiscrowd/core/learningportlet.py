import logging
import os
import pickle
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext import db
from core import portlet
from imsglobal.lticontext import LTI_Context

class LearningPortlet(portlet.Portlet):

  # Fix this with super later
  # def __init__(self):
    # self.context = False

  def establishContext(self):
    return True

  # TODO: extend the patent setup
  # For now a 100% override of the method
  def setup(self):

    self.super_setup()

    self.context = False
    if self.establishContext() : 
      self.context = LTI_Context(self, self.session);
      if ( self.context.complete ) : return False

    return True

  def getUrlParms(self) :
    retval = self.super_getUrlParms()
    if self.context != False and self.context.launch and not self.context.sessioncookie :
      retval['lti_launch_key'] = self.context.launch.key()
    return retval

  # To do call super
  def getFormFields(self) :
    ret = self.super_getFormFields()
    if self.context != False and self.context.launch and not self.context.sessioncookie :
      return ret + '<input type="hidden" name="lti_launch_key" value="%s">\n' % self.context.launch.key()
    else :
      return ret

