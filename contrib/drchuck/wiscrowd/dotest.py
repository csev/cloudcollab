#!/usr/bin/env python

# import cgi
import os
import wsgiref.handlers
import logging
import uuid
import hashlib
import base64
from google.appengine.ext.webapp import template
from  datetime import datetime

from google.appengine.ext import webapp

class DoTest(webapp.RequestHandler):

  def get(self):
    logging.info("DoLaunch get")
    path = os.path.join(os.path.dirname(__file__), 'templates/testform.html')
    tstime = datetime.utcnow()
    created = tstime.strftime("%Y-%m-%dT%H:%M:%SZ")
    nonce = str(uuid.uuid1())
    secret = "secret"
    presha1 = nonce + created + secret
    sha1 =  hashlib.sha1()
    sha1.update(presha1)
    x = sha1.digest()
    y = base64.b64encode(x)
    parms = { 'launchurl' : '/launch' ,
              'created' : created, 
              'nonce' : nonce, 
              'digest' : y,
              'toolid' : 'sakai.lti.168' }
    self.response.out.write(template.render(path, parms))

  def post(self):
    url = self.request.get('url')
    toolid = self.request.get('tool_id')
    if len(toolid.strip() ) < 1 :
      toolid = 'sakai.lti.168'
    logging.info("DoLaunch post url=" + url)
    path = os.path.join(os.path.dirname(__file__), 'templates/testform.html')
    tstime = datetime.utcnow()
    created = tstime.strftime("%Y-%m-%dT%H:%M:%SZ")
    nonce = str(uuid.uuid1())
    secret = "secret"
    presha1 = nonce + created + secret
    sha1 =  hashlib.sha1()
    sha1.update(presha1)
    x = sha1.digest()
    y = base64.b64encode(x)
    parms = { 'launchurl' : url,
              'created' : created, 
              'nonce' : nonce, 
              'digest' : y,
              'toolid' : toolid }
    self.response.out.write(template.render(path, parms));

