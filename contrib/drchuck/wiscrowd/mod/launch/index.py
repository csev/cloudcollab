import logging
import os
import sys
import pickle
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext import db

from util.sessions import Session
from imsglobal.lticontext import LTI_Context
from core.tool import ToolRegistration

import cgi
from google.appengine.api import urlfetch
from mdom import *
import httplib, urllib
from  datetime import datetime, timedelta
import hashlib, base64
import uuid

# Return our Registration
def register():
   return ToolRegistration(LaunchHandler, "LTI Launcher", 
          """This application allows you to launch other LTI Resources.""")

class LaunchHandler(webapp.RequestHandler):

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
    context = LTI_Context(self, self.session);
    
    if ( context.complete ) : return

    # if we don't have a launch - we are not provisioned
    if ( not context.launch ) :
      temp = os.path.join(os.path.dirname(__file__), 'templates/nolti.htm')
      outstr = template.render(temp, { })
      return outstr

    rendervars = { 'context' : context }

    url = self.request.get('url')
    secret = self.request.get('secret')
    height = self.request.get('height')
    tool_id = self.request.get('tool_id')
    if len(tool_id) < 1 : tool_id = None
    try: height = int(height)
    except: height = 1200
    rendervars['height'] = height
    newwindow = self.request.get('newwindow')
    if newwindow and len(newwindow) > 0 : rendervars['newwindow'] = newwindow
    if not url or len(url) < 1 :
      temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
      outstr = template.render(temp, { })
      return outstr

    # Sending - Make a Simple TI TimeStamp
    tstime = datetime.utcnow()
    timestamp = tstime.strftime("%Y-%m-%dT%H:%M:%SZ")

    nonce = str(uuid.uuid4());
    presha1 = nonce + timestamp + secret
    sha1 =  hashlib.sha1()
    sha1.update(presha1)
    x = sha1.digest()
    digest = base64.b64encode(x)
    if context.isInstructor() :
      role = "Instructor"
    else:
      role = "Student"

    form_data = urllib.urlencode({
        'action': "launchresolve",
        'sec_nonce': nonce,
        'sec_created': timestamp,
        'sec_digest': digest,
        'user_id': str(context.user.key()),
        'user_role': role,
        'user_displayid': context.getUserName(),
        'user_email': context.user.email,
        'user_firstname': context.user.firstname,
        'user_lastname': context.user.lastname,
        'course_id': context.course.course_id,
        'course_title': context.course.title,
        'course_name': context.course.name,
        'launch_targets': "iframe",
        'launch_tool_id': tool_id } )

    detail = None
    result = None
    try:
      result = urlfetch.fetch(url=url,
                        payload=form_data,
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    except Exception :
      detail = sys.exc_info()

    if result and result.status_code == 200:
       map = mdom_parse(result.content)
       rurl = None
       if map : rurl = map.get("/launchResponse/launchUrl",None)
       if rurl != None:
          forward = self.request.get('forward')
          if forward != "":
             pos = rurl.find('?')
             if pos > 0 :
                rurl = rurl + '&'
             else :
                rurl = rurl + '?'
	     rurl = rurl + "forward=" + forward
	     rurl = rurl + "&cs_forward=" + forward
	     rurl = rurl + "&cs_course=" + course
          logging.info("Launching email="+context.user.email+" key="+str(context.user.key())+" url="+rurl)
          temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
          rendervars['launchurl'] = rurl
          outstr = template.render(temp, rendervars)
          return outstr

    data = "Failed web service call:\n" 
    data = data + "Launch URL:"+url+"\n"
    if result: data = data + "Response code="+str(result.status_code)+"\n" 
    if result: data = data + "Content:\n"+result.content+"\n" 
    data = data + "Form Data:\n"+form_data+"\n"
    data = data.replace("<","&lt;")
    data = data.replace(">","&gt;")
    if detail: 
      for line in detail:
         data = data + str(line) + '\n'

    temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
    rendervars['msg'] = 'Failed web service call'
    rendervars['data'] = data
    outstr = template.render(temp, rendervars)
    return outstr

