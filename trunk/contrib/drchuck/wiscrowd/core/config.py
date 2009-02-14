
from google.appengine.ext import db

class Core_Config(db.Model):
     org_id = db.StringProperty()
     secret = db.StringProperty(default="")
     name = db.StringProperty()
     title = db.StringProperty()
     url = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class Config():

  def __init__(self,handler,title,desc):
    self.controller = None
    self.handler = handler
    self.title = title
    self.desc = desc

  def setcontroller(self,controller):
    self.controller = controller
