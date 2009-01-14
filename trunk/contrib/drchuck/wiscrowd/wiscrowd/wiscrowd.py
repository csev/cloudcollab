import logging
import os
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext import db

from util.sessions import Session
from imsglobal.lti import LTI

class Wisdom(db.Model) :
   course = db.ReferenceProperty()
   text = db.StringProperty()

# Return our list of routing URLs
def wiscrowd():
   return [ ('/wiz', WisHandler), ]

class WisHandler(webapp.RequestHandler):

  def prt(self,outstr):
    self.response.out.write(outstr)

  def prtln(self,outstr):
    self.response.out.write(outstr+"\n")

  def get(self):
    self.post()

  def post(self):
    self.session = Session()
    lti = LTI(self, self.session);
    
    if ( lti.complete ) : return

    # if we don't have a launch - we are not provisioned
    if ( not lti.launch ) :
      self.prtln("<pre>")
      self.prtln("Welcome to Wisdom of Crowds")
      self.prtln("")
      self.prtln("This tool must be launched from a ")
      self.prtln("Learning Management System (LMS) using the Simple LTI")
      self.prtln("launch protocol.")
      self.prtln("</pre>")
      return

    que = db.Query(Wisdom).filter("course =",lti.course)
    results = que.fetch(limit=1)

    if len(results) > 0 :
      wisdom = results[0]
    else:
      wisdom = Wisdom(course=lti.course, text= "")
      wisdom.put();

    text = wisdom.text
    name = self.request.get("name")
    if len(name) < 1 : 
      name = lti.user.email
    guess = self.request.get("guess")
    try:
      guess = int(guess)
    except:
      guess = -1

    msg = ""
    if lti.isInstructor() and name == "reset":
       wisdom.text = ""
       text = ""
       wisdom.put()
       msg = "Data reset"
    elif guess < 1 :
       msg = "Please enter a valid, numeric guess"
    elif  len(name) < 1 : 
       msg = "No Name Found"
    elif text.find(name+"::") >=0 :
       msg = "You already have answered this"
    else:
       if len(text) > 0 : text = text + ":::"
       text = text + name + "::" + str(guess)
       wisdom.text = text 
       wisdom.put()
       msg = "Thank you for your guess"

    rendervars = {'username': lti.user.email, 'course': lti.getCourseName(), 'msg' : msg }

    if lti.isInstructor() and len(text) > 0 :
       lines = text.split(":::")
       tot = 0.0
       count = 0
       data = ""
       for line in lines:
          words = line.split("::")
          try:
            val = int(words[1])
            tot = tot + val
            count = count + 1
            data = data + words[0] + "," + words[1] + "\n"
          except:
            continue
       ave = 0.0
       if count > 0 : ave = tot / count
       rendervars["ave"] = ave
       rendervars["count"] = count
       rendervars["data"] = data

    temp = os.path.join(os.path.dirname(__file__), 'templates/index.htm')
    outstr = template.render(temp, rendervars)
    self.response.out.write(outstr)
