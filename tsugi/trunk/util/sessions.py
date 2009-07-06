import os
import time
import datetime
import random
import Cookie
import logging
from google.appengine.api import memcache

COOKIE_NAME = '_wiscrowd_session_id'
DEFAULT_COOKIE_PATH = '/'
SESSION_EXPIRE_TIME = 7200 # sessions are valid for 7200 seconds (2 hours)

class Session(object):

    def __init__(self, request=None):
        self.sid = None
        self.key = None
        self.session = None
        self.request = request
        self.foundcookie = False
        self.cookiename = COOKIE_NAME
        string_cookie = os.environ.get('HTTP_COOKIE', '')
        self.cookie = Cookie.SimpleCookie()
        self.cookie.load(string_cookie)

        # check for existing cookie or request parameter
        if self.cookie.get(COOKIE_NAME):
            self.sid = self.cookie[COOKIE_NAME].value
            self.foundcookie = True
        elif self.request != None :
            self.sid = self.request.get(COOKIE_NAME)
       
        if self.sid != None and len(self.sid) < 1 : self.sid = None

        if self.sid != None:
            self.key = "session-" + self.sid
	    self.session = memcache.get(self.key)
            if self.session is None:
               logging.info("Invalidating session "+self.sid)
               self.sid = None
               self.key = None
               self.foundcookie = False

        if self.session is None:
            self.sid = str(random.random())[5:]+str(random.random())[5:]
            self.key = "session-" + self.sid
            logging.info("Creating session "+self.key);
            self.session = dict()
	    memcache.add(self.key, self.session, 3600)

            self.cookie[COOKIE_NAME] = self.sid
            self.cookie[COOKIE_NAME]['path'] = DEFAULT_COOKIE_PATH
            self.cookie[COOKIE_NAME]['expires'] = SESSION_EXPIRE_TIME
            # Send the Cookie header to the browser
            print self.cookie

    # Convienent support get() method
    def get(self, keyname, default=None):
        if keyname in self.session:
            return self.session[keyname]
        return default

    # Delete with no error
    def delete_item(self, keyname):
        if keyname in self.session:
            del self.session[keyname]
            self._update_cache()

    # Methods to work like a dictionary
    def __setitem__(self, keyname, value):
        self.session[keyname] = value
        self._update_cache()

    def __getitem__(self, keyname):
        if keyname in self.session:
            return self.session[keyname]
        raise KeyError(str(keyname))

    def __delitem__(self, keyname):
        if keyname in self.session:
	    del self.session[keyname]
            logging.info(self.session)
            self._update_cache()
            return
        raise KeyError(str(keyname))

    def __contains__(self, keyname):
        try:
            r = self.__getitem__(keyname)
        except KeyError:
            return False
        return True

    def __len__(self):
        return len(self.session)

    def _update_cache(self):
        memcache.replace(self.key, self.session, 3600)

