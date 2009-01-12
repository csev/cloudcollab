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


# A Model for a User
class LTI_Org(db.Model):
     logicalkey = "org_id"
     org_id = db.StringProperty()
     secret = db.StringProperty()
     name = db.StringProperty()
     title = db.StringProperty()
     url = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_User(db.Model):
     logicalkey = "user_id"
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
     logicalkey = "course_id"
     course_id = db.StringProperty()
     code = db.StringProperty()
     name = db.StringProperty()
     title = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_Session(db.Model):
     logicalkey = None
     user = db.ReferenceProperty(LTI_User)
     course = db.ReferenceProperty(LTI_Course)
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_Membership(db.Model):
     course = db.ReferenceProperty(LTI_Course)
     user = db.ReferenceProperty (LTI_User)
     role = db.IntegerProperty()
     roster = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_Tool(db.Model):
     logicalkey = "tool_id"
     tool_id = db.StringProperty()
     tool_name = db.StringProperty()
     tool_title = db.StringProperty()
     targets = db.StringProperty()
     resource_id = db.StringProperty()
     resource_url = db.StringProperty()
     width = db.StringProperty()
     height = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_Digest(db.Model):
     logicalkey = "digest"
     digest = db.StringProperty()
     request = db.StringProperty()
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

  def handlesetup(self, web, session, ptions):
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
    action = web.request.get('action')
    if ( len(action) < 1 ) : action = web.request.get("lti_action")
    if ( len(action) < 1 ) : return
    action = action.lower()
    if ( action != 'launchresolve' and action != 'direct' and action != 'launchhtml' ) :
      self.debug("Nothing action for us  launch...")
      return

    self.debug("Running on " + web.request.application_url)
    self.debug("Launch post action=" + action)

    # Echo the required parameters
    for key in web.request.params.keys(): 
      value = web.request.get(key) 
      if len(value) < 100: 
         self.debug(key+':'+value)
      else: 
         self.debug(key+':'+str(len(value))+' (bytes long)')

    doHtml = action.lower() == "launchhtml"
    doDirect = action.lower() == "direct"

    targets = web.request.get('launch_targets')

    nonce = web.request.get('sec_nonce')
    secret = web.request.get('sec_secret')
    if secret == None or secret == "":
        secret = "secret"
    timestamp = web.request.get('sec_created')
    digest = web.request.get('sec_digest')
    org_digest = web.request.get('sec_org_digest')

    self.debug("sec_digest=" + digest)
    self.debug("sec_org_digest=" + org_digest)

    if digest == None or len(digest) < 1 :
       digest = org_digest

    success = self.checknonce(nonce, timestamp, digest, "secret", 100000 ) 

    width = web.request.get('launch_width')
    height = web.request.get('launch_height')

    org_id = web.request.get("org_id")
    self.org = None
    if ( len(org_id) > 0 ) :
      # Todo figure out what to do with the org secret
      # and org policy options
      org = self.modelread(LTI_Org, org_id)
      self.debug("org.org_id="+str(org.org_id))

      self.modelload(org, web.request, "org_")
      self.debug("org.name="+str(org.name))

      org.put()
      self.debug("key = "+str(org.key()))
      self.org = org

    user = None
    user_id = web.request.get("user_id")
    if ( len(user_id) > 0 ) :
      user = self.modelread(LTI_User, user_id)
      self.modelload(user, web.request, "user_")
      self.debug("user.email="+str(user.email))
      user.put()

    course_id = web.request.get("course_id")
    course = None
    if ( len(course_id) > 0 ) :
      course = self.modelread(LTI_Course, course_id)
      self.modelload(course, web.request, "course_")
      self.debug("course.name="+str(course.name))
      course.put()

    memb = None
    if ( not (user and course ) ) :
       self.debug("Must have user and course for a complete launch")
       return

    que = db.Query(LTI_Membership)
    que = que.filter("course =", course.key())
    que = que.filter("user = ", user.key())
    results = que.fetch(limit=1)
    if len(results) > 0 :
      memb = results[0]
      self.debug("Existing membership record found")
    else : 
      memb = LTI_Membership(course = course, user = user)

    role = web.request.get("user_role")
    if ( len(role) < 1 ) : role = "Student"
    role = role.lower()
    roleval = 1;
    if ( role == "instructor") : roleval = 2
    memb.role = roleval
    memb.put()
 
    self.debug("Here we go "+memb.user.email)

    que = db.Query(LTI_Launch)
    que = que.filter("course =", course.key())
    que = que.filter("user = ", user.key())
    results = que.fetch(limit=1)
    if len(results) > 0 :
      launch = results[0]
      self.debug("Existing launch record found")
    else : 
      launch = LTI_Launch(course = course, user = user, memb = memb)

    self.modelload(launch, web.request, "launch_")
    launch.org = self.org
    launch.password = str(uuid.uuid4())
    launch.put()
    self.debug("launch.key()="+str(launch.key()))
    self.launch = launch

    url = web.request.application_url+web.request.path

    if ( url.find('?') >= 0 ) :
      url = url + "?"
    else :
      url = url + "?"

    url = url + urllib.urlencode({"lti_launch_key" : str(launch.key()), "lti_launch_password" : launch.password})

    self.debug("url = "+url)
 
    # We have made it to the point where we have handled this request
    self.complete = True
    self.user = launch.user
    self.course = launch.course
    self.memb = launch.memb
    self.org = launch.org

    # Need to make an option to allow a 
    # simple return instead of redirect
    if doDirect:
	web.redirect(url)
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
    else:
        web.response.out.write("\n\n<!--\nDebug Output:\n")

    web.response.out.write(self.dStr)

    if doHtml:
        web.response.out.write("\n</pre>\n")
    else:
        web.response.out.write("\n-->\n")


  def checknonce(self, nonce, timestamp, digest, secret = "secret", skew = 100000 ) :
    self.debug("sec_nonce=" + nonce)
    self.debug("sec_created=" + timestamp)
    self.debug("Using secret=" + secret)
    self.debug("Using digest=" + digest)

    presha1 = nonce + timestamp + secret
    self.debug("Presha1 " + presha1)
    sha1 =  hashlib.sha1()
    sha1.update(presha1)
    x = sha1.digest()
    y = base64.b64encode(x)
    self.debug("postsha1 "+y)
    self.debug("digest "+digest)
    if ( digest != y ) : return False

    # Receiving - Parse a Simple TI TimeStamp
    try:
        tock = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        self.debug("Parsed SimpleLTI TimeStamp "+tock.isoformat())
    except:
	self.debug("Error parsing timestamp format - expecting 2008-06-03T13:51:20Z")
        return False
    
    # Check for time difference (either way)
    nowtime = datetime.utcnow()
    self.debug("Current time "+nowtime.isoformat())
    diff = abs(nowtime - tock)

    # Our tolerable margin
    margin = timedelta(seconds=skew)
    success = diff < margin
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

  def errorResponse(self):
    return '''<launchResponse>
    <status>fail</status>
    <code>BadPasswordDigest</code>
    <description>The password digest was invalid</description>
</launchResponse>
'''

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
    self.debug("MODEL LOAD "+str(org.__class__))
    for key in req.params.keys(): 
      value = self.web.request.get(key) 
      thetype = self.modeltype(org, key)
      if ( thetype == "none" and prefix != None ) :
         if ( not key.startswith(prefix) ) : continue
         key = key[len(prefix):]
         thetype = self.modeltype(org, key)

      if ( thetype == "none" ) : continue
      self.debug(key+" ("+thetype+") = "+value)
      setattr(org,key,value)

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

  def modelread(self, theclass, keyvalue) :
    if ( len(keyvalue) > 0 ) :
      que = db.Query(theclass)
      que = que.filter(theclass.logicalkey+" =",keyvalue)

      results = que.fetch(limit=1)

      if len(results) > 0 :
        org = results[0]
      else :
        org = theclass()
        setattr(org, theclass.logicalkey, keyvalue)
      return org
    else : 
      return None 

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
    
