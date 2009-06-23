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

class BB_Context(Context):
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
    self.handlesetup(web, session, options)

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

    q = db.GqlQuery("SELECT * FROM LMS_Digest WHERE created < :1", before)
    results = q.fetch(options.get("digest_cleanup_count", 100))
    db.delete(results)

    # Validate the sec_digest 
    # TODO: Think about this one - is it optimistic?
    # dig = LMS_Digest.get_or_insert("key:"+digest)
    dig = opt_get_or_insert(LMS_Digest,"key:"+digest)
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
        # org = LMS_Org.get_or_insert("key:"+org_id)
        org = opt_get_or_insert(LMS_Org,"key:"+org_id)
        Model_Load(org, web.request.params, "org_")
        if org_secret == None : org_secret = ""
        org.secret = org_secret
        org.put()

    self.org = org

    course = None
    if course_id :
        # course = LMS_Course.get_or_insert("key:"+course_id)
        course = opt_get_or_insert(LMS_Course,"key:"+course_id)
        course_secret = course.secret  # Can't change secret from the web
        if course_secret == None :
          course_secret = options.get("default_course_secret",None) 
        Model_Load(course, web.request.params, "course_")
        course.course_id = course_id
	if course_secret == None : course_secret = ""
        course.secret = course_secret
        course.name = course_id
        course.put()

    # If we have a global org and a global course - add the link
    if len(course_id) > 0 and course and org :
      self.debug("Linking OrgCourse="+course_id+" from org="+str(org.key()))
      # orgcourse = LMS_OrgCourse.get_or_insert("key:"+course_id, parent=org)
      orgcourse = opt_get_or_insert(LMS_OrgCourse,"key:"+course_id, parent=org)
      orgcourse.course = course
      orgcourse.put()
    # If we have a path_course_id that is good, we are done
    # Just use that course
    elif len(course_id) > 0 and course :
      pass
    # We only have a course_id from the post data
    elif len(course_id) > 0 :
      if options.get('auto_create_courses', False) :
        # course = LMS_Course.get_or_insert("key:"+course_id, parent=org)
        course = opt_get_or_insert(LMS_Course,"key:"+course_id, parent=org)
        course_secret = course.secret  # Can't change secret from the web
        Model_Load(course, web.request.params, "course_")
	if course_secret == None : course_secret = ""
        course.secret = course_secret
        course.name = course_id
        course.put()
      else : 
        course = LMS_Course.get_by_key_name("key:"+course_id, parent=org)
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
        # user = LMS_User.get_or_insert("key:"+user_id, parent=org)
        user = opt_get_or_insert(LMS_User,"key:"+user_id, parent=org)
      else :
        # user = LMS_CourseUser.get_or_insert("key:"+user_id, parent=course)
        user = opt_get_or_insert(LMS_CourseUser,"key:"+user_id, parent=course)
        user.course = course
        course_user = True
      Model_Load(user, web.request.params, "user_")
      if user.user_id == None : user.user_id = user_id
      user.displayid = displayid
      user.put()

    memb = None
    if ( not (user and course ) ) :
       self.launcherror(web, doHtml, doDirect, dig, "Must have a valid user for a complete launch")
       return

    # memb = LMS_Membership.get_or_insert("key:"+user_id, parent=course)
    memb = opt_get_or_insert(LMS_Membership,"key:"+user_id, parent=course)
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

    q = db.GqlQuery("SELECT * FROM LMS_Launch WHERE created < :1", before)
    results = q.fetch(options.get('launch_cleanup_count', 100))
    db.delete(results)

    # launch = LMS_Launch.get_or_insert("key:"+user_id, parent=course)
    launch = opt_get_or_insert(LMS_Launch,"key:"+user_id, parent=course)
    Model_Load(launch, web.request.params, "launch_")
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
