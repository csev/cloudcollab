import logging
import cgi
import wsgiref.handlers
import logging
import hashlib
import base64
import uuid
import urllib
from datetime import datetime, timedelta
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.api import memcache

from basecontext import BaseContext
from core import oauth

class Google_Context(BaseContext):
  dStr = ""
  request = None
  complete = False
  sessioncookie = False # Indicates if Cookies are working
  launch = None
  user = None
  course = None
  memb = None
  org = None

  # We have several scenarios to handle
  def __init__(self, web, launch = False, options = {}):
    logging.info("Going for Google Context "+web.request.application_url+" path="+web.request.path+" url="+web.request.url);
    self.web = web
    self.request = web.request
    self.launch = None
    self.complete = False
    self.sessioncookie = False
    google_user = users.get_current_user()
    if launch:
        self.launch = launch

    if not google_user: return
    if web.context_id == False : return
    course_id = web.context_id
    org_id = "appengine.google.com";

    self.debug("course_id="+course_id+" org_id="+org_id);

    launch = { '_launch_type': 'google',
               'context_id': '456434513',
               'context_label': 'GOO201',
               'context_title': 'Design of Cloud Systems',
               'lis_person_contact_email_primary': google_user.email(),
               'lis_person_name_full': google_user.nickname(),
               'roles': 'Instructor',
               'oauth_consumer_key': 'google.edu',
               'tool_consumer_instance_description': 'University of Google',
               'tool_consumer_instance_guid': 'google.edu',
               'user_id':  google_user.email()}

    # We have made it to the point where we have handled this request
    self.launch = launch
    self.launchkey = '1234-goo-567'
    memcache.set(self.launchprefix + self.launchkey, self.launch, 3600)
    logging.info("Creating Google Launch = "+ self.launchprefix + self.launchkey)

  # It sure would be nice to have an error url to redirect to 
  def launcherror(self, web, dig, desc) :
      self.complete = True
      web.response.out.write("<p>\nIncorrect authentication data presented by the Learning Management System.\n</p>\n")
      web.response.out.write("<p>\nError code:\n</p>\n")
      web.response.out.write("<p>\n"+desc+"\n</p>\n")
      web.response.out.write("<!--\n")
  
      web.response.out.write("<pre>\nHTML Formatted Output(Test):\n\n")
      desc = cgi.escape(desc) 
      web.response.out.write(desc)
      web.response.out.write("\n\nDebug Log:\n")
      web.response.out.write(self.dStr)
      web.response.out.write("\nRequest Data:\n")
      web.response.out.write(self.requestdebug(web))
      web.response.out.write("\n</pre>\n")
      web.response.out.write("\n-->\n")

      if dig:
        dig.debug = self.dStr
        dig.put()

