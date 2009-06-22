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
from context import Context
from core.modelutil import *

class LTI_Context(Context):
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
    self.web = web
    self.request = web.request
    self.launch = None
    self.sessioncookie = False
    # Later set this to conservative
    if len(options) < 1 : options = self.Liberal
    self.handlebbproxy(web, session, options)
    if ( self.complete ) : return
    self.handlelaunch(web, session, options)
    if ( self.complete ) : return
    self.handlesetup(web, session, options)

  # TODO - Move this to context???
  def handlesetup(self, web, session, options):
    # get values form the request
    key = web.request.get('lti_launch_key')
    if ( len(key) <= 0 ) : key = None

    sesskey = None
    self.sessioncookie = False
    if session != False:
      sesskey = session.get('lti_launch_key', None)
      if key and sesskey and key == sesskey:
        self.sessioncookie = True
        # logging.info("Session and URL Key Match cookies are working...")
      elif sesskey and not key:
        self.sessioncookie = True
        key = sesskey
        # logging.info("Taking key from session ...")

    # On a normal request there are no parammeters - we just use session
    if ( key ) :
      # Need try/except in case Key() is unhappy with the string
      try:
        launch = LTI_Launch.get(db.Key(key))
      except:
        launch = None

      if launch:
        if session != False: session['lti_launch_key'] = key
        # logging.info("Placing in session: %s" % key)
      else:
        logging.info("Session not found in store "+key)
        if session != False and sesskey : del(session['lti_launch_key'])

      self.launch = launch
      self.setvars()
      return

    self.launch = None
    self.setvars()

  def handlelaunch(self, web, session, options):
    # Check for sanity - silently return
    action = web.request.get('action')
    if ( len(action) < 1 ) : action = web.request.get("lti_action")
    if ( len(action) < 1 ) : return
    action = action.lower()
    if action != 'launchresolve' and action != 'direct' and action != 'launchhtml' : return

    nonce = web.request.get('sec_nonce')
    timestamp = web.request.get('sec_created')
    digest = web.request.get('sec_digest')
    course_id = web.request.get("course_id")
    user_id = web.request.get("user_id")
    doHtml = action.lower() == "launchhtml"
    doDirect = action.lower() == "direct"
    targets = web.request.get('launch_targets')

    if len(nonce) <= 0 or len(timestamp) <= 0 or len(digest) <= 0 or len(user_id) <= 0 or len(course_id) <= 0 : 
      self.launcherror(web, doHtml, doDirect, None, "Missing one of sec_nonce, sec_created, sec_digest, course_id, user_id")
      return

    self.debug("Running on " + web.request.application_url)
    self.debug("Launch post action=" + action)

    # Determine check the timestamp for validity
    tock = self.parsetime(timestamp)
    if not tock :
      self.launcherror(web, doHtml, doDirect, None, "Error in format of TimeStamp")
      return

    org_digest = web.request.get('sec_org_digest')

    self.debug("sec_digest=" + digest)
    self.debug("sec_org_digest=" + org_digest)

    org_id = web.request.get("org_id")

    # Look in the URL for the course id
    urlpath = web.request.path
    trigger = "/lti_course_id/"
    path_course_id = None
    pos = urlpath.find(trigger)
    if ( pos >= 0 ) :
      path = urlpath[pos+len(trigger):]
      if path.find("/") > 0 :
        path = path[:path.find("/")]
      if len(path) > 0 : 
        path_course_id = path
        urlpath = urlpath[:pos]
        if len(urlpath) == 0 : urlpath = "/"

    self.debug("course_id="+course_id+" path_course_id="+str(path_course_id)+" path="+urlpath)

    # Clean up the digest - Delete up to 100 2-day-old digests
    nowtime = datetime.utcnow()
    before = nowtime - options.get('digest_expire', timedelta(hours=23))
    self.debug("Delete digests since "+before.isoformat())

    q = db.GqlQuery("SELECT * FROM LTI_Digest WHERE created < :1", before)
    results = q.fetch(options.get("digest_cleanup_count", 100))
    db.delete(results)

    # Validate the sec_digest 
    # dig = LTI_Digest.get_or_insert("key:"+digest)
    dig = opt_get_or_insert(LTI_Digest,"key:"+digest)

    reused = False
    if dig.digest == None :
      self.debug("Digest fresh")
      dig.digest = digest
    else:
      self.debug("Digest reused")
      reused = True

    dig.request = self.requestdebug(web)
    dig.put()

    # Get critical if there is some unauthorized reuse
    if reused and not options.get("allow_digest_reuse", False) :
      self.launcherror(web, doHtml, doDirect, dig, "Digest Reused")
      return

    # Validate the sec_org_digest if it is different from sec_digest
    if len(org_digest) > 0 and not org_digest == digest :
      # orgdig = LTI_Digest.get_or_insert("key:"+org_digest)
      orgdig = opt_get_or_insert(LTI_Digest,"key:"+org_digest)
      reused = False
      if orgdig.digest == None :
        self.debug("Organizational digest fresh")
        orgdig.digest = digest
      else:
        self.debug("Organizational digest reused")
        reused = True
  
      orgdig.request = self.requestdebug(web)
      orgdig.put()
  
      # Get critical if there is some unauthorized reuse
      if reused and not options.get("allow_digest_reuse", False) :
        self.launcherror(web, doHtml, doDirect, orgdig, "Organizational digest reused")
        return

    # Lets check to see if we have an organizational id and organizational secret
    # and check to see if we are really hearing from the organization
    org = None
    org_secret = None
    self.org = None
    if len(org_id) > 0  and len(org_digest) > 0  :
      if options.get('auto_create_orgs', False) :
        # org = LTI_Org.get_or_insert("key:"+org_id)
        org = opt_get_or_insert(LTI_Org,"key:"+org_id)
        org_secret = org.secret  # Can't change secret from the web
        Model_Load(org, web.request, "org_")
        if org_secret == None : org_secret = ""
        org.secret = org_secret
        org.put()
      else : 
        org = LTI_Org.get_by_key_name("key:"+org_id)
        if org : 
          org_secret = org.secret

    if org_secret == "" : org_secret = None

    if org and org_secret == None :
      org_secret = options.get("default_org_secret",None) 

    # No global orgs without secrets - sorry
    if not org_secret:
      org = None

    # Failing the org secret is not a complete failure - it 
    # simply means that the user_id and course_id and org data
    # are scoped to the course - on failure set org to None
    # and continue
    if org and org_secret:
      self.debug("org.key()="+str(org.key()))
      success = self.checknonce(nonce, timestamp, org_digest, org_secret, 
         options.get('nonce_time', 10000000) ) 
      if not success: org = None

    self.org = org

    # If we have a path_course_id then the course is not owned
    # by the organization - it is a standalone course where 
    # potentially many organiational course_ids will be mapped to it.
    course = None
    if path_course_id :
      if options.get('auto_create_courses', False) :
        # course = LTI_Course.get_or_insert("key:"+path_course_id)
        course = opt_get_or_insert(LTI_Course,"key:"+path_course_id)
        course_secret = course.secret  # Can't change secret from the web
        Model_Load(course, web.request, "course_")
        course.course_id = path_course_id
	if course_secret == None : course_secret = ""
        course.secret = course_secret
        course.put()
      else : 
        course = LTI_Course.get_by_key_name("key:"+course_id)
        if course : 
          course_secret = course.secret

      if course_secret == "" : course_secret = None

      if not course:
        self.launcherror(web, doHtml, doDirect, dig, "Course not found:"+path_course_id)
        return

      if course_secret == None :
        course_secret = options.get("default_course_secret",None) 

      # No global courses without secrets - sorry
      if not course_secret:
        self.launcherror(web, doHtml, doDirect, dig, "Course secret is not set:"+path_course_id)
        return

      self.debug("course.key()="+str(course.key()))
      success = self.checknonce(nonce, timestamp, digest, course_secret, 
         options.get('nonce_time', 10000000) ) 
      if not success: 
        self.launcherror(web, doHtml, doDirect, dig, "Course secret does not validate:"+path_course_id)
        return

    # If we have a global org and a global course - add the link
    if len(course_id) > 0 and course and org :
      self.debug("Linking OrgCourse="+course_id+" from org="+str(org.key())+" to path_course_id="+path_course_id)
      # orgcourse = LTI_OrgCourse.get_or_insert("key:"+course_id, parent=org)
      orgcourse = opt_get_or_insert(LTI_OrgCourse,"key:"+course_id, parent=org)
      orgcourse.course = course
      orgcourse.put()
    # If we have a path_course_id that is good, we are done
    # Just use that course
    elif len(course_id) > 0 and course :
      pass
    # We only have a course_id from the post data
    elif len(course_id) > 0 :
      if options.get('auto_create_courses', False) :
        # course = LTI_Course.get_or_insert("key:"+course_id, parent=org)
        course = opt_get_or_insert(LTI_Course,"key:"+course_id, parent=org)
        course_secret = course.secret  # Can't change secret from the web
        Model_Load(course, web.request, "course_")
	if course_secret == None : course_secret = ""
        course.secret = course_secret
        course.put()
      else : 
        course = LTI_Course.get_by_key_name("key:"+course_id, parent=org)
        if course : 
          course_secret = course.secret

      if course_secret == "" : course_secret = None

      if not course:
        self.launcherror(web, doHtml, doDirect, dig, "Course not found:"+course_id)
        return

      if course_secret == None or len(course_secret) <= 0 :
        course_secret = options.get("default_course_secret",None) 

      # No courses without secrets - sorry
      if not course_secret:
        self.launcherror(web, doHtml, doDirect, dig, "Course secret is not set:"+course_id)
        return

      self.debug("course.key()="+str(course.key()))
      success = self.checknonce(nonce, timestamp, digest, course_secret, 
         options.get('nonce_time', 10000000) ) 
      if not success: 
        self.launcherror(web, doHtml, doDirect, dig, "Course secret does not validate:"+course_id)
        return

    if ( not course ) :
       self.launcherror(web, doHtml, doDirect, dig, "Must have a valid course for a complete launch")
       return

    # Make the user and link to either then organization or the course
    user = None
    course_user = False
    if ( len(user_id) > 0 ) :
      if org:
        # user = LTI_User.get_or_insert("key:"+user_id, parent=org)
        user = opt_get_or_insert(LTI_User,"key:"+user_id, parent=org)
      else :
        # user = LTI_CourseUser.get_or_insert("key:"+user_id, parent=course)
        user = opt_get_or_insert(LTI_CourseUser,"key:"+user_id, parent=course)
        user.course = course
        course_user = True
      Model_Load(user, web.request, "user_")
      user.put()

    memb = None
    if ( not (user and course ) ) :
       self.launcherror(web, doHtml, doDirect, dig, "Must have a valid user for a complete launch")
       return

    # memb = LTI_Membership.get_or_insert("key:"+user_id, parent=course)
    memb = opt_get_or_insert(LTI_Membership,"key:"+user_id, parent=course)
    role = web.request.get("user_role")
    if ( len(role) < 1 ) : role = "Student"
    role = role.lower()
    roleval = 1
    if ( role == "instructor") : roleval = 2
    if ( role == "administrator") : roleval = 2
    memb.role = roleval
    memb.put()

    # One more data structure to build - if we don't have an 
    # organization and we have some organizational data - 
    # we stash it under the course.
 
    course_org = False
    if not org and len(org_id) > 0 :
      # org = LTI_CourseOrg.get_or_insert("key:"+org_id, parent=course)
      org = opt_get_or_insert(LTI_CourseOrg,"key:"+org_id, parent=course)
      Model_Load(org, web.request, "org_")
      org.course = course
      course_org = True
      org.put()

    # Clean up launches 
    nowtime = datetime.utcnow()
    before = nowtime - options.get('launch_expire', timedelta(days=2))
    self.debug("Delete launches since "+before.isoformat())

    q = db.GqlQuery("SELECT * FROM LTI_Launch WHERE created < :1", before)
    results = q.fetch(options.get('launch_cleanup_count', 100))
    db.delete(results)

    # launch = LTI_Launch.get_or_insert("key:"+user_id, parent=course)
    launch = opt_get_or_insert(LTI_Launch,"key:"+user_id, parent=course)
    Model_Load(launch, web.request, "launch_")
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

    # Need to make an option to allow a 
    # simple return instead of redirect
    # If we have a session attempt to store the key in the session
    # If all goes well the session and request key will match and 
    # urls will be keyword-free
    if doDirect:
      if session != False: session['lti_launch_key'] = str(launch.key())
      web.redirect(url)
      dig.debug = self.dStr
      dig.put()
      return

    if  success :
        self.debug("****** MATCH ******")
        respString = self.iframeResponse(url)
    else:
        self.debug("!!!!!! NO MATCH !!!!!!")
        respString = self.errorResponse()

    if doHtml:
        web.response.out.write("<pre>\nHTML Formatted Output(Test):\n\n")
        respString = cgi.escape(respString) 

    web.response.out.write(respString)

    if doHtml:
        web.response.out.write("\n\nDebug Output:\n")
        web.response.out.write(self.dStr)
        web.response.out.write("\n</pre>\n")

    dig.debug = self.dStr
    dig.put()

  def handlebbproxy(self, web, session, options):
    # Check for sanity - silently return
    action = web.request.get('tcbaseurl')
    if ( len(action) < 1 ) : return

    user_id = web.request.get('userid')
    course_id = web.request.get("course_id")
    digest = web.request.get("nonce")
    org_id = "proxy.blackboard.com"
    doDirect = True
    doHtml = False
    if user_id == None or course_id == None or digest is None:
      logging.info("Error mossing useris, course_id, or nonce on bbproxy launch")
      return

    # parse ticket
    ticket = web.request.get("ticket")
    displayid = user_id
    if not ticket is None:
      wds = ticket.split(":")
      if len(wds) > 3 : displayid = wds[3]

    # Clean up the digest - Delete up to 100 2-day-old digests
    nowtime = datetime.utcnow()
    before = nowtime - options.get('digest_expire', timedelta(hours=23))
    self.debug("Delete digests since "+before.isoformat())

    q = db.GqlQuery("SELECT * FROM LTI_Digest WHERE created < :1", before)
    results = q.fetch(options.get("digest_cleanup_count", 100))
    db.delete(results)

    # Validate the sec_digest 
    # TODO: Think about this one - is it optimistic?
    # dig = LTI_Digest.get_or_insert("key:"+digest)
    dig = opt_get_or_insert(LTI_Digest,"key:"+digest)
    reused = False
    if dig.digest == None :
      self.debug("Digest fresh")
      dig.digest = digest
    else:
      self.debug("Digest reused")
      reused = True

    dig.request = self.requestdebug(web)
    dig.put()

    # Get critical if there is some unauthorized reuse
    if reused and not options.get("allow_digest_reuse", False) :
      self.launcherror(web, doHtml, doDirect, dig, "Digest Reused")
      return

    org = None
    self.org = None
    org_secret = "secret"
    if len(org_id) > 0  :
        # org = LTI_Org.get_or_insert("key:"+org_id)
        org = opt_get_or_insert(LTI_Org,"key:"+org_id)
        Model_Load(org, web.request, "org_")
        if org_secret == None : org_secret = ""
        org.secret = org_secret
        org.put()

    self.org = org

    course = None
    if course_id :
        # course = LTI_Course.get_or_insert("key:"+course_id)
        course = opt_get_or_insert(LTI_Course,"key:"+course_id)
        course_secret = course.secret  # Can't change secret from the web
        if course_secret == None :
          course_secret = options.get("default_course_secret",None) 
        Model_Load(course, web.request, "course_")
        course.course_id = course_id
	if course_secret == None : course_secret = ""
        course.secret = course_secret
        course.name = course_id
        course.put()

    # If we have a global org and a global course - add the link
    if len(course_id) > 0 and course and org :
      self.debug("Linking OrgCourse="+course_id+" from org="+str(org.key()))
      # orgcourse = LTI_OrgCourse.get_or_insert("key:"+course_id, parent=org)
      orgcourse = opt_get_or_insert(LTI_OrgCourse,"key:"+course_id, parent=org)
      orgcourse.course = course
      orgcourse.put()
    # If we have a path_course_id that is good, we are done
    # Just use that course
    elif len(course_id) > 0 and course :
      pass
    # We only have a course_id from the post data
    elif len(course_id) > 0 :
      if options.get('auto_create_courses', False) :
        # course = LTI_Course.get_or_insert("key:"+course_id, parent=org)
        course = opt_get_or_insert(LTI_Course,"key:"+course_id, parent=org)
        course_secret = course.secret  # Can't change secret from the web
        Model_Load(course, web.request, "course_")
	if course_secret == None : course_secret = ""
        course.secret = course_secret
        course.name = course_id
        course.put()
      else : 
        course = LTI_Course.get_by_key_name("key:"+course_id, parent=org)
        if course : 
          course_secret = course.secret

      if course_secret == "" : course_secret = None

      if not course:
        self.launcherror(web, doHtml, doDirect, dig, "Course not found:"+course_id)
        return

      if course_secret == None or len(course_secret) <= 0 :
        course_secret = options.get("default_course_secret",None) 

      # No courses without secrets - sorry
      if not course_secret:
        self.launcherror(web, doHtml, doDirect, dig, "Course secret is not set:"+course_id)
        return

      self.debug("course.key()="+str(course.key()))
      success = self.checknonce(nonce, timestamp, digest, course_secret, 
         options.get('nonce_time', 10000000) ) 
      if not success: 
        self.launcherror(web, doHtml, doDirect, dig, "Course secret does not validate:"+course_id)
        return

    if ( not course ) :
       self.launcherror(web, doHtml, doDirect, dig, "Must have a valid course for a complete launch")
       return

    # Make the user and link to either then organization or the course
    user = None
    course_user = False
    if ( len(user_id) > 0 ) :
      if org:
        # user = LTI_User.get_or_insert("key:"+user_id, parent=org)
        user = opt_get_or_insert(LTI_User,"key:"+user_id, parent=org)
      else :
        # user = LTI_CourseUser.get_or_insert("key:"+user_id, parent=course)
        user = opt_get_or_insert(LTI_CourseUser,"key:"+user_id, parent=course)
        user.course = course
        course_user = True
      Model_Load(user, web.request, "user_")
      if user.user_id == None : user.user_id = user_id
      user.displayid = displayid
      user.put()

    memb = None
    if ( not (user and course ) ) :
       self.launcherror(web, doHtml, doDirect, dig, "Must have a valid user for a complete launch")
       return

    # memb = LTI_Membership.get_or_insert("key:"+user_id, parent=course)
    memb = opt_get_or_insert(LTI_Membership,"key:"+user_id, parent=course)
    role = web.request.get("tcrole")
    if ( len(role) < 1 ) : role = "Student"
    role = role.lower()
    roleval = 1
    if ( role == "instructor") : roleval = 2
    if ( role == "administrator") : roleval = 2
    memb.role = roleval
    memb.put()

    # Clean up launches 
    nowtime = datetime.utcnow()
    before = nowtime - options.get('launch_expire', timedelta(days=2))
    self.debug("Delete launches since "+before.isoformat())

    q = db.GqlQuery("SELECT * FROM LTI_Launch WHERE created < :1", before)
    results = q.fetch(options.get('launch_cleanup_count', 100))
    db.delete(results)

    # launch = LTI_Launch.get_or_insert("key:"+user_id, parent=course)
    launch = opt_get_or_insert(LTI_Launch,"key:"+user_id, parent=course)
    Model_Load(launch, web.request, "launch_")
    launch.memb = memb
    launch.org = org
    launch.user = user

    launch.course = course
    launch.put()
    self.debug("launch.key()="+str(launch.key()))

    urlpath = web.request.path
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
    dig.debug = self.dStr
    dig.put()

  def parsetime(self, timestamp) :
    # Receiving - Parse a Simple TI TimeStamp
    try:
        tock = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        self.debug("Parsed SimpleLTI TimeStamp "+tock.isoformat())
        return tock
    except:
	self.debug("Error parsing timestamp format - expecting 2008-06-03T13:51:20Z")
        return False
    
  def checknonce(self, nonce, timestamp, digest, secret = "secret", skew = 100000 ) :

    if len(nonce) <= 0 or len(timestamp) <= 0 or len(secret) <= 0 or len(digest) <= 0 : return False

    # Parse the timestamp
    tock = self.parsetime(timestamp)
    if not tock : return

    # Check for time difference (either way)
    nowtime = datetime.utcnow()
    self.debug("Current time "+nowtime.isoformat())
    diff = abs(nowtime - tock)

    # Our tolerable margin
    margin = timedelta(seconds=skew)
    if ( diff >= margin ) :
       self.debug("Time Mismatch Skew="+str(skew)+" Margin="+str(margin)+" Difference="+ str(diff))
       return False

    # Compute the digest
    presha1 = nonce + timestamp + secret
    # self.debug("Presha1 " + presha1)
    sha1 =  hashlib.sha1()
    sha1.update(presha1)
    x = sha1.digest()
    y = base64.b64encode(x)
    # self.debug("postsha1 "+y)
    # self.debug("digest "+digest)
    success = (digest == y)

    self.debug("Success="+str(success)+" Skew="+str(skew)+" Margin="+str(margin)+" Difference="+ str(diff))
    return success

  def iframeResponse(self,url):
    retval = '''<launchResponse>
   <status>success</status>
   <type>iFrame</type>
   <launchUrl>LAUNCHURL</launchUrl>
</launchResponse>
'''
    retval = retval.replace("LAUNCHURL",url)
    return retval

  def errorResponse(self, desc="The password digest was invalid"):
    retval = '''<launchResponse>
    <status>fail</status>
    <code>BadPasswordDigest</code>
    <description>DESC</description>
</launchResponse>
'''
    retval = retval.replace("DESC",desc)
    return retval

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
