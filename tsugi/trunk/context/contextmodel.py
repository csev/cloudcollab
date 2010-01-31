from google.appengine.ext import db

class LMS_Secret(db.model):
     consumer_key = db.StringProperty()
     secret = db.StringProperty(default="")
     name = db.StringProperty()
     title = db.StringProperty()
     url = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LMS_User(db.Model):
     user_id = db.StringProperty()
     sourced_id = db.StringProperty()
     password = db.StringProperty()
     givenname = db.StringProperty()
     familyname = db.StringProperty()
     fullname = db.StringProperty()
     email = db.StringProperty()
     locale = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)
     course_scoped = db.BooleanProperty(default=False)

class LMS_Course(db.Model):
     course_id = db.StringProperty()
     type = db.StringProperty()
     sourced_id = db.StringProperty()
     secret = db.StringProperty(default="")
     code = db.StringProperty()
     name = db.StringProperty()
     title = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LMS_Membership(db.Model):
     role = db.IntegerProperty()
     user = db.ReferenceProperty(LMS_User)
     course = db.ReferenceProperty(LMS_Course)
     org = db.ReferenceProperty(LMS_Org)
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)
