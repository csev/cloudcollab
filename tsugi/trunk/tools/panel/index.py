import logging
from google.appengine.api import memcache
from google.appengine.ext import db
from core.tool import ToolRegistration
from core import learningportlet

# Return our Registration
def register():
     return ToolRegistration(AdminHandler, "Administration Tool", 
         """This application allows you to administer this system.""")

class AdminHandler(learningportlet.LearningPortlet):

    def doaction(self):
        logging.info("doaction="+str(self.action))
        if not self.context.isAdmin() : return "Must be admin to use this tool"
        if self.action is False : return
        if self.action == "facebook" : return self.facebook_action()
        if self.action == "purge" : return self.purge_action()
        return "Action not found " + str(self.action)
    
    def getview(self, info):
        logging.info("getview="+str(self.action))
        if not self.context.isAdmin() : return "Must be admin to use this tool"
        output = ""
        if self.action is False : output = "No action"
        if self.action == "facebook" : output =  self.facebook_view(info)
        elif self.action == "purge" : output =  self.purge_view(info)

        output = self.doRender('index.htm', {'output' : output, 'action' : self.action})
        return output

    def facebook_action(self):
        # Both these keys are provided to you when you create a Facebook Application.
        api_key = self.request.get("facebook_api_key")
        api_secret = self.request.get("facebook_api_secret")
        if len(api_key) > 0 and len(api_secret) > 0:
            memcache.add("facebook_api_key", api_key)
            memcache.replace("facebook_api_key", api_key)
            memcache.add("facebook_api_secret", api_secret)
            memcache.replace("facebook_api_secret", api_secret)
            return "Facebook API Keys stored in memcache"
        else:
            return "Facebook API Keys not stored"

    def facebook_view(self, info):
        api_key = memcache.get("facebook_api_key")
        secret_key = memcache.get("facebook_api_secret")
        if api_key :
            api_key = api_key[:2]
        if secret_key :
            secret_key = secret_key[:2]
  
        str = "Key=%s secret=%s" % ( api_key, secret_key)
        return self.doRender('facebook.htm' , { 'info': info, 'str' : str } )

    def purge_action(self): 
        limit = self.request.get("limit") 
        if not limit: 
            limit = 10 
        table = self.request.get('model') 
        if not table: 
            return 'Must specify a model.'
        q = db.GqlQuery("SELECT __key__ FROM "+table)
	results = q.fetch(10)
	db.delete(results)
        return "%s records deleted" % len(results)

    def purge_view(self, info):
        return self.doRender('purge.htm' , { 'info': info } )

