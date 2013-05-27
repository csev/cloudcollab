import logging
from google.appengine.api import memcache

from core import tool
from core import learningportlet

# Return our Registration
def register():
   return tool.ToolRegistration(LTI11Handler, 'LTI 1.1 Test Tool', 
     '''This tool shows how to Send a grade back via LTI 1.1.''')

class LTI11Handler(learningportlet.LearningPortlet):

  def establishContext(self):
    return True

  def update(self):
    return ( { 'hello': 'world', 'doaction' : self.action, 'thing': self.request.get('thing')  } )

  # Don't assume POST data will be here - only info
  def render(self, info):
    pathinfo = 'controller=%s doview.action=%s resource=%s<br/>\n' % (self.controller, self.action, self.resource)
    rendervars = { 'info' : info, 'user': self.context.getUserName(), 
                   'pathinfo': pathinfo, 
		   'anchortag': self.link_to('Click Me', attributes={'class' : 'selected' }, action='act-anchor' ),
                   'formtag': self.form_tag(attributes={'class' : 'selected' } , action='act-post' ),
                   'formcancel' : self.form_button('Cancel', attributes={'class' : 'selected' }, action='act-cancel' ),
    		   'formsubmit' : self.form_submit('GO') }

    # logging.info(self.context.dump())

    return self.doRender('index.htm', rendervars)
