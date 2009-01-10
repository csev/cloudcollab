from google.appengine.ext import db
import logging

import cgi
import os
import wsgiref.handlers
import logging
import hashlib
import base64
from google.appengine.ext.webapp import template
from  datetime import datetime, timedelta

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

# A Model for a User
class LTI_Org(db.Model):
     owner_id = db.ReferenceProperty()
     org_id = db.StringProperty()
     secret = db.StringProperty()
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
     org_id = db.ReferenceProperty
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_Session(db.Model):
     user_id = db.ReferenceProperty
     course_id = db.ReferenceProperty
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_Course(db.Model):
     course_id = db.StringProperty()
     code = db.StringProperty()
     name = db.StringProperty()
     title = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_Membership(db.Model):
     course_id = db.ReferenceProperty
     user_id = db.ReferenceProperty 
     role_id = db.ReferenceProperty 
     roster = db.StringProperty
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_Tool(db.Model):
     tool_name = db.StringProperty
     tool_title = db.StringProperty
     tool_id = db.StringProperty
     targets = db.StringProperty
     resource_id = db.StringProperty
     resource_url = db.StringProperty
     width = db.StringProperty
     height = db.StringProperty
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_Digest(db.Model):
     digest = db.StringProperty
     request = db.StringProperty
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_Launch(db.Model):
     password = db.StringProperty
     user_id = db.ReferenceProperty
     course_id = db.ReferenceProperty
     org_id = db.ReferenceProperty
     resource_id = db.StringProperty
     targets = db.StringProperty
     resource_url = db.StringProperty
     tool_id = db.StringProperty
     tool_name = db.StringProperty
     tool_title = db.StringProperty
     width = db.StringProperty
     height = db.StringProperty

class LTI():
  dStr = ""

  def debug(self, str):
    logging.info(str)
    self.dStr = self.dStr + str + "\n"

  # We have several scenarios to handle
  def __init__(self, web, options = {}):
     logging.info("Construct me! " + web.request.path)
     self.web = web
     self.user = LTI_User(displayid="Chuck")
     setattr(self.user,"email", "csev@umich.edu")
     self.handlelaunch(web,options)
     value = getattr(LTI_User, "email")
     web.response.out.write("type "+str(type(LTI_User.email))+"\n")
     web.response.out.write("xtype "+str(value)+"\n")

  def handlelaunch(self, web, options):
    action = web.request.get('action')
    if ( len(action) < 1 ) : action = web.request.get("lti_action")
    if ( len(action) < 1 ) : return
    action = action.lower()
    if ( action != 'launchresolve' and action != 'direct' and action != 'launchhtml' ) :
      logging.info("Nothing action for us  launch...")
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
    doWidget = targets.lower().startswith('widget')
    doPost = targets.lower().startswith('post')

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

    self.org = LTI_Org()

    self.ormload(self.org, web.request, "org_")

    self.debug("org.name="+str(self.org.name))

    if doDirect:
	web.redirect("http://www.youtube.com/v/f90ysF9BenI")
	return

    if  success :
        self.debug("****** MATCH ******")
        if doWidget:
            respString = self.widgetResponse(width,height)
        elif doPost:
            respString = self.postResponse()
        else:
            respString = self.iframeResponse()
    else:
        self.debug("!!!!!! NO MATCH !!!!!!")
        respString = self.errorResponse()

    if doHtml or doDirect:
        web.response.out.write("<pre>\nHTML Formatted Output(Test):\n\n")
        respString = cgi.escape(respString) 

    if doDirect:
        web.response.out.write("Direct launch - data dump\n")
        web.response.out.write("<a href=http://www.youtube.com/v/f90ysF9BenI>Content</a>")
    else:
        web.response.out.write(respString)

    if doHtml or doDirect:
        web.response.out.write("\n\nDebug Output:\n")
    else:
        web.response.out.write("\n\n<!--\nDebug Output:\n")

    web.response.out.write(self.dStr)

    if doHtml or doDirect:
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

  def iframeResponse(self):
    return '''<launchResponse>
   <status>success</status>
   <type>iFrame</type>
   <launchUrl>http://www.youtube.com/v/f90ysF9BenI</launchUrl>
</launchResponse>
'''

  def postResponse(self):
    retval =  '''<launchResponse>
   <status>success</status>
   <type>post</type>
   <launchUrl>LAUNCHURL</launchUrl>
</launchResponse>
'''
    path = self.request.application_url + "/launch?i=25"
    retval = retval.replace("LAUNCHURL",path)
    return retval

  def widgetResponse(self, width, height):
    retval = '''<launchResponse>
   <status>success</status>
   <type>widget</type>
   <widget>
&lt;object width="425" height="344"&gt;&lt;param name="movie" value="http://www.youtube.com/v/f90ysF9BenI&amp;hl=en"&gt;&lt;/param&gt;&lt;embed src="http://www.youtube.com/v/f90ysF9BenI&amp;hl=en" type="application/x-shockwave-flash" width="425" height="344"&gt;&lt;/embed&gt;&lt;/object&gt;
  </widget>
</launchResponse>
'''
    if width != None and len(width) > 0 :
	retval = retval.replace("425",width)
    if height != None and len(height) > 0 :
	retval = retval.replace("344",height)
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
    self.debug("ORM LOAD")
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
