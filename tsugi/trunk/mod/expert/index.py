import logging
import pickle
import random

from core.tool import ToolRegistration
from core import learningportlet

from google.appengine.ext import db

class ExpertData(db.Model):
     course_key = db.StringProperty()
     user_key = db.StringProperty()
     user_name = db.StringProperty()
     data = db.StringListProperty()
     created = db.DateTimeProperty(auto_now_add=True)
     updated = db.DateTimeProperty(auto_now=True)

# Return our Registration
def register():
   return ToolRegistration(ExpertHandler, "Expert Game", """This 
application runs an experiment that measures how people use and
think about experti advice.
It is basesd on the book by Robert B. Cialdini called "Influence: Science and Practice""")

class ExpertHandler(learningportlet.LearningPortlet):

    def doaction(self):
        msg = self.check_required()
        if msg != None : return msg

        # Is this first or second round?
        if self.action == 'doguess' : 
            mod = self.get_model()
            logging.info(repr(mod.data))
            logging.info('Guess='+self.request.get('guess'))
            if ( len(mod.data[1]) == 0 ) :
                mod.data[1] = self.request.get('guess')
                mod.put()
            elif ( len(mod.data[2]) == 0 ) :
                mod.data[2] = self.request.get('guess')
                mod.put()
            else : 
                return "You only get two guesses"
            
            return None

        return None

    def getview(self, info):

        msg = self.check_required()
        if msg != None : return msg

        if self.action == 'view' and self.resource != None:
            return self.doRender(self.resource)

        if self.action == 'ready' : 
            mod = self.get_model()
            if ( len(mod.data[1]) > 0 ) : return self.doRender('thanks.htm')
            return self.doRender('ready.htm')

        if self.action == 'start' : 
            mod = self.get_model()
            group = int(mod.data[0])
            rendervars = {'group' : group}
            if ( len(mod.data[2]) > 0 ) : return self.view_index('You already have two guesses.  Any further guesses will be ignored.')
            return self.doRender('guess.htm', rendervars)

        if self.action == 'advice' : 
            mod = self.get_model()
            group = int(mod.data[0])
            advice = '180 pounds.'
            if ( group == 1 ) : advice = '185 pounds'
            rendervars = {'group' : group, 'advice': advice}
            if ( len(mod.data[2]) > 0 ) : return self.view_index('You already have two guesses.  Any further guesses will be ignored.')
            return self.doRender('guess.htm', rendervars)

        if self.action == 'doguess' : 
            mod = self.get_model()
            if ( len(mod.data[2]) > 0 ) : return self.doRender('thanks.htm')
            return self.doRender('second.htm')

        if self.action == 'data':
            if not self.context.isInstructor() : self.doRender('index.htm', 'Must be an instructor to view data.')
            que = db.Query(ExpertData)
            que = que.filter('course_key', self.context.getCourseKey())
            results = que.fetch(limit=1000)
            if len(results) > 0 :
                rendervar = {'results': results,
                             'context': self.context }
            else :
                rendervar = {'msg': 'No data has been collected yet.'} 

            return self.doRender('data.htm', rendervar)

        if self.action == 'reset':
            if not self.context.isInstructor() : self.view_index('Must be an instructor to reset data.')
            q = db.GqlQuery("SELECT __key__ FROM ExpertData WHERE course_key = :1", self.context.getCourseKey())
            results = q.fetch(1000)
            db.delete(results)
            return self.view_index('Deleted %d records.' % len(results))

        if self.action == 'resetall':
            if not self.context.isAdmin() : self.view_index('Must be an administrator to reset all data.')
            q = db.GqlQuery("SELECT __key__ FROM ExpertData") 
            results = q.fetch(1000)
            db.delete(results)
            return self.view_index('Deleted %d records.' % len(results))

        return self.view_index(info)

    def view_index(self,info):
        rendervars = {'msg': info, 'context': self.context }
        return self.doRender('index.htm',rendervars)

    # Retrieve the appropriate model
    def get_model(self) : 
        que = db.Query(ExpertData)
        que = que.filter('course_key', self.context.getCourseKey())
        que = que.filter('user_key', self.context.getUserKey())
        results = que.fetch(limit=1)
        if len(results) > 0 :
            return results[0]

        group = str(random.randint(1,2))
        newexpert = ExpertData(course_key=self.context.getCourseKey(),
            user_key=self.context.getUserKey(),
            user_name=self.context.getUserName(),
            data=[group, "", ""])
        newexpert.put()

        que = db.Query(ExpertData)
        que = que.filter('course_key', self.context.getCourseKey())
        que = que.filter('user_key', self.context.getUserKey())
        results = que.fetch(limit=1)
        if len(results) > 0 :
            return results[0]
        else :
            logging.warn("Error, unable to retrieve Expert course="+ self.context.getCourseKey() + 
                         " user=" +  self.context.getUserKey())
            return None

    # Move this into some portlet methods
    def check_required(self):
        error = "";
        if self.context.getCourseKey() == None:
            error += "This application requires a Course Key to function<br/>\n"
        if self.context.getUserKey() == None:
            error += "This application requires a User Key to function<br/>\n"
        if len(error) > 0 : 
            error += "The likely cause of this problem is improper configuration in your Learning Management System.<br/>\n"
            return error
        return None
       
