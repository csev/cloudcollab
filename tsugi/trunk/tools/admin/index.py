from core.tool import ToolRegistration
from core import learningportlet

# Return our Registration
def register():
   return ToolRegistration(AdminHandler, "Administration Tool", 
     """This application allows you to administer this system.""")

class AdminHandler(learningportlet.LearningPortlet):

  def getview(self, info):
    if self.context.isAdmin() : return "HELLO MASTER"
    else: return "YOU ARE NOT ADMIN"
