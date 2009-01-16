import logging
import os
import pickle
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext import db

from util.sessions import Session
from imsglobal.lti import LTI

class Wisdom(db.Model) :
   course = db.ReferenceProperty()
   blob = db.BlobProperty()

# Return our list of routing URLs
def wiscrowd():
   return [ ('/wiz', WisHandler), ]

class WisHandler(webapp.RequestHandler):

  def get(self):
    self.post()

  def post(self):
    self.session = Session()
    lti = LTI(self, self.session);
    
    if ( lti.complete ) : return

    # if we don't have a launch - we are not provisioned
    if ( not lti.launch ) :
      temp = os.path.join(os.path.dirname(__file__), 'templates/nolti.htm')
      outstr = template.render(temp, { })
      self.response.out.write(outstr)
      return

    que = db.Query(Wisdom).filter("course =",lti.course)
    results = que.fetch(limit=1)

    if len(results) > 0 :
      wisdom = results[0]
    else:
      wisdom = Wisdom(course=lti.course, blob= pickle.dumps( dict() ) )
      wisdom.put();

    data = pickle.loads(wisdom.blob)
    name = self.request.get("name")
    if len(name) < 1 : name = lti.user.email

    guess = self.request.get("guess")

    try: guess = int(guess)
    except: guess = -1

    msg = ""
    if lti.isInstructor() and name == "reset":
       data = dict()
       wisdom.blob = pickle.dumps( data ) 
       wisdom.put()
       msg = "Data reset"
    elif guess < 1 :
       msg = "Please enter a valid, numeric guess"
    elif  len(name) < 1 : 
       msg = "No Name Found"
    elif name in data : 
       msg = "You already have answered this"
    else:
       ret = db.run_in_transaction(self.addname, wisdom.key(), name, guess)
       if ret : 
         data = ret
         msg = "Thank you for your guess"
       else:
         msg = "Unable to store your guess please re-submit"

    rendervars = {'username': lti.user.email, 
                  'course': lti.getCourseName(), 
                  'msg' : msg, 
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
    self.response.out.write(outstr)

  def addname(self, key, name, guess):
    obj = db.get(key)
    data = pickle.loads(obj.blob)
    if ( len(data) > 499 ) : return data
    data[name] = guess
    obj.blob = pickle.dumps(data)
    obj.put()
    return data
