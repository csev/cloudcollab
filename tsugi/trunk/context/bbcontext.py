import logging
import cgi
import wsgiref.handlers
import logging
import hashlib
import base64
import uuid
import urllib
from datetime import datetime, timedelta
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.api import memcache

from basecontext import BaseContext

class Blackboard_Context(BaseContext):
  dStr = ""
  request = None
  complete = False
  sessioncookie = False # Indicates if Cookies are working
  launch = None

  # We have several scenarios to handle
  def __init__(self, web, launch = False, options = {}):
    self.web = web
    self.request = web.request
    self.launch = None
    self.sessioncookie = False
    if launch:
        self.launch = launch
        return

    # Check for sanity - silently return
    action = web.request.get('tcbaseurl')
    if ( len(action) < 1 ) : return

    logging.info("We have a Blackboard... ");

    course_id = web.request.get("course_id")
    user_id = web.request.get('userid')
    nonce = web.request.get('nonce')
    if user_id == None or course_id == None or nonce is None:
      logging.info("Error missing userid, course_id, or nonce on bbproxy launch")
      return

    # parse ticket
    ticket = web.request.get("ticket")
    displayid = user_id
    if not ticket is None:
      wds = ticket.split(":")
      if len(wds) > 3 : displayid = wds[3]

    launch = { '_launch_type': 'blackboard',
               'context_id': course_id,
               'lis_person_name_full': displayid,
               'roles': 'Instructor',
               'oauth_consumer_key': 'proxy.blackboard.com',
               'tool_consumer_instance_description': 'University of Blackboard',
               'user_id':  user_id }

    # We have made it to the point where we have handled this request
    self.launch = launch
    self.launchkey = web.request.get("nonce")
    memcache.set(self.launchprefix + self.launchkey, self.launch, 3600)
    logging.info("Creating Blackboard Launch = "+ self.launchprefix + self.launchkey)

  # It sure would be nice to have an error url to redirect to 
  def launcherror(self, web, doHtml, doDirect, dig, desc) :
      self.complete = True
      if doDirect :
        web.response.out.write("<p>\nIncorrect authentication data presented by the Learning Management System.\n</p>\n")
        web.response.out.write("<p>\nError code:\n</p>\n")
        web.response.out.write("<p>\n"+desc+"\n</p>\n")
        web.response.out.write("<!--\n")
  
      respString = self.errorResponse(desc)
      if doDirect or doHtml:
        web.response.out.write("<pre>\nHTML Formatted Output(Test):\n\n")
        respString = cgi.escape(respString) 
      web.response.out.write(respString)
      if doDirect or doHtml:
        web.response.out.write("\n\nDebug Log:\n")
        web.response.out.write(self.dStr)
        web.response.out.write("\nRequest Data:\n")
        web.response.out.write(self.requestdebug(web))
        web.response.out.write("\n</pre>\n")
      if doDirect :
        web.response.out.write("\n-->\n")

      if dig:
        dig.debug = self.dStr
        dig.put()


'''  Note: Sample BB Launch
tcbaseurl http://bb9-localdev1.blackboard.com:80
tcrole INSTRUCTOR
role COURSE:INSTRUCTOR
userid _1_1
returnurl /webapps/blackboard/course/course_button.jsp?course_id=_3_1&family=cou
rse_tools_area
nonce 175b3a3afbb748b0be0b81b6e3f739c3
timestamp 1236953957784
mac oBF4Pnfg8t7fRDdQ2IEiXg==
ticket 1236953957784:189642b747614986927fd2091a68087e:_1_1:administrator:1236954
257784:9005A8657E18A675DAE23C63B5A8A948:5E45AFF9F4D519043F8F95636913A164
course_id _3_1
direction ltr
locale en_US
samplesetting_course_georgekey georgevalue
ourguid dbafedc0176c4bf2992ccb4001a80511
'''
