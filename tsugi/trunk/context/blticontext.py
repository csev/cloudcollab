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

class BLTI_Context(BaseContext):
  dStr = ""
  request = None
  complete = False
  sessioncookie = False # Indicates if Cookies are working
  launch = None
  user = None
  course = None
  memb = None
  org = None
  # Patches to the model mapping from request values to 
  # model values
  user_mapping = {
    'lis_person_name_given': 'givenname',
    'lis_person_name_family': 'familyname',
    'lis_person_name_full': 'fullname',
    'lis_person_contact_email_primary': 'email',
    'lis_person_sourced_id': 'sourced_id'}

  org_mapping = {
    'tool_consumer_instance_guid': 'org_id',
    'tool_consumer_instance_name': 'name',
    'tool_consumer_instance_description': 'title'}


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
    self.web = web
    self.request = web.request
    self.launch = None
    self.complete = False
    self.sessioncookie = False
    # Later set this to conservative
    if len(options) < 1 : self.options = self.Liberal
    self.handlelaunch(web, session, self.options)

  def handlelaunch(self, web, session, options):
    # Check for sanity - silently return
    version = web.request.get('lti_version')
    if ( len(version) < 1 ) : return

    course_id = web.request.get("context_id")
    if isinstance(web.context_id, str) :
      logging.info("BasicLTI taking course_id from context_id");
      course_id = web.context_id

    user_id = web.request.get("user_id")
    oauth_key = web.request.get("oauth_consumer_key")
    urlpath = web.request.path

    if len(oauth_key) <= 0 or len(user_id) <= 0 or len(course_id) <= 0 : 
      self.launcherror(web, None, "Missing one of context_id, user_id, oauth_consumer_key")
      return

    self.debug("Running on " + web.request.application_url)

    # Do OAuth Here
    self.oauth_server = oauth.OAuthServer(LTI_OAuthDataStore(web, options))
    self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_PLAINTEXT())
    self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_HMAC_SHA1())

    params = self.request.params

    logging.info(self.request.url)
    # construct the oauth request from the request parameters
    oauth_request = oauth.OAuthRequest.from_request("POST", self.request.url, headers=self.request.headers, parameters=params)

    # verify the request has been oauth authorized
    try:
        logging.debug(self.requestdebug(web))
        consumer, token, params = self.oauth_server.verify_request(oauth_request)
    except oauth.OAuthError, err:
        logging.info(err)
        self.launcherror(web, None, "OAuth Security Validation failed:"+err.message)
    	return

    org_id = web.request.get("tool_consumer_instance_guid")
    org_secret = False
    if len(org_id) > 0 and oauth_key.startswith("basiclti-lms:") :
      org_secret = True

    # Lets check to see if we have an organizational id and organizational secret
    # and check to see if we are really hearing from the organization
    org = None
    if org_secret and len(org_id) > 0 :
      org = LMS_Org.get_by_key_name("key:"+org_id)
      if not org :
        self.launcherror(web, None, "Could not find organization:"+org_id)
        return
      # Check to see if we got any new data from the organization
      if Model_Load(org, web.request.params, None, self.org_mapping) :
        org.put()

    self.org = org

    # Retrieve the organization's course or standalone course
    if org and org_secret :
      course = LMS_Course.get_by_key_name("key:"+course_id, parent=org)
    else:
      course = LMS_Course.get_by_key_name("key:"+course_id)

    # Create new course if configured
    default_secret = options.get('default_course_secret', None)
    if (not course) and options.get('auto_create_courses', False) and (default_secret != None) :
      logging.warn("Creating course "+course_id+" in organization "+org_id+" with default secret")
      course = LMS_Course.get_or_insert("key:"+course_id, parent=org)
      if Model_Load(course, self.web.request.params, "context_") :
        course.course_id = course_id
        course.secret = default_secret
        course.put()

      if org : 
        self.debug("Linking OrgCourse="+course_id+" to org="+str(org.key()))
        orgcourse = opt_get_or_insert(LMS_OrgCourse,"key:"+course_id, parent=org)
        orgcourse.course = course
        orgcourse.put()
    elif course :
      secret = course.secret  
      if Model_Load(course, self.web.request.params, "context_") :
        course.secret = secret
        course.put()

    if not course:
       self.launcherror(web, None, "Unable to load course: "+course_id);
       return

    # Retrieve or make the user and link to either then organization or the course
    user = None
    course_user = False
    if ( len(user_id) > 0 ) :
      if org:
        user = opt_get_or_insert(LMS_User,"key:"+user_id, parent=org)
      else :
        user = opt_get_or_insert(LMS_CourseUser,"key:"+user_id, parent=course)
        user.course = course
        course_user = True

      if Model_Load(user, web.request.params, None, self.user_mapping) :
        user.put()

    memb = None
    if ( not (user and course ) ) :
       self.launcherror(web, None, "Must have a valid user for a complete launch")
       return

    memb = opt_get_or_insert(LMS_Membership,"key:"+user_id, parent=course)
    roles = web.request.get("roles")
    if ( len(roles) < 1 ) : roles = "Student"
    roles = roles.lower()
    roleval = 1
    if roles.find("instructor") >= 0 : roleval = 2
    if roles.find("administrator") >=0  : roleval = 2
    memb.role = roleval
    memb.put()

    # One more data structure to build - if we don't have an 
    # organization and we have some organizational data - 
    # we stash it under the course.
 
    course_org = False
    if not org and len(org_id) > 0 :
      # org = LMS_CourseOrg.get_or_insert("key:"+org_id, parent=course)
      org = opt_get_or_insert(LMS_CourseOrg,"key:"+org_id, parent=course)
      org.course = course
      course_org = True
      if Model_Load(org, web.request.params, None, self.org_mapping) :
        org.put()

    # Clean up launches 
    nowtime = datetime.utcnow()
    before = nowtime - options.get('launch_expire', timedelta(days=2))
    self.debug("Delete launches since "+before.isoformat())

    q = db.GqlQuery("SELECT * FROM LMS_Launch WHERE created < :1", before)
    results = q.fetch(options.get('launch_cleanup_count', 100))
    db.delete(results)

    launch = opt_get_or_insert(LMS_Launch,"basiclti:"+user_id, parent=course)
    Model_Load(launch, web.request.params, "launch_")
    launch.memb = memb
    if course_org:
      launch.course_org = org
    else:
      launch.org = org
    if course_user:
      launch.course_user = user
    else:
      launch.user = user

    launch.course = course
    launch.launch_type = "basiclti"
    launch.put()
    self.debug("launch.key()="+str(launch.key()))

    url = web.request.application_url+urlpath

    if ( url.find('?') >= 0 ) :
      url = url + "?"
    else :
      url = url + "?"

    url = url + urllib.urlencode({"lti_launch_key" : str(launch.key())})

    self.debug("url = "+url)
    url = url.replace("&", "&amp;")
 
    # We have made it to the point where we have handled this request
    self.complete = True
    self.launch = launch
    self.user = user
    self.course = course
    self.org = org
    self.memb = memb

    if session != False: session['lti_launch_key'] = str(launch.key())
    web.redirect(url)

  # It sure would be nice to have an error url to redirect to 
  def launcherror(self, web, dig, desc) :
      self.complete = True
      return_url = web.request.get("launch_presentation_return_url")
      if len(return_url) > 1 :
          desc = urllib.quote(desc) 
          if return_url.find('?') > 1 : 
              return_url = return_url + '&lti_msg=' + desc
          else :
              return_url = return_url + '?lti_msg=' + desc
          web.redirect(return_url)
          return

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


class LTI_OAuthDataStore(oauth.OAuthDataStore):

    def __init__(self, web, options):
        self.web = web
        self.options = options

    def lookup_consumer(self, key):
        if key.startswith('basiclti-lms:') :
            org_id = key[len('basiclti-lms:') :]
            logging.info("lookup_consumer org_id="+org_id)
            if org_id == "umich.edu" : return oauth.OAuthConsumer(key, "secret");
	elif key == "12345" : return oauth.OAuthConsumer(key, "secret");

        logging.info("Did not find consumer "+key)
        return None

    # We don't do request_tokens
    def lookup_token(self, token_type, token):
        return oauth.OAuthToken(None, None)

    # Trust all nonces
    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        return None

    # We don't do request_tokens
    def fetch_request_token(self, oauth_consumer):
        return None

    # We don't do request_tokens
    def fetch_access_token(self, oauth_consumer, oauth_token):
        return None

    # We don't do request_tokens
    def authorize_request_token(self, oauth_token, user):
        return None
