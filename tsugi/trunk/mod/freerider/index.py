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
   def __init__(self, playercount=4):
     self.playercount = playercount
     self.turns = 4
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
    email = self.getpersonkey()
    if email in gm.players :
      rendervars['player'] = 'true'

    if email in gm.players or self.context.isInstructor() :
      rendervars['showstatus'] = 'true'

    if ( len(gm.players) < gm.playercount ) :
      rendervars['joinbutton'] = self.form_button('Join', action='join')

    if gm.turn < 1 :
      rendervars['status'] = 'The game has not started'
    elif gm.turn > gm.turns :
      rendervars['status'] = 'The game has finished'
    elif not email in gm.players:
      rendervars['status'] = 'You are not playing in the current game'
    elif email == gm.players[gm.current] :
      rendervars['status'] = 'It is your turn'
    else:
      rendervars['status'] = 'It is not your turn'


    return self.doRender('index.htm', rendervars)

  def getmodel(self):
    freekey = 'FreeRider-'+str(self.context.getCourseKey())
    logging.info('Loading Free key='+freekey)
    freerider =  memcache.get(freekey)
    # If we changed the program ignore old things in the cache
    if freerider == None or not isinstance(freerider, GameState):
      freerider = GameState()
      memcache.add(freekey, freerider, 3600)
    return freerider

  def putmodel(self, freerider):
    freekey = 'FreeRider-'+str(self.context.getCourseKey())
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

    email = self.getpersonkey()

    if email == None or len(email) < 1:
      return 'You must have an E-Mail to play'
    
    if email in gm.players:
      return 'You have already joined the game'

    if len(gm.players) >= gm.playercount: 
      return 'The game is closed - better luck next time'

    gm.players.append(email)
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

    email = self.getpersonkey()

    if gm.turn < 1 or gm.turn > gm.turns : 
      return 'The game is not running!'
    if not email in gm.players:
      return 'You are not currently playing!'
    if not email == gm.players[gm.current] :
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
    email = self.getpersonkey()

    me = None
    for i in range(len(gm.players)):
      if gm.players[i] == email : 
         me = i

    r = '<pre>\n'

    if gm.turn > 0 and gm.turn < 5 and email == gm.players[gm.current]:
      r = r + '<font color="red">It is your turn</font>\n\n'

    if gm.turn < 1:
      r = r + 'Game has not started\n'
    elif gm.turn > 4:
      r = r + 'Game completed\n'
    else:
      r = r + 'GAME ON! Current turn: '+str(gm.turn)+'\n';

    r = r + '\n'
    if email in gm.players and not self.context.isInstructor() :
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

  def getpersonkey(self) :
    email = self.context.getUserEmail()
    if ( email == None ) : email = getUserShortName()
    return email

