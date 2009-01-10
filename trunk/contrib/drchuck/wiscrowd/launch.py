#!/usr/bin/env python

import cgi
import os
import wsgiref.handlers
import logging
import hashlib
import base64
from google.appengine.ext.webapp import template
from  datetime import datetime, timedelta

from google.appengine.ext import webapp

class LaunchHandler(webapp.RequestHandler):

  dStr = ""

  def debug(self, str):
    logging.info(str)
    self.dStr = self.dStr + str + "\n"

  def get(self):
    self.post();

    # path = os.path.join(os.path.dirname(__file__), 'launch.html')
    # self.response.out.write(template.render(path, {}))

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
    return retval;

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

  def post(self):
    self.debug("Running on " + self.request.application_url)
    action = self.request.get('action')
    self.debug("Launch post action=" + action)
    doHtml = action.lower() == "launchhtml"
    doDirect = action.lower() == "direct"

    targets = self.request.get('launch_targets')
    doWidget = targets.lower().startswith('widget')
    doPost = targets.lower().startswith('post')

    nonce = self.request.get('sec_nonce')
    secret = self.request.get('sec_secret')
    if secret == None or secret == "":
        secret = "secret"
    timestamp = self.request.get('sec_created')
    digest = self.request.get('sec_digest')
    org_digest = self.request.get('sec_org_digest')

    self.debug("sec_digest=" + digest)
    self.debug("sec_org_digest=" + org_digest)

    if digest == None or len(digest) < 1 :
       digest = org_digest

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
    success = ( digest == y )

    # Echo the required parameters
    self.debug("user_id=" + self.request.get("user_id"))
    self.debug("user_role=" + self.request.get("user_role"))
    self.debug("course_id=" + self.request.get("course_id"))
    self.debug("course_code=" + self.request.get("course_code"))
    self.debug("org_id=" + self.request.get("org_id"))
    self.debug("org_title=" + self.request.get("org_title"))
    self.debug("org_name=" + self.request.get("org_name"))
    self.debug("launch_resource_id=" + self.request.get("launch_resource_id"))
    self.debug("launch_resource_url=" + self.request.get("launch_resource_url") + " (optional)")
    self.debug("launch_width=" + self.request.get("launch_width"))
    self.debug("launch_height=" + self.request.get("launch_height"))

    # Receiving - Parse a Simple TI TimeStamp
    try:
        tock = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        self.debug("Parsed SimpleLTI TimeStamp "+tock.isoformat())
    
        # Check for time difference (either way)
        nowtime = datetime.utcnow()
        self.debug("Current time "+nowtime.isoformat())
        diff = abs(nowtime - tock)

        # Our tolerable margin
        margin = timedelta(seconds=30)
        # self.debug("Margin"+margin+" difference"+ diff)

        if diff < margin :
           self.debug("Timestamp is within 30 seconds...")
        else :
           self.debug("Time difference greater than 30 seconds")
    except:
	self.debug("Error parsing timestamp format - expecting 2008-06-03T13:51:20Z")

    width = self.request.get('launch_width')
    height = self.request.get('launch_height')

    if doDirect:
	self.redirect("http://www.youtube.com/v/f90ysF9BenI")
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
        self.response.out.write("<pre>\nHTML Formatted Output(Test):\n\n")
        respString = cgi.escape(respString) 

    if doDirect:
        self.response.out.write("Direct launch - data dump\n");
        self.response.out.write("<a href=http://www.youtube.com/v/f90ysF9BenI>Content</a>");
    else:
        self.response.out.write(respString)

    if doHtml or doDirect:
        self.response.out.write("\n\nDebug Output:\n")
    else:
        self.response.out.write("\n\n<!--\nDebug Output:\n")

    self.response.out.write(self.dStr)

    if doHtml or doDirect:
        self.response.out.write("\n</pre>\n")
    else:
        self.response.out.write("\n-->\n")

