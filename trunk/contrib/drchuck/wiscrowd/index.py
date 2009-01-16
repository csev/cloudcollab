import logging
import os
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from util.sessions import Session
from imsglobal.lti import LTI

import dotest

from  wiscrowd.wiscrowd import wiscrowd

tools = [ wiscrowd() ]

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
    lti = LTI(self, self.session)
    
    # If the LTI code already sent a response it sets "complete"
    # so we are done
    if ( lti.complete ) : return

    rendervars = { 'path': self.request.path }
    if lti.launch :
      if ( lti.user ) : rendervars['user'] = lti.user
      rendervars['tools'] = tools
      rendervars['username'] = lti.getUserName()
      rendervars['coursename'] = lti.getCourseName()
      if ( lti.isInstructor() ) :
        rendervars['role'] = "instructor"
      else:
        rendervars['role'] = "student"
      rendervars['dump'] = lti.dump()

    temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
    outstr = template.render(temp, rendervars)
    self.response.out.write(outstr)

def main():
  # Compute the routes and add routes for the tools
  routes = [ ('/login', dotest.DoTest),
            ('/logout', LogoutHandler)]
  routes = routes + [ (x.path, x.handler) for x in tools ]
  routes.append( ('/.*', MainHandler) )

  application = webapp.WSGIApplication(routes, debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
