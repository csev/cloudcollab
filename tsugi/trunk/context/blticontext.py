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

class BLTI_Context(BaseContext):
  dStr = ""
  request = None
  complete = False
  sessioncookie = False # Indicates if Cookies are working

  # We have several scenarios to handle
  def __init__(self, web, launch = False, options = {}):
    self.web = web
    self.request = web.request
    self.options = options
    self.complete = False
    self.sessioncookie = False
    if launch:
        self.launch = launch
        return
    
    self.handlelaunch(web, self.options)

  def handlelaunch(self, web, options):
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

    # Copy the parameters as the launch data
    self.launchkey = str(uuid.uuid4())
    self.launch = dict(self.request.params)
    self.launch['_launch_type'] = 'basiclti'
    memcache.set(self.launchprefix + self.launchkey, self.launch, 3600)
    logging.info("Creating BasicLTI Launch = "+ self.launchprefix + self.launchkey)

  # It sure would be nice to have an error url to redirect to 
  def launcherror(self, web, dig, desc) :
      self.complete = True
      return_url = web.request.get("launch_presentation_return_url")
      if len(return_url) > 1 :
          desc = urllib.quote(desc) 
          if return_url.find('?') > 1 : 
              return_url = return_url + '&lti_errormsg=' + desc
          else :
              return_url = return_url + '?lti_errormsg=' + desc
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

  def getContextType() :
      return 'basiclti'

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

