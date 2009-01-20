import logging
import os
import pickle
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import memcache

from util.sessions import Session
from imsglobal.lti import LTI

# Move this to LMS
class ToolRegistration():

  def __init__(self,path,handler,title,desc):
    self.path = path
    self.handler = handler
    self.title = title
    self.desc = desc

# Return out Registration
def freerider():
   return ToolRegistration('/freerider', FreeRiderHandler, "Free Rider", """This 
application allows you to play the "Free Rider" game as described by
James Surowiecki in the book "The Wisdom of Crowds".""")

def getactionpath(self, action="", forajax=False):
  basepath = "/freerider"
  str = self.request.path
  pos = str.find(basepath)
  newpath = str[0:pos+len(basepath)].strip()
  if len(action.strip()) > 0 :
    newpath = newpath + "/" + action
  if forajax : newpath = newpath.replace("/portal/","/")
  logging.info("New Path="+newpath)
  return newpath

def getaction(self):
  basepath = "/freerider"
  str = self.request.path
  pos = str.find(basepath)
  try: action = str[pos+len(basepath)+1:].strip()
  except: action = ""
  logging.info("Action="+action)
  return action

class FreeRiderHandler(webapp.RequestHandler):

  outStr = ""

  def getmodel(self, lti):
    freekey = "FreeRider-"+str(lti.course.key())
    logging.info("Loading Free key="+freekey)
    freerider =  memcache.get(freekey)
    if freerider == None:
      freerider = dict()
      memcache.add(freekey, freerider, 3600)
    return freerider

  def putmodel(self, freerider, lti):
    freekey = "FreeRider-"+str(lti.course.key())
    logging.info("Storing Free key="+freekey)
    memcache.replace(freekey, freerider, 3600)

  def get(self):
    istr = self.markup()
    if ( istr != None ) : self.response.out.write(istr)

  def post(self):
    istr = self.markup()
    if ( istr != None ) : self.response.out.write(istr)

  def mainscreen(self, lti):
    rendervars = {'username': lti.user.email, 
                  'course': lti.getCourseName(), 
                  'messagesaction' : getactionpath(self,"messages", True), 
                  'playaction' : getactionpath(self,"play", True), 
                  'request': self.request}

    if lti.isInstructor() : 
      rendervars['resetaction'] = getactionpath(self,"reset", True)
      rendervars['instructor'] = "yes"

    data = self.getmodel(lti)
    if ( len(data) < 4 ) :
      rendervars['joinaction'] = getactionpath(self,"join", True)

    temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
    outstr = template.render(temp, rendervars)
    return outstr

  # This method returns tool output as a string
  def markup(self):
    self.session = Session()
    lti = LTI(self, self.session);
    
    if ( lti.complete ) : return

    # if we don't have a launch - we are not provisioned
    if ( not lti.launch ) :
      temp = os.path.join(os.path.dirname(__file__), 'templates/nolti.htm')
      outstr = template.render(temp, { })
      return outstr

    action = getaction(self)
    if action == "messages" : return self.action_messages(lti)
    if action == "join" : return self.action_join(lti)
    if action == "play" : return self.action_play(lti)

    return self.mainscreen(lti)

  def action_join(self,lti) :
    data = self.getmodel(lti)
    

  def action_messages(self,lti) :
    data = self.getmodel(lti)
     
    return "Player count: "+str(len(data))

    name = self.request.get("name")
    if len(name) < 1 : name = lti.user.email

    guess = self.request.get("guess")

    try: guess = int(guess)
    except: guess = -1

    msg = ""
    if lti.isInstructor() and string.lower(name) == "reset":
       data = dict()
       freerider.blob = pickle.dumps( data ) 
       freerider.put()
       msg = "Data reset"
    elif guess < 1 :
       msg = "Please enter a valid, numeric guess"
    elif  len(name) < 1 : 
       msg = "No Name Found"
    elif name in data : 
       msg = "You already have answered this"
    else:
       ret = db.run_in_transaction(self.addname, freerider.key(), name, guess)
       if ret : 
         data = ret
         msg = "Thank you for your guess"
       else:
         msg = "Unable to store your guess please re-submit"

    rendervars = {'username': lti.user.email, 
                  'course': lti.getCourseName(), 
                  # 'msg' : msg, 
                  'request': self.request}
    if lti.isInstructor() : rendervars['instructor'] = "yes"

    if lti.isInstructor() and len(data) > 0 :
       text = ""
       total = 0
       for (key, val) in data.items(): 
         text = text + key + "," + str(val) + "\n"
         total = total + val
       count = len(data)
       ave = 0
       if count > 0 : ave = total / count
       rendervars["ave"] = ave
       rendervars["count"] = count
       rendervars["data"] = text

    temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
    outstr = template.render(temp, rendervars)
    return outstr

