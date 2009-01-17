#!/usr/bin/env python

import os
import cgi
import logging
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.api import urlfetch
from mdom import *
import httplib, urllib
from  datetime import datetime, timedelta
import hashlib, base64
import uuid
from google.appengine.ext import db

class User(db.Model):
  email = db.EmailProperty()
  firstname = db.StringProperty()
  lastname = db.StringProperty()

def doRender(self, tname = "index.htm", values = { }):
    logging.info(tname)
    if tname == '/':
      tname = 'index.htm'
    temp = os.path.join(os.path.dirname(__file__), 'templates/' + tname)
    if not os.path.isfile(temp):
      return False

    # Make a copy of the dictionary and add basic values
    newval = dict(values)
    if not 'path' in newval:
        path = self.request.path
        newval['path'] = self.request.path

    user = users.get_current_user()
    if user:
      newval['user'] = user
      newval['logouturl'] = users.create_logout_url("/")

    outstr = template.render(temp, newval)
    self.response.out.write(outstr)
    return True

class LoginHandler(webapp.RequestHandler):

  def get(self):
    user = users.get_current_user()

    if user:
      pass
    else:
      self.redirect(users.create_login_url(self.request.uri))
      return

    que = db.Query(User).filter("email =",user.email())
    results = que.fetch(limit=1)
    if len(results) > 0 :
      doRender(self, 'welcome.htm', 
               { 'message' : 'Welcome back - You may update your info or press "Continue"', 
                                'userobj': results[0]})
    else:
      doRender(self, 'welcome.htm', { 'message' : 'Please enter your first and last name'})

  def post(self):
    user = users.get_current_user()

    if user:
      pass
    else:
      self.redirect(users.create_login_url(self.request.uri))
      return

    fname = self.request.get('firstname')
    lname = self.request.get('lastname')

    # Check for a user already existing
    que = db.Query(User).filter("email =",user.email())
    results = que.fetch(limit=1)

    if len(results) > 0 :
      userobj = results[0]
    else:
      userobj = User(email = user.email())

    userobj.firstname = fname
    userobj.lastname = lname
    userobj.put()
    doRender(self,'courses.htm')
  
class LaunchHandler(webapp.RequestHandler):

  def get(self):
    user = users.get_current_user()

    if user:
      pass
    else:
      self.redirect(users.create_login_url(self.request.uri))
      return

    url = self.request.get('url')
    role = self.request.get('role')
    course = self.request.get('course')
    if len(course) < 1 : course = "cloud123"

    # Sending - Make a Simple TI TimeStamp
    tstime = datetime.utcnow()
    timestamp = tstime.strftime("%Y-%m-%dT%H:%M:%SZ")

    nonce = str(uuid.uuid4());
    secret = "secret"
    presha1 = nonce + timestamp + secret
    sha1 =  hashlib.sha1()
    sha1.update(presha1)
    x = sha1.digest()
    digest = base64.b64encode(x)
    if role != "":
      role = "Instructor"
    else:
      role = "Student"

    # Check for a user already existing
    que = db.Query(User).filter("email =",user.email())
    results = que.fetch(limit=1)

    firstname = "Unknown"
    lastname = "Unknown"
    key = 'unknown'
    if len(results) > 0 :
      userobj = results[0]
      firstname = userobj.firstname
      lastname = userobj.lastname
      key = str(userobj.key())
    
    form_data = urllib.urlencode({
        'action': "launchresolve",
        'sec_nonce': nonce,
        'sec_created': timestamp,
        'sec_digest': digest,
        'user_id': key,
        'user_role': role,
        'user_displayid': user.nickname(),
        'user_email': user.email(),
        'user_firstname': firstname,
        'user_lastname': lastname,
        'course_id': course,
        'course_title': course,
        'course_name': course,
        'launch_targets': "iframe",
        'launch_resource_id': "27b2066ac545" })

    result = urlfetch.fetch(url=url,
                        payload=form_data,
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'})

    if result.status_code == 200:
       map = mdom_parse(result.content)
       rurl = None
       if map : rurl = map.get("/launchResponse/launchUrl",None)
       if rurl != None:
          forward = self.request.get('forward')
          if forward != "":
             pos = rurl.find('?')
             if pos > 0 :
                rurl = rurl + '&'
             else :
                rurl = rurl + '?'
	     rurl = rurl + "forward=" + forward
	     rurl = rurl + "&cs_forward=" + forward
	     rurl = rurl + "&cs_course=" + course
          logging.info("Launching email="+user.email()+" key="+key+" url="+rurl)
          self.redirect(rurl)
          return

    self.response.out.write("Failed web service call:\n")
    self.response.out.write("Response code="+str(result.status_code)+"\n")
    self.response.out.write("Content:\n"+result.content+"\n")
    self.response.out.write("Form Data:\n"+form_data+"\n")

class ZapHandler(webapp.RequestHandler):

  def get(self):
    user = users.get_current_user()

    if user:
      self.response.headers['Content-Type'] = 'text/plain'
      self.response.out.write('Hello, ' + user.nickname())
    else:
      self.redirect(users.create_login_url(self.request.uri))
      return

    # Sending - Make a Simple TI TimeStamp
    tstime = datetime.utcnow()
    print "Current UTC Time", tstime
    timestamp = tstime.strftime("%Y-%m-%dT%H:%M:%SZ")
    print "Sending SimpleLTI TimeStamp", timestamp
    
    # Receiving - Parse a Simple TI TimeStamp
    tock = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    print "Parsed SimpleLTI TimeStamp", tock


    nonce = str(uuid.uuid4());
    secret = "secret"
    presha1 = nonce + timestamp + secret
    print("Presha1 " + presha1)
    sha1 =  hashlib.sha1()
    sha1.update(presha1)
    x = sha1.digest()
    digest = base64.b64encode(x)
    print("digest "+digest)

    
    form_data = urllib.urlencode({
        'action': "launchresolve",
        'sec_nonce': nonce,
        'sec_created': timestamp,
        'sec_digest': digest,
        'user_id': "0ae836b9-7fc9-4060-006f-27b2066ac545",
        'user_role': "Instructor",
        'user_displayid': user.nickname(),
        'user_email': user.email(),
        'course_id': "8213060-006f-27b2066ac545",
        'course_name': "SI300",
        'launch_targets': "iframe",
        'launch_resource_id': "27b2066ac545" })

    url = 'http://simplelti.appspot.com/launch'
    result = urlfetch.fetch(url=url,
                        payload=form_data,
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    if result.status_code == 200:
      print result.content

class MainHandler(webapp.RequestHandler):

  def get(self):
    hostname = self.request.host
    if hostname.find("appspot") > 0 :
       self.redirect("http://www.cloudcollab.com/")
       return
    logging.info('host'+self.request.host)
    app = self.request.application_url
    path = self.request.path
    if doRender(self,path):
      return
    doRender(self, 'index.htm',{ 'error': 'Missing template for '+path})

def main():
  application = webapp.WSGIApplication([
     ('/zap', ZapHandler),
     ('/launch', LaunchHandler),
     ('/login', LoginHandler),
     ('/.*', MainHandler)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
