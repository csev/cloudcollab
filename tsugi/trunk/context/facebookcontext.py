import logging
import cgi
import wsgiref.handlers
from datetime import datetime, timedelta
from google.appengine.ext import webapp
from google.appengine.api import memcache

from basecontext import BaseContext
import facebook

class Facebook_Context(BaseContext):
  dStr = ""
  request = None
  complete = False
  sessioncookie = False # Indicates if Cookies are working
  launch = None

  def __init__(self, web, lanuch = False, options = {}):
    # logging.info("Going for Facebook Context "+web.request.application_url+" path="+web.request.path+" url="+web.request.url);
    # logging.info(web.requestdebug(web))
    self.web = web
    self.request = web.request
    self.launch = None
    self.complete = False
    self.sessioncookie = False
    if launch:
        self.launch = launch
        return

    # Look for a signature
    if len(web.request.get("fb_sig_api_key")) < 1 or len(web.request.get("fb_sig_app_id")) < 1: return

    course_id = web.context_id
    org_id = "facebook.com";

    # No API Key - No Facebook
    api_key = memcache.get("facebook_api_key")
    secret_key = memcache.get("facebook_api_secret")
    if api_key == None or secret_key == None : return
    logging.info("Facebook Key found...");

    # Initialize the Facebook Object.
    self.facebookapi = facebook.Facebook(api_key, secret_key)
    logging.info("Facebook API..."+str(self.facebookapi));

    # Checks to make sure that the user is logged into Facebook.
    if self.facebookapi.check_session(self.request):
      pass
    else:
      # If not redirect them to your application add page.
      url = self.facebookapi.get_add_url()
      web.response.out.write('<fb:redirect url="' + url + '" />')
      self.complete = True
      return

    logging.info("Facebook Session found...");

   # Checks to make sure the user has added your application.
    if self.facebookapi.added:
      pass
    else:
      # If not redirect them to your application add page.
      url = self.facebookapi.get_add_url()
      web.response.out.write('<fb:redirect url="' + url + '" />')
      self.complete = True
      return

    logging.info("Facebook has been added found...");

    # Get the information about the user.
    facebook_user = self.facebookapi.users.getInfo( [self.facebookapi.uid], ['uid', 'name', 'birthday', 'relationship_status'])[0]

    # Display a welcome message to the user along with all the greetings.
    logging.info('Hello %s,<br>' % facebook_user['name'])

    logging.info("Facebook course_id="+str(course_id)+" org_id="+org_id);

    if course_id is False : 
      logging.info("Hacking Facebook bootstrap!")
      web.course_id = "12345"
      course_id = "12345"

    user_id = self.facebookapi.uid
    user_name = facebook_user['name'] 
    logging.info("Facebook userid = "+user_id)
    logging.info("Facebook name="+user_name)

    launch = { '_launch_type': 'facebook',
               'context_id': course_id,
               'context_label': 'FB201',
               'lis_person_name_full': user_name,
               'roles': 'Instructor',
               'oauth_consumer_key': 'facebook.edu',
               'tool_consumer_instance_description': 'University of Facebook',
               'user_id':  user_id}

    # We have made it to the point where we have handled this request
    self.launch = launch
    self.launchkey = '1234-facebook-567'
    memcache.set(self.launchprefix + self.launchkey, self.launch, 3600)
    logging.info("Creating Facebook Launch = "+ self.launchprefix + self.launchkey)

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
      web.response.out.write(web.requestdebug(web))
      web.response.out.write("\n</pre>\n")
      web.response.out.write("\n-->\n")

      if dig:
        dig.debug = self.dStr
        dig.put()

