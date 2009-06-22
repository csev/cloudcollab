import logging
import urllib
from google.appengine.ext import db
from google.appengine.api import users

from contextmodel import *
from core.modelutil import *

class Context():
  '''Extendable class with the common capabilities.'''
  dStr = ''
  launch = None
  sessioncookie = True
  user = None
  course = None
  memb = None
  org = None
  request = None
  complete = False

  def __init__(self, request, params, session = False):
    self.request = request
    self.complete = False
    self.session = session
    # If the session came from a cookie, our URLs can be simpler
    self.sessioncookie = False
    if not self.session is False:
       self.sessioncookie = self.session.foundcookie
    self.buildlaunch(params)
    if not self.session is False:
       if not self.launch is None:
	  self.session["lti_launch_key"] = str(self.launch.key())

  def setvars(self):
    self.user = None
    self.course = None
    self.memb = None
    self.org = None
    if self.launch : 
      if self.launch.user : self.user = self.launch.user
      if self.launch.course_user : self.user = self.launch.course_user
      if self.launch.course : self.course = self.launch.course
      if self.launch.memb : self.memb = self.launch.memb
      if self.launch.course_org : self.org = self.launch.course_org
      if self.launch.org : self.org = self.launch.org

  # If we are going to forward back to ourselves, this handles
  # The clever bits about establishing the key from the URL 
  # or session - It is not used in this base class because
  # setup is completely done from parms that come from elsewhere
  # on each request
  def handlesetup(self, web, session):
    # get values form the request
    key = web.request.get('lti_launch_key')
    if ( len(key) <= 0 ) : key = None

    sesskey = None
    self.sessioncookie = False
    if session != False:
      sesskey = session.get('lti_launch_key', None)
      if key and sesskey and key == sesskey:
        self.sessioncookie = True
        # logging.info("Session and URL Key Match cookies are working...")
      elif sesskey and not key:
        self.sessioncookie = True
        key = sesskey
        # logging.info("Taking key from session ...")

    # On a normal request there are no parammeters - we just use session
    if ( key ) :
      # Need try/except in case Key() is unhappy with the string
      try:
        launch = LTI_Launch.get(db.Key(key))
      except:
        launch = None

      if launch:
        if session != False: session['lti_launch_key'] = key
        # logging.info("Placing in session: %s" % key)
      else:
        logging.info("Session not found in store "+key)
        if session != False and sesskey : del(session['lti_launch_key'])

      self.launch = launch
      self.setvars()
      return

    self.launch = None
    self.setvars()

  def getUrlParms(self) :
    if self.launch and not self.sessioncookie :
      return { 'lti_launch_key': self.launch.key() }
    else : 
      return { }

  def getFormFields(self) : 
    if self.launch and not self.sessioncookie :
      return '<input type="hidden" name="lti_launch_key" value="%s">\n' % self.launch.key()
    else : 
      return ' '

  def getPath(self, action="", resource=False, direct=False, controller=False):
    '''Retrieve the raw path to a controller/action pair.   Does not handle 
    when parameters are needed when cookies are not set.  Do not use
    directly from tool code.'''
    newpath = "/"
    if not direct and ( self.request.path.startswith("/portal") or self.request.path == "/" ):
      newpath = "/portal/"

    (pathcontroller, oldact, resource) = self.parsePath()

    if controller:
      newpath = newpath + controller + "/"
    elif pathcontroller :
      newpath = newpath + pathcontroller + "/"

    if action and len(action) > 0 : 
      newpath = newpath + action + "/"
    return newpath

  # For now return the parameters all the time - even for the post
  def getPostPath(self, action="", resource=False, direct=False, controller=False):
    return self.getGetPath(action, resource, { }, direct, controller)

  def getGetPath(self, action="", resource=False, params = {}, direct=False, controller=False):
    newpath = self.getPath(action, resource, direct, controller)
    p = self.getUrlParms()
    p.update(params)
    if len(p) > 0 : 
       newpath = newpath + '?' + urllib.urlencode(p)
    return newpath

  def parsePath(self):
    '''Returns a tuple which is the controller, action and the rest of the path.
    The "rest of the path" does not start with a slash.'''
    action = False
    controller = False
    resource = False
    str = self.request.path
    words = str.split("/")
    if len(words) > 0 and len(words[0]) < 1 :
       del words[0]
    if len(words) > 0 and words[0] == "portal" :
       del words[0]
    if len(words) > 0 :
       controller = words[0]
       del words[0]
    if len(words) > 0 :
       action = words[0]
       del words[0]
    if len(words) > 0 :
       remainder = "/".join(words)
    # print "Cont=",controller," Act=",action," Resource=",resource
    return (controller, action, resource)

  def debug(self, str):
    logging.info(str)
    self.dStr = self.dStr + str + "\n"

  def getDebug(self):
    return dStr

  def dump(self):
    ret = "Dump of LTI Object\n";
    if ( not self.launch ):
      ret = ret + "No launch data\n"
      return ret
    ret = ret + "Complete = "+str(self.complete) + "\n";
    ret = ret + Model_Dump(self.user)
    ret = ret + Model_Dump(self.course)
    ret = ret + Model_Dump(self.memb)
    ret = ret + Model_Dump(self.org)
    ret = ret + Model_Dump(self.launch)

    return ret

  def requestdebug(self, web):
    # Drop in the request for debugging
    reqstr = web.request.path + "\n"
    for key in web.request.params.keys():
      value = web.request.get(key)
      if len(value) < 100: 
         reqstr = reqstr + key+':'+value+'\n'
      else: 
         reqstr = reqstr + key+':'+str(len(value))+' (bytes long)\n'
    return reqstr

  # Some utility mehtods
  def isInstructor(self) :
    if self.launch and self.memb :
      return (self.memb.role == 2)
    else : 
      return False

  def isAdmin(self):
      if users.is_current_user_admin(): return True
      return False

  def getUserName(self):
     if ( not ( self.launch and self.user ) ) : return "Anonymous"
     if ( self.user.fullname and len(self.user.fullname) > 0) : return self.user.fullname
     retval = ""
     if ( self.user.givenname and self.user.familyname and len(self.user.givenname) > 0 and len(self.user.familyname) > 0) : 
        return self.user.givenname + " " + self.user.familyname
     elif ( self.user.givenname and len(self.user.givenname) > 0) : return self.user.givenname
     elif ( self.user.familyname and len(self.user.familyname) > 0) : return self.user.familyname
     if ( self.user.email and len(self.user.email) > 0) : return self.user.email
     return ""

  def getCourseName(self):
     if ( not ( self.launch and self.course ) ) : return "None"
     if ( self.course.name ) : return self.course.name
     if ( self.course.title ) : return self.course.title
     if ( self.course.code ) : return self.course.code
     return ""

