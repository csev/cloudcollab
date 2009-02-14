import logging
import os
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import users
from util.sessions import Session
from imsglobal.context import Context
from imsglobal.lticontext import LTI_Context

bootstrap = {
  'user_locale': 'en_US',
  'user_role': 'Instructor',
  'course_code': 'Info 101',
  'course_id': '12345',
  'course_name': 'SI101',
  'course_title': 'Introductory Informatics',
  'org_name': 'SO: Self Organization',
  'org_id': 'localhost',
  'org_title': 'The self-organizing organization.',
  'org_url': 'http://www.cloudcolab.com'}

# Register all the tools - add new tools here
tools = list()

# Register the admin tool
X = __import__("tools.admin.index", globals(), locals(), [''])
Y = X.register() 
Y.setcontroller("admin")
tools.append( Y )

# Register the lti_test
X = __import__("tools.lti_test.index", globals(), locals(), [''])
Y = X.register() 
Y.setcontroller("lti_test")
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
      self.redirect("/")
    else:
      self.redirect(users.create_login_url("/"))
      return

class LogoutHandler(webapp.RequestHandler):

  def get(self):
    # Logout if we came in via launch
    self.session = Session()
    self.session.delete('lti_launch_key')
    user = users.get_current_user()
    if user:
        self.redirect(users.create_logout_url("/") )
    else:
        self.redirect("/")

class MainHandler(webapp.RequestHandler):

  def get(self):
    self.post()

  def post(self):
    # LTI Can use any session that has dictionary semantics
    self.session = Session()

    # If the user is logged in, we construct a launch, if not, we 
    # try to provision via LTI
    user = users.get_current_user()
    if user:
      bootstrap['user_displayid'] = user.nickname()
      bootstrap['user_email'] = user.email()
      bootstrap['user_id'] = user.email()
      context = Context(self.request, bootstrap, self.session)
    else:
      # Provision LTI.  This either (1) handles an incoming
      # launch request, (2) handles the incoming GET that
      # comes back to us after launch, or (3) if we are just
      # cruising along we load the proper launch context using
      # a session value.
      context = LTI_Context(self, self.session)
    
      # If the LTI code already sent a response it sets "complete"
      # so we are done
      if ( context.complete ) : return

    (controller, action, resource) = context.parsePath()
    # print "POST", context.getPostPath()
    # print "GET", context.getGetPath()


    rendervars = { 'user' : user, 'path': self.request.path, 
                   'context' : context,
                   'logouturl': users.create_logout_url("/") }

    logging.info("index.py launch="+str(context.launch));
    if context.launch :
      if ( context.user ) : rendervars['user'] = context.user
      rendervars['username'] = context.getUserName()
      rendervars['coursename'] = context.getCourseName()
      if ( context.isInstructor() ) :
        rendervars['role'] = "instructor"
      else:
        rendervars['role'] = "student"
      rendervars['dump'] = context.dump()

    rendervars['portalpath'] = context.getGetPath(direct=True,controller="portal")

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
         try:
             X = __import__("mod."+controller+".index", globals(), locals(), [''])
             if X != None:
                 tool = X.register()
                 tool.controller(controller)
         except:
              pass

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

    # Copy the tools and add the Real URLs
    # WARNING - Need to copy the tool registrations !!!!!
    toolz = list()
    for tool in tools:
       if tool.controller.find("_") >= 0 : continue
       toolz.append(tool)
       tool.portalpath = context.getGetPath(controller=tool.controller)
       tool.directpath = context.getGetPath(direct=True,controller=tool.controller)
       # print "C=",tool.controller,"P=",tool.portalpath,"D=",tool.directpath

    rendervars['tools'] = toolz

    # See if there is a template of the same name as the path
    if doRender(self, self.request.path, rendervars ) : return

    # If this is not one of our registered tools,
    # send out the main page
    temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
    outstr = template.render(temp, rendervars)
    self.response.out.write(outstr)

def main():
  # Compute the routes and add routes for the tools
  routes = [ ('/login', LoginHandler),
            ('/logout', LogoutHandler)]
  routes = routes + [ ("/"+x.controller+".*", x.handler) for x in tools ]
  routes.append( ('/.*', MainHandler) )

  application = webapp.WSGIApplication(routes, debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
