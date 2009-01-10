#!/usr/bin/env python

import os
import cgi
import logging
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
# import django.template

import launch
import dotest
from imsglobal.lti import LTI

class MainHandler(webapp.RequestHandler):

  def post(self):
    self.get()

  def get(self):
    logging.info("Hello index get")
    logging.info(self.request.path)
    l = LTI(self);
    u = l.user.displayid;
    logging.info("Put " + u)
    app = self.request.application_url
    u = l.user.email;
    logging.info("Put " + u)
    path = self.request.path
    try:
        temp = os.path.join(os.path.dirname(__file__), 'templates' + path)
        self.response.out.write(template.render(temp, {'url': app, 'path':path }))
    except:
        temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
        self.response.out.write(template.render(temp, {'url': app, 'path':path }))

def main():
  application = webapp.WSGIApplication([
     ('/dotest', dotest.DoTest),
     ('/launch.*', launch.LaunchHandler),
     ('/.*', MainHandler)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
