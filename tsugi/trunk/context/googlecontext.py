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
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import users

from contextmodel import *
from basecontext import BaseContext
from core import oauth
from core.modelutil import *

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

  # Option values
  Liberal = { 'nonce_time': 1000000, 
              'allow_digest_reuse': True,
              'digest_expire': timedelta(minutes=20), 
              'digest_cleanup_count' : 100,
              'launch_expire': timedelta(hours=1),
              'launch_cleanup_count': 100,
              'auto_create_orgs' : True,
              'default_org_secret' : "secret",
              'auto_create_courses' : True,
              'default_course_secret' : "secret"
            } 

  # We have several scenarios to handle
  def __init__(self, web, session = False, options = {}):
    logging.info("Going for Google Context "+web.request.application_url+" path="+web.request.path+" url="+web.request.url);
    self.web = web
    self.request = web.request
    self.launch = None
    self.complete = False
    self.sessioncookie = False
    google_user = users.get_current_user()
    if not google_user: return

    # Later set this to conservative
    if len(options) < 1 : self.options = self.Liberal
    self.handlelaunch(web, False, google_user, self.options)

  def handlelaunch(self, web, session, google_user, options):

    if web.context_id == False : return
    course_id = web.context_id
    org_id = "appengine.google.com";

    self.debug("course_id="+course_id+" org_id="+org_id);

    # Lets check to see if we have an organizational id and organizational secret
    # and check to see if we are really hearing from the organization
    org = LMS_Org.get_by_key_name("key:"+org_id)
    if not org :
      logging.info("Inserting Google Organization")
      org = opt_get_or_insert(LMS_Org,"key:"+org_id)
      org.name = "Google Accounts"
      org.title = "Google Accounts"
      org.url = "http://www.google.com/"
      org.put()

    self.org = org

    # Retrieve the standalone course
    course = LMS_Course.get_by_key_name("key:"+course_id)

    # Create new course if this is an admin user
    default_secret = options.get('default_course_secret', None)
    if users.is_current_user_admin() and (not course) and options.get('auto_create_courses', False) and (default_secret != None) :
      logging.warn("Creating course "+course_id+" with default secret")
      course = LMS_Course.get_or_insert("key:"+course_id)
      course.course_id = course_id
      course.secret = default_secret
      course.put()

    if not course:
       self.launcherror(web, None, "Unable to load course: "+course_id);
       return

    # Retrieve or make the user and link to either then organization or the course
    user = None
    user_id = google_user.email()
    if ( len(user_id) > 0 ) :
      user = opt_get_or_insert(LMS_User,"google:"+user_id)
      changed = False
      if user.email != google_user.email() :
        changed = True
        user.email = google_user.email() 
      if user.fullname != google_user.nickname() :
        changed = True
        user.fullname = google_user.nickname() 

      if changed : user.put()

    memb = None
    if ( not (user and course ) ) :
       self.launcherror(web, None, "Must have a valid user for a complete launch")
       return

    memb = opt_get_or_insert(LMS_Membership,"key:"+user_id, parent=course)
    roleval = 1
    if users.is_current_user_admin() : roleval = 2
    if memb.role != roleval :
      memb.role = roleval
      memb.put()

    # Clean up launches 
    nowtime = datetime.utcnow()
    before = nowtime - options.get('launch_expire', timedelta(days=2))
    self.debug("Delete launches since "+before.isoformat())

    q = db.GqlQuery("SELECT * FROM LMS_Launch WHERE created < :1", before)
    results = q.fetch(options.get('launch_cleanup_count', 100))
    db.delete(results)

    # TODO: Think about efficiency here
    launch = opt_get_or_insert(LMS_Launch,"key:"+user_id, parent=course)
    launch.memb = memb
    launch.org = org
    launch.user = user
    launch.course = course
    launch.type = "google"
    launch.put()
    self.debug("launch.key()="+str(launch.key()))
 
    # We have made it to the point where we have handled this request
    self.launch = launch
    self.setvars()

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

