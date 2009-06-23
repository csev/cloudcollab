from google.appengine.ext import db

class LMS_Org(db.Model):
     org_id = db.StringProperty()
     sourced_id = db.StringProperty()
     secret = db.StringProperty(default="")
     name = db.StringProperty()
     title = db.StringProperty()
     url = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)
     course_scoped = db.BooleanProperty(default=False)

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
     sourced_id = db.StringProperty()
     secret = db.StringProperty(default="")
     code = db.StringProperty()
     name = db.StringProperty()
     title = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

# Organiztions that are scoped to a course
# It would be nice to extend LMS_Org here - but it causes problems 
class LMS_CourseOrg(db.Model):
     course = db.ReferenceProperty(LMS_Course, collection_name='orgs')
     # copied from LMS_Org
     org_id = db.StringProperty()
     sourced_id = db.StringProperty()
     name = db.StringProperty()
     title = db.StringProperty()
     url = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)
     course_scoped = db.BooleanProperty(default=True)

# Users that are scoped to a course
# It would be nice to extend LMS_User here - but it causes problems 
class LMS_CourseUser(db.Model):
     course = db.ReferenceProperty(LMS_Course, collection_name='users')
     # Copied from LMS_User
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
     course_scoped = db.BooleanProperty(default=True)

# Many to many mappings from Organizations to Courses
class LMS_OrgCourse(db.Model):
     org = db.ReferenceProperty(LMS_Org, collection_name='courses')
     course = db.ReferenceProperty(LMS_Course)

class LMS_Membership(db.Model):
     role = db.IntegerProperty()
     roster = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LMS_Digest(db.Model):
     digest = db.StringProperty()
     request = db.TextProperty()
     debug = db.TextProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LMS_Launch(db.Model):
     user = db.ReferenceProperty(LMS_User)
     course = db.ReferenceProperty(LMS_Course)
     org = db.ReferenceProperty(LMS_Org)
     memb = db.ReferenceProperty(LMS_Membership)
     # For course scoped org and user
     course_user = db.ReferenceProperty(LMS_CourseUser)
     course_org = db.ReferenceProperty(LMS_CourseOrg)
     resource_id = db.StringProperty()
     targets = db.StringProperty()
     resource_url = db.StringProperty()
     width = db.StringProperty()
     height = db.StringProperty()
