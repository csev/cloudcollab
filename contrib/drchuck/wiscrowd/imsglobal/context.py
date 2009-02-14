import logging
import urllib
from google.appengine.ext import db
from google.appengine.api import users

from contextmodel import *
from core.modelutil import *

class Context():
  '''Build a launch from parameters.'''
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
    self.sessioncookie = False
    self.session = session
    self.buildlaunch(params)

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

  def buildlaunch(self, params):
    course_id = params.get("course_id")
    user_id = params.get("user_id")
    org_id = params.get("org_id")
    role = params.get("user_role")

    org = None
    course = None
    user = None
    if len(org_id) > 0 :
      org = LTI_Org.get_or_insert("key:"+org_id)
      Model_Load2(org, params, "org_")
      org.put()

    if len(course_id) > 0 and org :
      course = LTI_Course.get_or_insert("key:"+course_id, parent=org)
      Model_Load2(course, params, "course_")
      course.put()

    if ( len(user_id) > 0 ) and org :
      user = LTI_User.get_or_insert("key:"+user_id, parent=org)
      Model_Load2(user, params, "user_")
      user.put()

    memb = None
    if user and course :
      memb = LTI_Membership.get_or_insert("key:"+user_id, parent=course)
      if ( len(role) < 1 ) : role = "Student"
      role = role.lower()
      roleval = 1;
      if ( role == "instructor") : roleval = 2
      if ( role == "administrator") : roleval = 2
      memb.role = roleval
      memb.put()

    launch = LTI_Launch.get_or_insert("key:"+user_id, parent=course)
    Model_Load2(launch, params, "launch_")
    launch.memb = memb
    launch.org = org
    launch.user = user
    launch.course = course
    launch.put()
    self.debug("launch.key()="+str(launch.key()))

    self.complete = True
    self.launch = launch
    self.user = user
    self.course = course
    self.org = org
    self.memb = memb

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
     if ( self.user.displayid and len(self.user.displayid) > 0) : return self.user.displayid
     retval = ""
     if ( self.user.firstname and self.user.lastname and len(self.user.firstname) > 0 and len(self.user.lastname) > 0) : 
        return self.user.firstname + " " + self.user.lastname
     elif ( self.user.firstname and len(self.user.firstname) > 0) : return self.user.firstname
     elif ( self.user.lastname and len(self.user.lastname) > 0) : return self.user.lastname
     if ( self.user.email and len(self.user.email) > 0) : return self.user.email
     return ""

  def getCourseName(self):
     if ( not ( self.launch and self.course ) ) : return "None"
     if ( self.course.name ) : return self.course.name
     if ( self.course.title ) : return self.course.title
     if ( self.course.code ) : return self.course.code
     return ""

