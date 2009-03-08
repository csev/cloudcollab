import logging
import os
import pickle
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext import db

from util.sessions import Session
from imsglobal.lticontext import LTI_Context
from core.tool import ToolRegistration

class Wisdom(db.Model) :
   blob = db.BlobProperty()

# Return our Registration
def register():
   return ToolRegistration(WisHandler, "Wisdom of Crowds", """This 
application allows you to play games
where you are trying to determine something as 
a group by averaging many independent guesses.  
It is basesd on the book by James Surowiecki called "The Wisdom of Crowds""")

class WisHandler(webapp.RequestHandler):

  outStr = ""

  def get(self):
    istr = self.markup()
    if ( istr != None ) : self.response.out.write(istr)

  def post(self):
    istr = self.markup()
    if ( istr != None ) : self.response.out.write(istr)

  # This method returns tool output as a string
  def markup(self):
    self.session = Session()
    context = LTI_Context(self, self.session);
    
    if ( context.complete ) : return

    # if we don't have a launch - we are not provisioned
    if ( not context.launch ) :
      temp = os.path.join(os.path.dirname(__file__), 'templates/nolti.htm')
      outstr = template.render(temp, { })
      return outstr

    wisdom = Wisdom.get_or_insert("a", parent=context.course)
    if wisdom.blob == None : 
      wisdom.blob = pickle.dumps( dict() ) 
      wisdom.put()

    data = pickle.loads(wisdom.blob)
    name = self.request.get("name")
    if len(name) < 1 : name = context.user.email

    guess = self.request.get("guess")

    try: guess = int(guess)
    except: guess = -1

    msg = ""
    if context.isInstructor() and name.lower() == "reset":
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

    rendervars = {'context': context,
                  'msg' : msg}
    
    if context.isInstructor() and len(data) > 0 :
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

  def addname(self, key, name, guess):
    obj = db.get(key)
    data = pickle.loads(obj.blob)
    if ( len(data) > 499 ) : return data
    data[name] = guess
    obj.blob = pickle.dumps(data)
    obj.put()
    return data