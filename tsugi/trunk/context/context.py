import logging
import cgi
import wsgiref.handlers
import logging
import hashlib
import base64
import uuid
import urllib
from datetime import datetime, timedelta
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import users

from contextmodel import *
from basecontext import BaseContext
from slticontext import SLTI_Context
from blticontext import BLTI_Context
from googlecontext import Google_Context
from core.modelutil import *

# TODO: Consider completely ignoring session *all the time*
def Get_Context(web, session = False, options = {}):
    context = BLTI_Context(web, session, options)
    if ( context.complete or context.launch != None ) : 
        return context

    context = SLTI_Context(web, session, options)
    if ( context.complete or context.launch != None ) : 
        return context

    context = Google_Context(web, session, options)
    if ( context.complete or context.launch != None ) : 
        return context

    return BaseContext(web, session)
