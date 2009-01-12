import logging
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from util.sessions import Session
from imsglobal.lti import LTI

import dotest

class LogoutHandler(webapp.RequestHandler):

  def get(self):
    self.session = Session()
    self.session.delete('lti_launch_key')
    self.session.delete('lti_launch_password')
    self.redirect("/")

class MainHandler(webapp.RequestHandler):

  def prt(self,outstr):
    self.response.out.write(outstr)

  def prtln(self,outstr):
    self.response.out.write(outstr+"\n")

  def get(self):
    self.post()

  def post(self):
    # LTI Can use any session that has dictionary semantics
    self.session = Session()

    # Provision LTI.  This either (1) handles an incoming
    # launch request, (2) handles the incoming GET that
    # comes back to us after launch, or (3) if we are just
    # cruising along we load the proper launch context using
    # a session value.
    lti = LTI(self, self.session);
    
    # If the LTI code already sent a response it sets "complete"
    # so we are done
    if ( lti.complete ) : return

    self.prtln("<pre>")

    # if we don't have a launch - we are not provisioned
    if ( not lti.launch ) :
      self.prtln("LTI Runtime not started")
      self.prtln("")
      self.prtln("This tool must be launched from a ")
      self.prtln("Learning Management System (LMS) using the Simple LTI")
      self.prtln("launch protocol.")
      self.prtln("")
      self.prtln("To simulate an LMS launch go <a href=/lms>here</a>")
      self.prtln("</pre>")
      return

    # We are provisioned - lets dump some data!
    self.prtln("LTI Runtime started")
    self.prtln("<a href=/logout>Logout</a>")
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
     ('/lms', dotest.DoTest),
     ('/logout', LogoutHandler),
     ('/.*', MainHandler)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
