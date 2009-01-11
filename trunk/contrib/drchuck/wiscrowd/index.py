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
    self.prtln("User:"+lti.getUserName())
    self.prtln("Course:"+lti.getCourseName())
    if ( lti.isInstructor() ) :
      self.prtln("Role: Instructor")
    else:
      self.prtln("Role: Sudent")
    self.prtln("")
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
