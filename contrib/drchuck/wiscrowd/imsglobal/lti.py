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

class LTI_Org(db.Model):
     org_id = db.StringProperty()
     secret = db.BlobProperty()
     name = db.StringProperty()
     title = db.StringProperty()
     url = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_User(db.Model):
     user_id = db.StringProperty()
     eid = db.StringProperty()
     displayid = db.StringProperty()
     password = db.StringProperty()
     firstname = db.StringProperty()
     lastname = db.StringProperty()
     email = db.StringProperty()
     locale = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_Course(db.Model):
     course_id = db.StringProperty()
     secret = db.BlobProperty()
     code = db.StringProperty()
     name = db.StringProperty()
     title = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

# Organiztions that are scoped to a course
class LTI_CourseOrg(LTI_Org):
     course = db.ReferenceProperty(LTI_Course, collection_name='orgs')

# Users that are scoped to a course
# Should this be pointing to a CourseOrg ?
# Or just make a nasty composite key with the org_id ?
# Or should we use E-Mail?  No no no!
class LTI_CourseUser(LTI_Org):
     course = db.ReferenceProperty(LTI_Course, collection_name='users')

# Many to many mappings from Organizations to Courses
class LTI_OrgCourse(db.Model):
     org = db.ReferenceProperty(LTI_Org, collection_name='courses')
     course = db.ReferenceProperty(LTI_Course)

class LTI_Membership(db.Model):
     role = db.IntegerProperty()
     roster = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_Digest(db.Model):
     digest = db.StringProperty()
     request = db.TextProperty()
     debug = db.TextProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_Launch(db.Model):
     password = db.StringProperty()
     user = db.ReferenceProperty(LTI_User)
     course = db.ReferenceProperty(LTI_Course)
     org = db.ReferenceProperty(LTI_Org)
     memb = db.ReferenceProperty(LTI_Membership)
     resource_id = db.StringProperty()
     targets = db.StringProperty()
     resource_url = db.StringProperty()
     tool_id = db.StringProperty()
     tool_name = db.StringProperty()
     tool_title = db.StringProperty()
     width = db.StringProperty()
     height = db.StringProperty()

class LTI():
  dStr = ""
  complete = False
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

  def debug(self, str):
    logging.info(str)
    self.dStr = self.dStr + str + "\n"

  def getDebug(self):
    return dStr

  def dump(self):
    ret = "Dump of LTI Object\n";
    if ( not self.launch ):
      ret = ret + "No launch data\n"
      return ret
    ret = ret + "Complete = "+str(self.complete) + "\n";
    ret = ret + self.modeldump(self.user)
    ret = ret + self.modeldump(self.course)
    ret = ret + self.modeldump(self.memb)
    ret = ret + self.modeldump(self.org)
    ret = ret + self.modeldump(self.launch)

    return ret

  # We have several scenarios to handle
  def __init__(self, web, session = None, options = {}):
    self.web = web
    self.launch = None
    # Later set this to ocnservative
    if len(options) < 1 : options = self.Liberal
    self.handlelaunch(web, session, options)
    if ( self.complete ) : return
    self.handlesetup(web, session, options)

  def setvars(self):
    self.user = None
    self.course = None
    self.memb = None
    self.org = None
    if self.launch : 
      if self.launch.user : self.user = self.launch.user
      if self.launch.course : self.course = self.launch.course
      if self.launch.memb : self.memb = self.launch.memb
      if self.launch.org : self.org = self.launch.org

  def handlesetup(self, web, session, options):
    # get values form the request
    password = web.request.get('lti_launch_password')
    key = web.request.get('lti_launch_key')
    if ( len(password) < 0 ) : password = None
    if ( len(key) < 0 ) : key = None
    if ( key and not password ) : key = None
    if ( password and not key ) : password = None
    # self.debug("Password = "+str(password)+" Key="+(key))

    # get the values from the session
    sesskey = None
    sesspassword = None
    if session :  
      sesskey = session.get('lti_launch_key', None)
      sesspassword = session.get('lti_launch_password', None)
      # Deal with when only one is set
      if ( sesskey and not sesspassword) :
        del(session['lti_launch_key'])
        sesskey = None
      if ( sesspassword and not sesskey) :
        del(session['lti_launch_password'])
        sesspassword = None
    # self.debug("Session Password = "+str(sesspassword)+" Key="+str(sesskey))

    # If we have a key and password in session and they match
    # it is OK - if there is a mismatch - ignore the session
    if ( key and sesskey ) :
      if ( sesskey != key or sesspassword != password ) :
        del(session['lti_launch_key'])
        del(session['lti_launch_password'])
        sesskey = None
        sesspassword = None

    # On a normal request there are no parammeters - we just use session
    if ( sesskey ) :
      # Need try/except in case Key() is unhappy with the string
      try:
        launch = LTI_Launch.get(db.Key(sesskey))
      except:
        launch = None

      if not launch:
        self.debug("Session not found in store "+sesskey)
        if sesspassword : del(session['lti_launch_password'])
        if sesskey : del(session['lti_launch_key'])

      self.launch = launch
      self.setvars()
      return

    # On an initial we have parammeters and use them
    if ( key ) :
      # Need try/except in case Key() is unhappy with the string
      try:
        launch = LTI_Launch.get(db.Key(key))
      except:
        self.debug("Session Not Found in Store")
        launch = None

      # if the password does not match, give up
      if launch:
         self.debug("Database password="+str(launch.password))
         if len(password) > 0 and password == launch.password :
           launch.password = None
           launch.put()
           self.debug("Session one-time use password cleared")
         else :
           self.debug("Session password mis motch")
           launch = None

      if launch:
        session['lti_launch_key'] = key
        session['lti_launch_password'] = password
      else:
        if sesspassword : del(session['lti_launch_password'])
        if sesskey : del(session['lti_launch_key'])

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
    if action != 'launchresolve' and action != 'direct' and action != 'launchhtml' :
      return

    nonce = web.request.get('sec_nonce')
    timestamp = web.request.get('sec_created')
    digest = web.request.get('sec_digest')
    course_id = web.request.get("course_id")
    user_id = web.request.get("user_id")

    if len(nonce) <= 0 or len(timestamp) <= 0 or len(digest) <= 0 : 
       return
    if len(user_id) < 0 or len(course_id) <= 0 : return

    self.debug("Running on " + web.request.application_url)
    self.debug("Launch post action=" + action)

    # Determine check the timestamp for validity
    tock = self.parsetime(timestamp)
    if not tock : return

    doHtml = action.lower() == "launchhtml"
    doDirect = action.lower() == "direct"
    targets = web.request.get('launch_targets')
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

    ### What about ORG Digests - they need love too
    # Clean up the digest - Delete up to 100 2-day-old digests
    nowtime = datetime.utcnow()
    before = nowtime - options.get('digest_expire', timedelta(hours=23))
    self.debug("Delete digests since "+before.isoformat())

    q = db.GqlQuery("SELECT * FROM LTI_Digest WHERE created < :1", before)
    results = q.fetch(options.get("digest_cleanup_count", 100))
    db.delete(results)

    # Validate the sec_digest 
    dig = LTI_Digest.get_or_insert("key:"+digest)
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
      self.launcherror(web, doHtml, dig, "Digest Reused")
      return

    # Validate the sec_org_digest 
    if len(org_digest) > 0:
      orgdig = LTI_Digest.get_or_insert("key:"+org_digest)
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
        self.launcherror(web, doHtml, orgdig, "Organizational digest reused")
        return

    # Lets check to see if we have an organizational id and organizational secret
    # and check to see if we are really hearing from the organization
    org = None
    org_secret = None
    self.org = None
    if len(org_id) > 0  and len(org_digest) > 0  :
      if options.get('auto_create_orgs', False) :
        org = LTI_Org.get_or_insert("key:"+org_id)
        org_secret = org.secret  # Can't change secret from the web
        self.modelload(org, web.request, "org_")
        org.secret = org_secret
        org.put()
      else : 
        org = LTI_Org.get_by_keyname("key:"+org_id)
        if org : 
          org_secret = org.secret

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
      if not success: 
        self.launcherror(web, doHtml, orgdig, "Organizational digest did not validate")
        return

    self.org = org

    # If we have a path_course_id then the course is not owned
    # by the organization - it is a standalone course where 
    # potentially many organiational course_ids will be mapped to it.
    course = None
    if path_course_id :
      if options.get('auto_create_courses', False) :
        course = LTI_Course.get_or_insert("key:"+path_course_id)
        course_secret = course.secret  # Can't change secret from the web
        self.modelload(org, web.request, "course_")
        course.secret = course_secret
        course.put()
      else : 
        course = LTI_Course.get_by_keyname("key:"+course_id)
        if course : 
          course_secret = course.secret

      if not course:
        self.launcherror(web, doHtml, dig, "Course not found:"+path_course_id)
        return

      if course_secret == None :
        course_secret = options.get("default_course_secret",None) 

      # No global courses without secrets - sorry
      if not course_secret:
        self.launcherror(web, doHtml, dig, "Course secret is not set:"+path_course_id)
        return

      self.debug("course.key()="+str(course.key()))
      success = self.checknonce(nonce, timestamp, digest, course_secret, 
         options.get('nonce_time', 10000000) ) 
      if not success: 
        self.launcherror(web, doHtml, dig, "Course secret does not validate:"+path_course_id)
        return

    # If we have a global org and a global course - add the link
    if len(course_id) > 0 and course and org :
      self.debug("Linking OrgCourse="+course_id+" from org="+str(org.key())+" to path_course_id="+path_course_id)
      orgcourse = LTI_OrgCourse.get_or_insert("key:"+course_id, parent=org)
      orgcourse.course = course
      orgcourse.put()
    # If we have a path_course_id that is good, we are done
    # Just use that course
    elif len(course_id) > 0 and course :
      pass
    # We only have a course_id from the post data
    elif len(course_id) > 0 :
      if options.get('auto_create_courses', False) :
        course = LTI_Course.get_or_insert("key:"+course_id, parent=org)
        course_secret = course.secret  # Can't change secret from the web
        self.modelload(org, web.request, "course_")
        course.secret = course_secret
        course.put()
      else : 
        course = LTI_Course.get_by_keyname("key:"+course_id, parent=org)
        if course : 
          course_secret = course.secret

      if not course:
        self.launcherror(web, doHtml, dig, "Course not found:"+course_id)
        return

      if course_secret == None :
        course_secret = options.get("default_course_secret",None) 

      # No courses without secrets - sorry
      if not course_secret:
        self.launcherror(web, doHtml, dig, "Course secret is not set:"+course_id)
        return

      self.debug("course.key()="+str(course.key()))
      success = self.checknonce(nonce, timestamp, digest, course_secret, 
         options.get('nonce_time', 10000000) ) 
      if not success: 
        self.launcherror(web, doHtml, dig, "Course secret does not validate:"+path_course_id)
        return

    if ( not course ) :
       self.launcherror(web, doHtml, dig, "Must have a valid course for a complete launch")
       return
     
    user = None
    if ( len(user_id) > 0 ) :
      if org:
        user = LTI_User.get_or_insert("key:"+user_id, parent=org)
      else :
        user = LTI_User.get_or_insert("key:"+user_id, parent=course)
      self.modelload(user, web.request, "user_")
      user.put()

    memb = None
    if ( not (user and course ) ) :
       self.launcherror(web, doHtml, dig, "Must have a valid user for a complete launch")
       return

    memb = LTI_Membership.get_or_insert("key:"+user_id, parent=course)
    role = web.request.get("user_role")
    if ( len(role) < 1 ) : role = "Student"
    role = role.lower()
    roleval = 1;
    if ( role == "instructor") : roleval = 2
    if ( role == "administrator") : roleval = 2
    memb.role = roleval
    memb.put()
 
    # Clean up launches - Delete up to 10 "old launches"
    nowtime = datetime.utcnow()
    before = nowtime - options.get('launch_expire', timedelta(days=2))
    self.debug("Delete launches since "+before.isoformat())

    q = db.GqlQuery("SELECT * FROM LTI_Launch WHERE created < :1", before)
    results = q.fetch(options.get('launch_cleanup_count', 100))
    db.delete(results)

    # Should launches be unique per launch - or keyed by user_id and reused
    # An advantage of reusing the same launch is that folks don't get logged
    # Out on later launches - it is more like a session - perhaps we should have
    # a session.   The the question is "One course" per session?  Would the user
    # appear to be switched to a new course for launch?  Would it be "latest launch"?
    # Maybe keep all the launches and make a session - hmmmm.
    launch = LTI_Launch.get_or_insert("key:"+user_id, parent=course)
    self.modelload(launch, web.request, "launch_")
    launch.password = str(uuid.uuid4())
    launch.user = user
    launch.memb = memb
    launch.org = org
    launch.course = course
    launch.put()
    self.debug("launch.key()="+str(launch.key()))

    url = web.request.application_url+urlpath

    if ( url.find('?') >= 0 ) :
      url = url + "?"
    else :
      url = url + "?"

    url = url + urllib.urlencode({"lti_launch_key" : str(launch.key()), "lti_launch_password" : launch.password})

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
    if doDirect:
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
    self.debug("sec_nonce=" + nonce)
    self.debug("sec_created=" + timestamp)
    self.debug("Using secret=" + secret)
    self.debug("Using digest=" + digest)

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
    self.debug("Presha1 " + presha1)
    sha1 =  hashlib.sha1()
    sha1.update(presha1)
    x = sha1.digest()
    y = base64.b64encode(x)
    self.debug("postsha1 "+y)
    self.debug("digest "+digest)
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

  def launcherror(self, web, doHtml, dig, desc) :
      self.complete = True
      respString = self.errorResponse(desc)
      if doHtml:
        web.response.out.write("<pre>\nHTML Formatted Output(Test):\n\n")
        respString = cgi.escape(respString) 
      web.response.out.write(respString)
      if doHtml:
        web.response.out.write("\n\nDebug Output:\n")
        web.response.out.write(self.dStr)
        web.response.out.write("\n</pre>\n")
      if dig:
        dig.debug = self.dStr
        dig.put()

  def requestdebug(self, web):
    # Drop in the request for debugging
    reqstr = web.request.path + "\n"
    for key in web.request.params.keys():
      value = web.request.get(key)
      if len(value) < 100: 
         reqstr = reqstr + key+':'+value+'\n'
      else: 
         reqstr = reqstr + key+':'+str(len(value))+' (bytes long)\n'
    return reqstr

  # Some utility mehtods
  def isInstructor(self) :
    if self.launch and self.memb :
      return (self.memb.role == 2)
    else : 
      return False

  def getUserName(self):
     if ( not ( self.launch and self.user ) ) : return "Anonymous"
     if ( self.user.displayid ) : return self.user.displayid
     retval = ""
     if ( self.user.firstname and self.user.lastname ) : 
        return self.user.firstname + " " + self.user.lastname
     elif ( self.user.firstname ) : return self.user.firstname
     elif ( self.user.lastname ) : return self.user.lastname
     if ( self.user.email ) : return self.user.email
     return ""

  def getCourseName(self):
     if ( not ( self.launch and self.course ) ) : return "None"
     if ( self.course.name ) : return self.course.name
     if ( self.course.title ) : return self.course.title
     if ( self.course.code ) : return self.course.code
     return ""

  # Loop through the request keys and see if they can be put 
  # into the model
  def modelload(self, org, req, prefix = None):
    count = 0
    for key in req.params.keys(): 
      value = self.web.request.get(key) 
      thetype = self.modeltype(org, key)
      if ( thetype == "none" and prefix != None ) :
         if ( not key.startswith(prefix) ) : continue
         key = key[len(prefix):]
         thetype = self.modeltype(org, key)

      if ( thetype == "none" ) : continue
      setattr(org,key,value)
      count = count + 1
    self.debug("MODEL LOAD "+str(org.__class__)+" loaded "+str(count)+" keys")

  def modeltype(self, obj, key):
    try:
      attr = str(type(getattr(obj.__class__, key)))
    except :
      return "none"

    if attr.find("ext.db.StringProperty") > 0 : return "string"
    if attr.find("ext.db.ReferenceProperty") > 0 : return "reference"
    if attr.find("ext.db.DateTimeProperty")  > 0: return "datetime"
    if attr.find("ext.db.IntegerProperty")  > 0: return "int"
    return "none"

  def modeldump(self, obj):
    if ( not obj ) : 
       return ""
       ret = ret + " Not populated\n"
       return ret

    ret = "Dumping " + obj.__class__.__name__  + "\n"

    for key in dir(obj.__class__) : 
      # print "Key " + key + "\n"
      typ = self.modeltype(obj, key)
      # print "Typ " + typ + "\n"
      if ( typ == "string" or typ == "int" ) :
        val = getattr(obj,key)
	if ( not val ) : val = "None"
        ret = ret + "  " + key + "=" + str(val) + "\n";

    return ret
    
