import logging
import os
import pickle
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import memcache

from util.sessions import Session
from imsglobal.lticontext import LTI_Context
from core import tool
from core import learningportlet

# Return our Registration
def register():
   return tool.ToolRegistration(SampleHandler, "Sample Tool", 
     """This tool shows how to build a simple Learning Portlet.""")

class SampleHandler(learningportlet.LearningPortlet):

  def doaction(self):
    return ( "This is some info")

  def getview(self, info):
    url = self.getPostPath()
    self.debug("New URL: "+url)
    ret = "Sample Output\n"
    ret = ret + self.getAnchorTag("Click Me", url, { 'class' : "selected" } ) + '\n'
    ret = ret + self.getFormTag(url, { 'class' : "selected" } ) + '\n'
    ret = ret + self.getFormFields() + '\n'
    ret = ret + self.getFormButton("Cancel", url, { 'class' : "selected" } ) + '\n'
    ret = ret + self.getFormSubmit("GO") + '\n'
    ret = ret + "</form>\n";
    ret = ret + "\n<pre>\n----   Debug Output ----\n"
    ret = ret + self.getDebug()
    ret = ret + "\n</pre>\n"
    
    return ret
