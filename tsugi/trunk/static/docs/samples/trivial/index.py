import logging
from core import tool
from core import learningportlet

def register():
   return tool.ToolRegistration(TrivialHandler, 
     'Trivial Tool', 
     'This tool is very very trivial')

class TrivialHandler(learningportlet.LearningPortlet):

  def update(self):
    logging.info("doAction action=%s" % self.action)
    if self.action == 'reset':
      self.session.delete_item('guesses')
      return 'Guess count reset!'

    guess = self.request.get('guess')
    try:
       iguess = int(guess)
    except:
       return 'Please enter a valid guess' 

    self.session['guesses']=self.session.get('guesses',0)+1

    if iguess == 42:
       return 'Congratulations!'
    elif iguess < 42:
       return 'Your guess %s is too low' % iguess
    else:
       return 'Your guess %s is too high' % iguess

  def render(self, info):
    rendervars = dict()

    if isinstance(info, str) : 
      rendervars['msg'] = info

    rendervars['guesses'] = self.session.get('guesses', 0)

    return self.doRender('index.htm', rendervars)

