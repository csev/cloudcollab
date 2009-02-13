import logging
import os
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import users
from util.sessions import Session
from imsglobal.lti import Context

import dotest

# Register all the tools - add new tools here
tools = list()

# Register the adimin tool
X = __import__("admin.index", globals(), locals(), [''])
Y = X.register() 
Y.setcontroller("admin")
tools.append( Y )

# Loop through and register the modules
temp = os.path.join(os.path.dirname(__file__),'mod')
dirs = os.listdir(temp)

for dir in dirs:
  if len(dir) < 1 : continue
  if dir[0] == '.' : continue
  if dir[0] == '_' : continue
  try:
    X = __import__("mod."+dir+".index", globals(), locals(), [''])
    Y = X.register() 
    Y.setcontroller(dir)
    tools.append( Y )
  except:
    pass

# TODO: Memcache the tool list!  Sweet!

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
    lti = Context(self, self.session)
    
    # If the LTI code already sent a response it sets "complete"
    # so we are done
    if ( lti.complete ) : return

    (controller, action, rest) = lti.parsePath()
    # print "POST", lti.getPostPath()
    # print "GET", lti.getGetPath()
    rendervars = { 'path': self.request.path, 'logouturl': users.create_logout_url("/") }

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
    tool = None
    for toolreg in tools:
        if controller == toolreg.controller :
            tool = toolreg
            break

    # Dyn-O-Register!
    if tool == None and controller :
         # Load the module!
         X = __import__("mod."+controller+".index", globals(), locals(), [''])
         if X != None:
             tool = X.register()
             tool.controller(controller)

    # Dispatch the request to the tool's handler
    if tool != None : 
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
  routes = routes + [ ("/"+x.controller+".*", x.handler) for x in tools ]
  routes.append( ('/.*', MainHandler) )

  application = webapp.WSGIApplication(routes, debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
