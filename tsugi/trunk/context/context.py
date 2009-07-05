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

# We completely ignore session all the time to force the
# use GET parameters all the time so folks can be different
# places in different windows safely (sort of like like WOA)

# TODO: Session needs to live in launch context!
# TODO: Deal with performance impact of many re-launches without a session

def Get_Context(web, session = False, options = {}):
    # BLTI Looks for a particular signature so it is pretty safe
    context = BLTI_Context(web, False, options)
    if ( context.complete or context.launch != None ) : 
        logging.info("BasicLTI Context complete="+str(context.complete));
        return context

    # SLTI Looks for a particular signature so it is pretty safe
    context = SLTI_Context(web, False, options)
    if ( context.complete or context.launch != None ) : 
        logging.info("SimpleLTI Context complete="+str(context.complete));
        return context

    # Intercept requests with lti_launch_key
    context = BaseContext(web, False)
    if ( context.complete ) : 
        return context

    if ( context.launch != None ) : 
        logging.info("Base context, type="+str(context.launch.launch_type)+" launch.course_id="+context.launch.course.course_id+" wci="+web.context_id)
        if web.context_id == False : 
            logging.info("NO path context id")
            return context
        if context.launch.course and context.launch.course.course_id == web.context_id :
            logging.info("Context id's match!")
            return context
        logging.info("Mismatch between launch course and path course...")

    # If we are logged in through Google
    context = Google_Context(web, False, options)
    if ( context.complete or context.launch != None ) : 
        return context

    # Dangerous
    context = BaseContext(web, session)
    return context
