import logging
import os
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from util.sessions import Session
from imsglobal.lti import LTI

import dotest

from  wiscrowd.wiscrowd import wiscrowd
from  freerider.freerider import freerider

# Register all the tools - add new tools here
tools = [ wiscrowd(), freerider() ]

# New Registration Pattern - Soon to Generalize
X = __import__("mod.prisoner.index", globals(), locals(), [''])
tools.append( X.register() )


# A helper to do the rendering and to add the necessary
# variables for the _base.htm template
def doRender(self, tname = "index.htm", values = { }):
  if tname.find("_") == 0: return
  temp = os.path.join(os.path.dirname(__file__),
         'templates/' + tname)
  if not os.path.isfile(temp):
    return False

  # Make a copy of the dictionary and add the path and session
  newval = dict(values)
  newval['path'] = self.request.path

  outstr = template.render(temp, newval)
  self.response.out.write(outstr)
  return True

class LogoutHandler(webapp.RequestHandler):

  def get(self):
    self.session = Session()
    self.session.delete('lti_launch_key')
    self.session.delete('lti_launch_password')
    self.redirect("/")

class MainHandler(webapp.RequestHandler):

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
    logging.info("index.py launch="+str(lti.launch));
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

    # Check to see if the path is a portal path and handle
    # If so get the fragment and render
    for tool in tools:
      if self.request.path.startswith("/portal" + tool.path) :
         handler = tool.handler()  # make an instance to call
         handler.initialize(self.request, self.response)
         fragment = handler.markup()
         if fragment == None : return
         rendervars['fragment'] = fragment
         temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
         outstr = template.render(temp, rendervars)
         self.response.out.write(outstr)
         return

    rendervars['dash'] = "yes"

    # See if there is a template of the same name as the path
    if doRender(self, self.request.path, rendervars ) : return

    # If this is not one of our registered tools,
    # send out the main page
    temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
    outstr = template.render(temp, rendervars)
    self.response.out.write(outstr)

def main():
  # Compute the routes and add routes for the tools
  routes = [ ('/login', dotest.DoTest),
            ('/logout', LogoutHandler)]
  routes = routes + [ (x.path+".*", x.handler) for x in tools ]
  routes.append( ('/.*', MainHandler) )

  application = webapp.WSGIApplication(routes, debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
