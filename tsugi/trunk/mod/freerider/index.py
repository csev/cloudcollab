import logging
import pickle
from google.appengine.api import memcache

from core.tool import ToolRegistration
from core import learningportlet

# Return our Registration
def register():
   return ToolRegistration(FreeRiderHandler, 'Free Rider', """This 
application allows you to play the "Free Rider" game as described by
James Surowiecki in the book "The Wisdom of Crowds".""")

class GameState():
   def __init__(self, playercount=5):
     self.playercount = playercount
     self.players = list()
     self.chips = list()
     self.last = list()
     self.turn = -1
     self.current = 0
     self.pot = 0

class FreeRiderHandler(learningportlet.LearningPortlet):

  # Called for form posts
  def doaction(self):
    logging.info('doaction Action=%s'%self.action)
    if self.action == 'play' : return self.action_play()
    if self.action == 'join' : return self.action_join()
    if self.action == 'reset' : return  self.action_reset()
    if self.action == 'messages' : return None
    logging.info('Unknown doaction=%s' % self.action)
    return None

  def getview(self, info):
    logging.info('getview Action=%s'%self.action)

    if self.action == 'messages': 
       return self.view_messages()

    rendervars = {'context': self.context,
                  'notice' : info,
                  'request': self.request}

    gm = self.getmodel()
    if ( len(gm.players) < 4 ) :
      rendervars['joinbutton'] = self.form_button('Join', action='join')

    return self.doRender('index.htm', rendervars)

  def getmodel(self):
    freekey = 'FreeRider-'+str(self.context.course.key())
    logging.info('Loading Free key='+freekey)
    freerider =  memcache.get(freekey)
    # If we changed the program ignore old things in the cache
    if freerider == None or not isinstance(freerider, GameState):
      freerider = GameState()
      memcache.add(freekey, freerider, 3600)
    return freerider

  def putmodel(self, freerider):
    freekey = 'FreeRider-'+str(self.context.course.key())
    logging.info('Store Free key='+freekey)
    memcache.replace(freekey, freerider, 3600)

  def action_reset(self) :
    if not self.context.isInstructor() :
      return 'Only the instructor can reset!'
    gm = GameState()
    self.putmodel(gm)
    return 'Game reset'

  def action_join(self) :
    gm = self.getmodel()

    if not self.context.user.email or len(self.context.user.email) < 1:
      return 'You must have an E-Mail to play'
    
    if self.context.user.email in gm.players:
      return 'You have already joined the game'

    if len(gm.players) >= gm.playercount: 
      return 'The game is closed - you can play next time'

    gm.players.append(self.context.user.email)
    gm.chips.append(20)
    gm.last.append( list () )

    # Let the game begin!
    if len(gm.players) >= gm.playercount: 
       gm.turn = 1
       gm.current = 0
       
    self.putmodel(gm)

    return 'Welcome to the game'

  def action_play(self) :
    gm = self.getmodel()

    if gm.turn < 1 or gm.turn > 4: 
      return 'The game is not running!'
    if not context.user.email in gm.players:
      return 'You are not currently playing!'
    if not context.user.email == gm.players[gm.current] :
      return 'It is not your turn!'

    contrib = self.request.get('chips')
    try: contrib = int(contrib)
    except: contrib = -1
    
    if contrib > gm.chips[gm.current] : contrib = gm.chips[gm.current]

    if contrib < 0 :
      return 'Please enter a real number'

    gm.pot = gm.pot + contrib
    gm.chips[gm.current] = gm.chips[gm.current] - contrib
    gm.last[gm.current].append(contrib)
    gm.current = gm.current + 1
    if gm.current >= gm.playercount:
      gm.current = 0
      gm.turn = gm.turn + 1
      # Split the pot
      each = int((gm.pot * 1.6) / gm.playercount) 
      for i in range(len(gm.chips)):
        gm.chips[i] = gm.chips[i] + each
      gm.pot = 0

    self.putmodel(gm)

    return 'Thanks for your contribution!'

  def view_messages(self) :
    gm = self.getmodel()

    me = None
    for i in range(len(gm.players)):
      if gm.players[i] == self.context.user.email : 
         me = i

    r = '<pre>\n'

    if gm.turn > 0 and gm.turn < 5 and self.context.user.email == gm.players[gm.current]:
      r = r + '<font color="red">It is your turn</font>\n\n'

    if gm.turn < 1:
      r = r + 'Game has not started\n'
    elif gm.turn > 4:
      r = r + 'Game completed\n'
    else:
      r = r + 'GAME ON! Current turn: '+str(gm.turn)+'\n';

    r = r + '\n'
    if self.context.user.email in gm.players and not self.context.isInstructor() :
      r = r + 'Your pot: '+str(gm.chips[me])+' Contribution History:'+str(gm.last[me])+'\n'
      r = r + 'Players: '+str(len(gm.players))+'\n'
    else:
      r = r + 'Current pot total: ' + str(gm.pot) + '\n'
      for i in range(len(gm.players)):
         if gm.current == i :
           r = r + '===> '
         else:
           r = r + '     '
         r = r + '(' + str(gm.chips[i]) + ' / ' + str(gm.last[i]) + ') ' + gm.players[i] + '\n'

    r = r + '</pre>\n'
    return r
