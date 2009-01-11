import logging
import cgi
import os
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

def modeltype(obj, key):
      try:
         attr = str(type(getattr(obj.__class__, key)))
      except :
         return None

      if attr.find("ext.db.StringProperty") : return "string"
      if attr.find("ext.db.ReferenceProperty") : return "reference"
      if attr.find("ext.db.DateTimeProperty") : return "datetime"
      if attr.find("ext.db.IntegerProperty") : return "int"

def modelread(theclass, keyvalue) :
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

  def debug(self, str):
    logging.info(str)
    self.dStr = self.dStr + str + "\n"

  # We have several scenarios to handle
  def __init__(self, web, session = None, options = {}):
     self.complete = False
     self.web = web
     self.user = LTI_User(displayid="Chuck")
     setattr(self.user,"email", "csev@umich.edu")
     self.handlelaunch(web, session, options)
     value = getattr(LTI_User, "email")
     if ( self.complete ) : return
     self.handlesetup(web, session, options)
     value = getattr(LTI_User, "email")

  def handlesetup(self, web, session, ptions):
    password = web.request.get('lti_launch_password')
    key = web.request.get('lti_launch_key')
    if ( len(password) < 0 or len(key) < 0 ) :
      self.debug("Nothing for us to setup...")
      return
    self.debug("Password = "+password+" Key="+key)
    '''
    Deal with the situation where we see id/pw the first time
    with an empty session or - we see it a second time on refresh
    with a session id/pw on the request that matches session
    If we have non-empty session, and it does not match the 
    request parameters, clear the session
    '''
    self.launch = None
    launch = LTI_Launch.get(db.Key(key))
    self.debug("Launch came back "+launch.user.email);

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
      org = modelread(LTI_Org, org_id)
      self.debug("org.org_id="+str(org.org_id))

      self.ormload(org, web.request, "org_")
      self.debug("org.name="+str(org.name))

      org.put()
      self.debug("key = "+str(org.key()))
      self.org = org

    user_id = web.request.get("user_id")
    self.user = None
    if ( len(user_id) > 0 ) :
      user = modelread(LTI_User, user_id)
      self.ormload(user, web.request, "user_")
      self.debug("user.email="+str(user.email))
      user.put()
      self.user = user

    course_id = web.request.get("course_id")
    self.course = None
    if ( len(course_id) > 0 ) :
      course = modelread(LTI_Course, course_id)
      self.ormload(course, web.request, "course_")
      self.debug("course.name="+str(course.name))
      course.put()
      self.course = course

    self.memb = None
    que = db.Query(LTI_Membership)
    que = que.filter("course =", self.course.key())
    que = que.filter("user = ", self.user.key())
    results = que.fetch(limit=1)
    if len(results) > 0 :
      memb = results[0]
      self.debug("Existing membership record found")
    else : 
      memb = LTI_Membership(course = self.course, user = self.user)

    role = web.request.get("user_role")
    if ( len(role) < 1 ) : role = "Student"
    role = role.lower()
    roleval = 1;
    if ( role == "instructor") : roleval = 2
    memb.role = roleval
    memb.put()
    self.memb = memb

    self.debug("Here we go "+memb.user.email)

    self.launch = None
    que = db.Query(LTI_Launch)
    que = que.filter("course =", self.course.key())
    que = que.filter("user = ", self.user.key())
    results = que.fetch(limit=1)
    if len(results) > 0 :
      launch = results[0]
      self.debug("Existing launch record found")
    else : 
      launch = LTI_Launch(course = self.course, user = self.user)

    self.ormload(launch, web.request, "launch_")
    launch.org = self.org
    launch.password = str(uuid.uuid4())
    launch.put()
    self.debug("launch.key()="+str(launch.key()))
    self.launch = launch

    url = "http://"+os.environ['HTTP_HOST']+web.request.path

    if ( url.find('?') >= 0 ) :
      url = url + "?"
    else :
      url = url + "?"

    url = url + urllib.urlencode({"lti_launch_key" : str(launch.key()), "lti_launch_password" : launch.password})

    self.debug("url = "+url)
 
    # We have made it to the point where we have handled this request
    self.complete = True
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

  # Loop through the request keys and see if they can be put 
  # into the model
  def ormload(self, org, req, prefix = None):
    self.debug("ORM LOAD "+str(org.__class__))
    for key in req.params.keys(): 
      value = self.web.request.get(key) 
      thetype = modeltype(org, key)
      if ( thetype == None and prefix != None ) :
         if ( not key.startswith(prefix) ) : continue
         key = key[len(prefix):]
         thetype = modeltype(org, key)

      if ( thetype == None ) : continue
      self.debug(key+" ("+thetype+") = "+value)
      setattr(org,key,value)
