import logging
import pickle
from google.appengine.api import memcache

from core.tool import ToolRegistration
from core import learningportlet

# Return our Registration
def register():
   return ToolRegistration(WisHandler, "Wisdom of Crowds", """This 
application allows you to play games
where you are trying to determine something as 
a group by averaging many independent guesses.  
It is basesd on the book by James Surowiecki called "The Wisdom of Crowds""")

class WisHandler(learningportlet.LearningPortlet):

  def doaction(self):
    wiskey = "WisCrowd-"+str(self.context.course.key())
    data = self.getmodel(wiskey)
    logging.info("Loading Wis Key="+wiskey)

    name = self.request.get("name")
    if len(name) < 1 : name = self.context.user.email

    guess = self.request.get("guess")

    try: guess = int(guess)
    except: guess = -1

    msg = ""
    if self.context.isInstructor() and name.lower() == "reset":
       data = dict()
       logging.info("Storing Wis Key="+wiskey)
       memcache.set(wiskey, data, 3600)
       msg = "Data reset"
    elif guess < 1 :
       msg = "Please enter a valid, numeric guess"
    elif  len(name) < 1 : 
       msg = "No Name Found"
    elif name in data : 
       msg = "You already have answered this"
    elif len(data) > 1000 : 
       msg = "Game only supports 1000 players."
    else:
       data[name] = guess
       memcache.set(wiskey, data, 3600)
       logging.info("Storing Wis Key="+wiskey)
       # Retrieve and check to see if it was stored
       data = self.getmodel(wiskey)
       if data.get(name,None) == guess :
         msg = "Thank you for your guess"
       else:
         msg = "Unable to store your guess please re-submit"
         logging.warning("Failed to Store Wis Key="+wiskey)

    return msg

  def getview(self, info):
    wiskey = "WisCrowd-"+str(self.context.course.key())
    data = self.getmodel(wiskey)

    rendervars = {'context': self.context,
                  'msg' : info}
    
    if self.context.isInstructor() and len(data) > 0 :
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

    return self.doRender('index.htm', rendervars)

  def getmodel(self, wiskey):
    data =  memcache.get(wiskey)
    # If we changed the program ignore old things in the cache
    if data == None or not isinstance(data, dict):
      data = dict()
    return data
