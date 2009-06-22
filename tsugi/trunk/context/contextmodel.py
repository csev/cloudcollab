from google.appengine.ext import db

class LTI_Org(db.Model):
     org_id = db.StringProperty()
     sourced_id = db.StringProperty()
     secret = db.StringProperty(default="")
     name = db.StringProperty()
     title = db.StringProperty()
     url = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)
     course_scoped = db.BooleanProperty(default=False)

class LTI_User(db.Model):
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

class LTI_Course(db.Model):
     course_id = db.StringProperty()
     sourced_id = db.StringProperty()
     secret = db.StringProperty(default="")
     code = db.StringProperty()
     name = db.StringProperty()
     title = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

# Organiztions that are scoped to a course
# It would be nice to extend LTI_Org here - but it causes problems 
class LTI_CourseOrg(db.Model):
     course = db.ReferenceProperty(LTI_Course, collection_name='orgs')
     # copied from LTI_Org
     org_id = db.StringProperty()
     sourced_id = db.StringProperty()
     name = db.StringProperty()
     title = db.StringProperty()
     url = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)
     course_scoped = db.BooleanProperty(default=True)

# Users that are scoped to a course
# It would be nice to extend LTI_User here - but it causes problems 
class LTI_CourseUser(db.Model):
     course = db.ReferenceProperty(LTI_Course, collection_name='users')
     # Copied from LTI_User
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
class LTI_OrgCourse(db.Model):
     org = db.ReferenceProperty(LTI_Org, collection_name='courses')
     course = db.ReferenceProperty(LTI_Course)

class LTI_Membership(db.Model):
     role = db.IntegerProperty()
     roster = db.StringProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_Digest(db.Model):
     digest = db.StringProperty()
     request = db.TextProperty()
     debug = db.TextProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

class LTI_Launch(db.Model):
     user = db.ReferenceProperty(LTI_User)
     course = db.ReferenceProperty(LTI_Course)
     org = db.ReferenceProperty(LTI_Org)
     memb = db.ReferenceProperty(LTI_Membership)
     # For course scoped org and user
     course_user = db.ReferenceProperty(LTI_CourseUser)
     course_org = db.ReferenceProperty(LTI_CourseOrg)
     resource_id = db.StringProperty()
     targets = db.StringProperty()
     resource_url = db.StringProperty()
     width = db.StringProperty()
     height = db.StringProperty()
