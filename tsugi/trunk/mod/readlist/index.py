import logging
import pickle
from google.appengine.ext import db
from core.tool import ToolRegistration
from core import learningportlet
from google.appengine.api import memcache

class Reading(db.Model) :
   blob = db.BlobProperty()

# Return our Registration
def register():
   return ToolRegistration(ReadListHandler, "The ReadList Tool (ReadList v. 1)", "This application allows you to build a communal reading list of links with your classmates as you surf the web. No AJAX; that's in version 2, below.")

class ReadListHandler(learningportlet.LearningPortlet):

  def doaction(self):

    reading = Reading.get_or_insert("a", parent=self.context.course)
    if reading.blob == None : 
      reading.blob = pickle.dumps( dict() ) 
      reading.put()

    data = pickle.loads(reading.blob)
    title = self.request.get("title")
    URL = self.request.get("URL")
    
    msg = ""
    # Secret list reset for instructors only
    if self.context.isInstructor() and URL.lower() == "reset":
       data = dict()
       reading.blob = pickle.dumps( data ) 
       reading.put()
       msg = "Data reset."
    elif len(title) < 1 :
       msg = "Please enter a valid title."
    elif len(URL) < 1 :
       msg = "Please enter a URL or URL name."
# This part isn't working    
    #elif title in data : 
    #   msg = "This title has already been added."
# Also, make sure preused title or URL doesn't overwrite older data
    else:
       ret = db.run_in_transaction(self.addURL, reading.key(), URL, title)
       if ret : 
         data = ret
         msg = "Thank you for your adding to the list!"
	 if len(title) > 0:
		 return 'Thank you for adding <em><strong>%s</strong></em> to the list!' % title
       else:
         msg = "Unable to store your title; please re-submit."

    return msg

  def getview(self, info):
    reading = Reading.get_or_insert("a", parent=self.context.course)
    if reading.blob == None : 
      reading.blob = pickle.dumps( dict() ) 
      reading.put()

    data = pickle.loads(reading.blob)
    rendervars = {'context': self.context,
                  'msg' : info}

    if self.context.isInstructor() and len(data) > 0 :
       text = ""
       for (key, val) in data.items(): 
         text = text + val + ", " + key + "\n"
         rendervars["data"] = text

    logging.info(data.items())
    rendervars["datalist"]=data
    return self.doRender('index.htm', rendervars)

  def addURL(self, key, URL, title):
    obj = db.get(key)
    data = pickle.loads(obj.blob)
    if ( len(data) > 5000 ) : return data
    data[URL] = title
    obj.blob = pickle.dumps(data)
    obj.put()
    return data
