import logging
from google.appengine.api import memcache

from basecontext import BaseContext
from lticontext import LTI_Context
from googlecontext import Google_Context
from facebookcontext import Facebook_Context
from bbcontext import Blackboard_Context

# We completely ignore session all the time to force the
# use GET parameters all the time so folks can be different
# places in different windows safely (sort of like like WOA)

# TODO: Session needs to live in launch context!
# TODO: Deal with performance impact of many re-launches without a session
# TODO: Do this from memcache!

def Get_Context(web, options = {}):

    # Check to see if we are in the middle of a launch
    key = web.request.get('lti_launch_key')
    if ( len(key) > 0 ) : 
        memkey = 'lti_launch_key:' + key;
        launch = memcache.get(memkey)
        if launch and launch.get('_launch_type') == 'basiclti' : 
            context = LTI_Context(web, launch, options)
            context.launchkey = key
            logging.info("LTI Context restored="+key);
            return context
        elif launch and launch.get('_launch_type') == 'google' : 
            context = Google_Context(web, launch, options)
            context.launchkey = key
            logging.info("Google Context restored="+key);
            return context
    
    # LTI Looks for a particular signature so it is pretty safe
    context = Blackboard_Context(web, False, options)
    if ( context.complete or context.launch != None ) : 
        logging.info("Blackboard  Context complete="+str(context.complete));
        return context

    # LTI Looks for a particular signature so it is pretty safe
    context = LTI_Context(web, False, options)
    if ( context.complete or context.launch != None ) : 
        logging.info("LTI Context complete="+str(context.complete));
        return context

    # Facebook Looks for a particular signature so it is pretty safe
    # And we only do it if we have a canvas URL set
    canvas_url = memcache.get("facebook_canvas_url")
    logging.info("Canvas_url = %s" % (canvas_url) )
    if canvas_url != None :
        context = Facebook_Context(web, False, options)
        if ( context.complete or context.launch != None ) : 
            logging.info("Facebook Context complete="+str(context.complete));
            web.redirectafterpost = False
            web.renderfragment = True
            # web.proxyurl = "http://apps.facebook.com/wisdom-of-crowds/"
            web.proxyurl = canvas_url
            logging.info("web.proxyurl = %s" % (web.proxyurl) )
            return context

    # Intercept requests with lti_launch_key
    context = BaseContext(web, False)
    if ( context.complete ) : 
        return context

    if ( context.launch != None ) : 
        logging.info("Base context, type="+str(context.getContextType())+" launch.course_id="+context.getCourseKey()+" wci="+str(web.context_id))
        if web.context_id == False : 
            # logging.info("NO path context id")
            return context
        if context.launch.course and context.launch.course.course_id == web.context_id :
            # logging.info("Context ID's match")
            return context
        logging.info("Mismatch between launch course and path course...")

    # If we are logged in through Google
    context = Google_Context(web, False, options)
    if ( context.complete or context.launch != None ) : 
        return context

    # Dangerous
    context = BaseContext(web, False)
    return context
