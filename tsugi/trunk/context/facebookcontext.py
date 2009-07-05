import logging
import cgi
import wsgiref.handlers
from datetime import datetime, timedelta
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import memcache

from contextmodel import *
from basecontext import BaseContext
import facebook
from core.modelutil import *

class Facebook_Context(BaseContext):
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

  def __init__(self, web, session = False, options = {}):
    logging.info("Going for Facebook Context "+web.request.application_url+" path="+web.request.path+" url="+web.request.url);
    self.web = web
    self.request = web.request
    self.launch = None
    self.complete = False
    self.sessioncookie = False

    # Must have path based course id
    if web.context_id == False : return
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
      ## url = self.facebookapi.get_add_url()
      ## web.response.out.write('<fb:redirect url="' + url + '" />')
      ## self.complete = True
      # For now if you are not logged in...  We do not care
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

    # logging.info("<pre>\n"+self.requestdebug()+"</pre>")

    logging.info("Facebook course_id="+course_id+" org_id="+org_id);

    # Lets check to see if we have an organizational id and organizational secret
    # and check to see if we are really hearing from the organization
    org = LMS_Org.get_by_key_name("key:"+org_id)
    if not org :
      logging.info("Inserting Facebook Organization")
      org = opt_get_or_insert(LMS_Org,"key:"+org_id)
      org.name = "Facebook Accounts"
      org.title = "Facebook Accounts"
      org.url = "http://www.facebook.com/"
      org.put()

    self.org = org

    # Retrieve the standalone course - No creation until we know which
    # Facebook Users are admins or have site.new
    course = LMS_Course.get_by_key_name("key:"+course_id)
    if not course:
       self.launcherror(web, None, "Unable to load course: "+course_id);
       return

    # Retrieve or make the user and link to either then organization or the course
    user = None
    user_id = self.facebookapi.uid
    user_name = facebook_user['name'] + ' (Facebook)'
    logging.info("Facebook userid = "+user_id)
    logging.info("Facebook name="+user_name)
    if ( len(user_id) > 0 ) :
      user = opt_get_or_insert(LMS_User,"facebook:"+user_id)
      changed = False
      if user.fullname != user_name :
        changed = True
        user.fullname = user_name

      if changed : user.put()

    memb = None
    if ( not (user and course ) ) :
       self.launcherror(web, None, "Must have a valid user for a complete launch")
       return

    memb = opt_get_or_insert(LMS_Membership,"key:"+user_id, parent=course)
    roleval = 1
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
    launch = opt_get_or_insert(LMS_Launch,"facebook:"+user_id, parent=course)
    launch.memb = memb
    launch.org = org
    launch.user = user
    launch.course = course
    launch.launch_type = "facebook"
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

