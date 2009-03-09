import logging
from google.appengine.api import memcache

from core import tool
from core import learningportlet

# Return our Registration
def register():
   return tool.ToolRegistration(SampleHandler, "Sample Tool", 
     """This tool shows how to build a simple Learning Portlet which supports AJAX.""")

class SampleHandler(learningportlet.LearningPortlet):

  def establishContext(self):
    return True

  def doaction(self):
    return ( { 'infox': 'hello', 'thing': self.request.get('thing')  } )

  # Don't assume POST data will be here - only info
  def getview(self, info):
    pathinfo = "controller=%s action=%s resource=%s<br/>\n" % (self.controller, self.action, self.resource)
    rendervars = { 'info' : info, 'user': self.context.getUserName(), 
                   'pathinfo': pathinfo, 
		   'anchortag': self.getAnchorTag("Click Me", { 'class' : "selected" }, action="act-anchor" ),
                   'formtag': self.getFormTag({ 'class' : "selected" } , action="act-post" ),
                   'formcancel' : self.getFormButton("Cancel", { 'class' : "selected" }, action="act-cancel" ),
    		   'formsubmit' : self.getFormSubmit('GO') }

    # logging.info(self.context.dump())

    return self.doRender('index.htm', rendervars)
