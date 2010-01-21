import logging
import urllib
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import memcache

class BaseContext():
  '''Extendable class with the common capabilities.'''
  dStr = ''
  launch = None
  launchkey = None
  launchprefix = 'lti_launch_key:'
  sessioncookie = True
  request = None
  complete = False

  def __init__(self, web, session = False):
    self.request = web.request
    self.complete = False
    self.session = session
    self.errormsg = None
    # If the session came from a cookie, our URLs can be simpler
    self.sessioncookie = False
    if not self.session is False:
       self.sessioncookie = self.session.foundcookie
    if not self.session is False:
       if not self.launch is None:
	  self.session["lti_launch_key"] = str(self.launchkey)
    self.handlesetup(web, session)

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
        logging.info("getting a launch="+self.launchprefix + key)
        launch = memcache.get(self.launchprefix + key)
        if launch:
            self.launch = launch
            self.launchkey = key
            # logging.info("Placing in session: %s" % key)
            if session != False: session['lti_launch_key'] = key
            return
        else:
            logging.info("Session not found in store "+key)
            if session != False and sesskey : del(session['lti_launch_key'])

    self.launch = None

  def XXgetUrlParms(self) :
    if self.launch and not self.sessioncookie :
      return { 'lti_launch_key': self.launchkey }
    else : 
      return { }

  def XXgetFormFields(self) : 
    if self.launch and not self.sessioncookie :
      return '<input type="hidden" name="lti_launch_key" value="%s">\n' % self.launchkey
    else : 
      return ' '

  def XXgetPath(self, action="", resource=False, direct=False, controller=False, context_id=False):
    '''Retrieve the raw path to a controller/action pair.   Does not handle 
    when parameters are needed when cookies are not set.  Do not use
    directly from tool code.'''
    newpath = "/"
    if not direct and ( self.request.path.startswith("/portal") or self.request.path == "/" ):
      newpath = "/portal/"

    (pathcontroller, oldact, resource) = self.XXparsePath()

    if controller:
      newpath = newpath + controller + "/"
    elif pathcontroller :
      newpath = newpath + pathcontroller + "/"

    if isinstance(context_id, str) :
      newpath = newpath + context_id + "/"
    if action and len(action) > 0 : 
      newpath = newpath + action + "/"
    return newpath

  # For now return the parameters all the time - even for the post
  def XXgetPostPath(self, action="", resource=False, direct=False, controller=False, context_id=False):
    return self.XXgetGetPath(action, resource, { }, direct, controller, context_id)

  def XXgetGetPath(self, action="", resource=False, params = {}, direct=False, controller=False, context_id=False):
    newpath = self.XXgetPath(action, resource, direct, controller, context_id)
    p = self.XXgetUrlParms()
    p.update(params)
    if len(p) > 0 : 
       newpath = newpath + '?' + urllib.urlencode(p)
    return newpath

  def XXparsePath(self):
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

  # Some utility methods
  def isInstructor(self) :
    roles = self.launch.get('roles')
    roles = roles.lower()
    if roles.find("instructor") >= 0 : return(True)
    if roles.find("administrator") >=0  : return(True)
    return False

  def isAdmin(self):
      if users.is_current_user_admin(): return True
      return False

  def getUserEmail(self):
      email = self.launch.get('lis_person_contact_email_primary')
      if ( email and len(email) > 0 ) : return email;
      # Sakai Hack
      email = self.launch.get('lis_person_contact_emailprimary')
      if ( email and len(email) > 0 ) : return email;
      return None

  def getUserShortName(self):
      email = self.getUserEmail()
      givenname = self.launch.get('lis_person_name_given')
      familyname = self.launch.get('lis_person_name_family')
      fullname = self.launch.get('lis_person_name_full')
      if ( email and len(email) > 0 ) : return email;
      if ( givenname and len(givenname) > 0 ) : return givenname;
      if ( familyname and len(familyname) > 0 ) : return familyname;
      return self.getUserName();

  def getUserName(self):
      print self.launch
      givenname = self.launch.get('lis_person_name_given')
      familyname = self.launch.get('lis_person_name_family')
      fullname = self.launch.get('lis_person_name_full')
      if ( fullname and len(fullname) > 0 ) : return fullname;
      if ( familyname and len(familyname) > 0 and givenname and len(givenname) > 0 ) : return givenname + familyname;
      if ( givenname and len(givenname) > 0 ) : return givenname;
      if ( familyname and len(familyname) > 0 ) : return familyname;
      email = self.getUserEmail()
      if ( email and len(email) > 0 ) : return email;
      return None

  def getUserKey(self):
      key = self.launch.get('oauth_consumer_key')
      id = self.launch.get('user_id')
      if ( id and key and len(id) > 0 and len(key) > 0 ) : return key + ':' + id
      return None

  def getCourseKey(self):
      key = self.launch.get('oauth_consumer_key')
      id = self.launch.get('context_id')
      if ( id and key and len(id) > 0 and len(key) > 0 ) : return key + ':' + id
      return None

  def getCourseName(self):
      label = self.launch.get('context_label')
      title = self.launch.get('context_title')
      id = self.launch.get('context_id')
      if ( label and len(label) > 0 ) : return label
      if ( title and len(title) > 0 ) : return title
      if ( id and len(id) > 0 ) : return id
      return None

  def getContextType(self):
      return self.launch.get('_launch_type')
