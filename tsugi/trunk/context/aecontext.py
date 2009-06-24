import logging
import urllib
from google.appengine.ext import db
from google.appengine.api import users

from contextmodel import *
from basecontext import BaseContext
from core.modelutil import *

class AE_Context(BaseContext):
  '''Build a launch from parameters.'''
  dStr = ''
  launch = None
  sessioncookie = True
  user = None
  course = None
  memb = None
  org = None
  request = None
  complete = False

  def __init__(self, request, params, session = False):
    self.request = request
    self.complete = False
    self.session = session
    # If the session came from a cookie, our URLs can be simpler
    self.sessioncookie = False
    if not self.session is False:
       self.sessioncookie = self.session.foundcookie
    self.buildlaunch(params)
    if not self.session is False:
       if not self.launch is None:
	  self.session["lti_launch_key"] = str(self.launch.key())

  def buildlaunch(self, params):
    course_id = params.get("course_id")
    user_id = params.get("user_id")
    org_id = params.get("org_id")
    role = params.get("user_role")

    org = None
    course = None
    user = None
    if len(org_id) > 0 :
      # org = LMS_Org.get_or_insert("key:"+org_id)
      org = opt_get_or_insert(LMS_Org,"key:"+org_id)
      Model_Load(org, params, "org_")
      org.put()

    if len(course_id) > 0 and org :
      # course = LMS_Course.get_or_insert("key:"+course_id, parent=org)
      course = opt_get_or_insert(LMS_Course,"key:"+course_id, parent=org)
      Model_Load(course, params, "course_")
      course.put()

    if ( len(user_id) > 0 ) and org :
      # user = LMS_User.get_or_insert("key:"+user_id, parent=org)
      user = opt_get_or_insert(LMS_User,"key:"+user_id, parent=org)
      Model_Load(user, params, "user_")
      user.put()

    memb = None
    if user and course :
      # memb = LMS_Membership.get_or_insert("key:"+user_id, parent=course)
      memb = opt_get_or_insert(LMS_Membership,"key:"+user_id, parent=course)
      if ( len(role) < 1 ) : role = "Student"
      role = role.lower()
      roleval = 1
      if ( role == "instructor") : roleval = 2
      if ( role == "administrator") : roleval = 2
      memb.role = roleval
      memb.put()

    # launch = LMS_Launch.get_or_insert("key:"+user_id, parent=course)
    launch = opt_get_or_insert(LMS_Launch,"key:"+user_id, parent=course)
    Model_Load(launch, params, "launch_")
    launch.memb = memb
    launch.org = org
    launch.user = user
    launch.course = course
    launch.put()
    self.debug("launch.key()="+str(launch.key()))

    self.complete = True
    self.launch = launch
    self.user = user
    self.course = course
    self.org = org
    self.memb = memb

