import logging
import os
import sys
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import users
from util import sessions
from context.context import Get_Context
from mod import *

# Register all the tools - add new tools here
tools = list()

# Register the panel tool
X = __import__("tools.panel.index", globals(), locals(), [''])
Y = X.register() 
Y.setcontroller("panel")
tools.append( Y )

# Register the lti_test
## X = __import__("tools.lti_test.index", globals(), locals(), [''])
## Y = X.register() 
## Y.setcontroller("lti_test")
## tools.append( Y )

# Loop through and register the modules
temp = os.path.join(os.path.dirname(__file__),'mod')
dirs = os.listdir(temp)

for dir in dirs:
  if len(dir) < 1 : continue
  if dir[0] == '.' : continue
  if dir[0] == '_' : continue
  X = __import__("mod."+dir+".index", globals(), locals(), [''])
  Y = X.register() 
  Y.setcontroller(dir)
  tools.append( Y )

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

  outstr = str(template.render(temp, newval))
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
    # TODO - wipe out the launch entry?
    self.session = sessions.Session(self)
    self.session.delete_item('lti_launch_key')
    user = users.get_current_user()
    if user:
        self.redirect(users.create_logout_url("/") )
    else:
        self.redirect("/")

class MainHandler(webapp.RequestHandler):

  def get(self):
    self.isget = True
    return self.service()

  def post(self):
    self.isget = False
    return self.service()

  def service(self):
    # LTI Can use any session that has dictionary semantics
    self.session = sessions.Session(self)
    # TODO: Fix this
    self.context_id = "12345"
    context = Get_Context(self, self.session)
    user = users.get_current_user()
    
    (controller, action, resource) = context.XXparsePath()
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
        rendervars['role'] = "learner"
      rendervars['dump'] = context.dump()

    rendervars['portalpath'] = context.XXgetGetPath(direct=True,controller="portal")

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
         # Warning this might mask some errors - but hey 
         # we need to convert these old apps to new style
         # portlets
         if self.isget:
             handler.setDiv('fred');
             fragment = handler.handleget()
         else:
             # If we are posting to /portal it must mean
             # Ajax is not working
             fragment = handler.handlepost()

         if fragment == None : return
         rendervars['fragment'] = fragment
         temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
         outstr = str(template.render(temp, rendervars))
         self.response.out.write(outstr)
         return

    rendervars['dash'] = "yes"

    # Copy the tools and add the Real URLs
    # WARNING - Need to copy the tool registrations !!!!!
    toolz = list()
    for tool in tools:
       if tool.controller.find("_") >= 0 : continue
       toolz.append(tool)
       tool.portalpath = context.XXgetGetPath(controller=tool.controller,context_id="12345") 
       tool.directpath = context.XXgetGetPath(direct=True,controller=tool.controller,context_id="12345") 
       # print "C=",tool.controller,"P=",tool.portalpath,"D=",tool.directpath

    rendervars['tools'] = toolz

    # See if there is a template of the same name as the path
    if doRender(self, self.request.path, rendervars ) : return

    # If this is not one of our registered tools,
    # send out the main page
    temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
    outstr = str(template.render(temp, rendervars))
    self.response.out.write(outstr)

  def requestdebug(self):
    # Drop in the request for debugging
    reqstr = self.request.path + "\n"
    for key in self.request.params.keys():
      value = self.request.get(key)
      if len(value) < 100:
         reqstr = reqstr + key+':'+value+'\n'
      else:
         reqstr = reqstr + key+':'+str(len(value))+' (bytes long)\n'
    return reqstr

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

