import logging
import os
import sys
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.ext import db
from util import sessions
from context.aecontext import AE_Context
from context.slticontext import SLTI_Context
from context.blticontext import BLTI_Context
import facebook
from core import oauth
from core import oauth_store

bootstrap = {
  'user_locale': 'en_US',
  'user_role': 'Student',
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
    self.session = sessions.Session()
    self.session.delete('lti_launch_key')
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
    self.session = sessions.Session()

    # If the user is logged in, we construct a launch, if not, we 
    # try to provision via LTI
    user = users.get_current_user()
    if user:
      bootstrap['user_displayid'] = user.nickname()
      bootstrap['user_email'] = user.email()
      bootstrap['user_id'] = user.email()
      if users.is_current_user_admin() : bootstrap['user_role'] = "Instructor"
      context = AE_Context(self.request, bootstrap, self.session)
    else:
      # Provision LTI.  This either (1) handles an incoming
      # launch request, (2) handles the incoming GET that
      # comes back to us after launch, or (3) if we are just
      # cruising along we load the proper launch context using
      # a session value.
      context = BLTI_Context(self, self.session)
    
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

# http://dollarmani-facebook.blogspot.com/2008/09/using-facebook-api-in-python.html
class FaceBookHandler(webapp.RequestHandler):
  def get(self):
    api_key = memcache.get("facebook_api_key")
    secret_key = memcache.get("facebook_api_secret")
    if api_key :
      api_key = api_key[:2]
    if secret_key :
      secret_key = secret_key[:2]

    str = "Key=%s secret=%s" % ( api_key, secret_key)
    doRender(self, '/facebook.htm' , { 'str': str } )

  def post(self):
  # Both these keys are provided to you when you create a Facebook Application.
    api_key = self.request.get("facebook_api_key")
    api_secret = self.request.get("facebook_api_secret")
    if len(api_key) > 0 and len(api_secret) > 0:
       memcache.add("facebook_api_key", api_key)
       memcache.replace("facebook_api_key", api_key)
       memcache.add("facebook_api_secret", api_secret)
       memcache.replace("facebook_api_secret", api_secret)
       self.response.out.write("Facebook API Keys stored in memcache")
       self.get()
       return

    api_key = memcache.get("facebook_api_key")
    secret_key = memcache.get("facebook_api_secret")

    if api_secret == None or api_key == None:
       self.get()
       return

    # Initialize the Facebook Object.
    self.facebookapi = facebook.Facebook(api_key, secret_key)

    # Checks to make sure that the user is logged into Facebook.
    if self.facebookapi.check_session(self.request):
      pass
    else:
      # If not redirect them to your application add page.
      url = self.facebookapi.get_add_url()
      self.response.out.write('<fb:redirect url="' + url + '" />')
      return

    # Checks to make sure the user has added your application.
    if self.facebookapi.added:
      pass
    else:
      # If not redirect them to your application add page.
      url = self.facebookapi.get_add_url()
      self.response.out.write('<fb:redirect url="' + url + '" />')
      return

    # Get the information about the user.
    user = self.facebookapi.users.getInfo( [self.facebookapi.uid], ['uid', 'name', 'birthday', 'relationship_status'])[0]

    # Display a welcome message to the user along with all the greetings.
    self.response.out.write('Hello %s,<br>' % user['name'])
    self.response.out.write('Welcome to wiscrowd in facebook running in the cloudcollab framework.<br>')
    self.response.out.write('URL: '+self.request.path+"<br>\n")

    self.response.out.write("""
Sample Output<br/>
Info None<br/>
Path controller=sample action=False resource=False<br/>
<a href="http://apps.facebook.com/wisdom-of-crowds/sample/anchor/" class="selected">Click Me</a>
<form action="http://apps.facebook.com/wisdom-of-crowds/sample/formtag/" method="post" class="selected" id="myform">
<input type="text" name="thing" size="40">
<input type="submit" value="GO" >
</form>
""")
     
    self.response.out.write("<pre>\n"+self.requestdebug()+"</pre>")

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

class OAuthHandler(webapp.RequestHandler):
  def get(self):
    self.response.out.write("<pre>\n"+self.requestdebug()+"</pre>")
  def post(self):
    self.response.out.write("<pre>\n"+self.requestdebug()+"</pre>")
    self.oauth_server = oauth.OAuthServer(oauth_store.BasicOAuthDataStore())
    self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_PLAINTEXT())
    self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_HMAC_SHA1())

    params = self.request.params

    logging.info(self.request.url)
    # construct the oauth request from the request parameters
    oauth_request = oauth.OAuthRequest.from_request("POST", self.request.url, headers=self.request.headers, parameters=params)

    # verify the request has been oauth authorized
    try:
        consumer, token, params = self.oauth_server.verify_request(oauth_request)
        # send okay response
        self.response.out.write("<p>YAY</p>");
    except oauth.OAuthError, err:
        logging.info(err)
        self.response.out.write("<p>Boo "+err.message+"</p>");
    return

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

class PurgeHandler(webapp.RequestHandler): 
    def get(self): 
        if not users.is_current_user_admin() : 
            self.response.out.write('Must be admin.')
            return
        limit = self.request.get("limit") 
        if not limit: 
            limit = 10 
        table = self.request.get('table') 
        if not table: 
            self.response.out.write('Must specify a table.')
            return
        q = db.GqlQuery("SELECT __key__ FROM "+table)
	results = q.fetch(10)
        self.response.out.write("%s records" % len(results))
	db.delete(results)

def main():
  # Compute the routes and add routes for the tools
  routes = [ ('/login', LoginHandler),
            ('/facebook.*', FaceBookHandler),
            ('/oauth.*', OAuthHandler),
            ('/purge.*', PurgeHandler),
            ('/logout', LogoutHandler)]
  routes = routes + [ ("/"+x.controller+".*", x.handler) for x in tools ]
  routes.append( ('/.*', MainHandler) )

  application = webapp.WSGIApplication(routes, debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()

