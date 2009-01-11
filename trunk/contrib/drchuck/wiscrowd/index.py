#!/usr/bin/env python

import os
import cgi
import logging
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
# import django.template

import dotest
from imsglobal.lti import LTI

class MainHandler(webapp.RequestHandler):

  def prt(self,outstr):
    self.response.out.write(outstr)

  def prtln(self,outstr):
    self.response.out.write(outstr+"\n")

  def post(self):
    self.get()

  def get(self):
    lti = LTI(self);
    if ( lti.complete ) : return
    self.prtln("<pre>")
      
    if ( not lti.launch ) :
      self.prtln("LTI Runtime failed to start")
      self.prtln("</pre>")
      return

    self.prtln("LTI Runtime started")
    if ( lti.isInstructor() ) :
      self.prtln("Running as Instructor")
    else:
      self.prtln("Running as Sudent")

    u = lti.launch.resource_id;
    logging.info("MAIN " + u)
    app = self.request.application_url
    u = lti.user.email;
    logging.info("MAIN " + u)
    self.prtln(lti.dump())
    self.prtln("</pre>")

def main():
  application = webapp.WSGIApplication([
     ('/dotest', dotest.DoTest),
     ('/.*', MainHandler)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
