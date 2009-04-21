class ToolRegistration():

  def __init__(self,handler,title,desc):
    self.controller = None
    self.handler = handler
    self.title = title
    self.desc = desc

  def setcontroller(self,controller):
    self.controller = controller
