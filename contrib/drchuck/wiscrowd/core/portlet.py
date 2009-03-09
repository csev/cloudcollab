import logging
import urllib
import os
import pickle
import inspect
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext import db
from util.sessions import Session

# TODO: Add some debugging
# Add try / except on get/post and put out a decent message
# Come up with a way to do sessions without cookies

# TODO: Preferences like JSR-168 ??? 
  
class Portlet(webapp.RequestHandler):

  def __init__(self) :
    self.div = False
    self.portal = False
    self.action = False
    self.controller = False
    self.resource = False
    self.session = None
    
    # Set this to False to supppress reiret after post
    self.redirectafterpost = True

    self.dStr = ""

    self.portlet_title = None
    self.portlet_header = None
    self.portlet_ajax_prefix = 'portlet_ajax_'

    # This is not a guarantee that the browser supports JavaScript
    # If this is False, we will generate no JavaScript
    self.javascript_allowed = True
    # Hack for testing
    # self.javascript_allowed = False

  # Deal with Javascript turned off - warning
  def setDiv(self, newdiv) :
    """Allows the div to be injected from above"""
    self.div = newdiv
    if self.javascript_allowed is False:
      logging.info("Warning - Javascript is off and setting div=%s" % newdiv)

  def requireSession(self):
    return True

  def requireLogin(self):
    return True

  def setTitle(self,newtitle):
    self.portlet_title = newtitle

  def setHeader(self,newheader):
    self.portlet_header = newheader

  def setup(self):
    if self.requireSession() :
      self.session = Session(self.request)
    else:
      self.session = None

    # Set all of the path based variables
    self.parsePath()
    return True

  def get(self):
    output = self.handleget()
    if ( output != None ) : self.response.out.write(output)

  def post(self):
    output = self.handlepost()
    if ( output != None ) : self.response.out.write(output)

  def handleget(self):
    if not self.setup(): return
    info = self.session.get("_portlet_info", None)
    output = self.getview(info)
    self.session.delete("_portlet_info")
    return output

  def handlepost(self):
    if not self.setup(): return
    ( info ) = self.doaction()

    # TODO: Eventually check content type...  Probably if this 
    # is not HTML, we just return the output - hmmm.
    # Or do we let the self.doaction tell us not to redirect
    # somehow - not a bad idea

    # Do redirect unless this is an Ajax Post or we have 
    # redirect after POST turned off
    if self.div is False and self.redirectafterpost is True:
      self.session["_portlet_info"]  = info 
      logging.info("Redirect after POST %s" % self.request.uri)
      self.redirect(self.request.uri)
      return None
    else:
      info = pickle.dumps( info ) 
      info = pickle.loads( info )
      output = self.getview(info)

    self.session.delete("_portlet_info")
    return output

  def doaction(self):
    logging.info("Your portlet is missing a doaction() method")

  def getview(self, info):
    logging.info("Your portlet is missing a getview() method")
    return "This portlet is missing a getview() method."

  # For now return the parameters all the time - even for the post
  def getPostPath(self, action=False, resource=False, direct=False, controller=False, ignoreajax=False):
    return self.getGetPath(action, resource, { }, direct, controller, ignoreajax)

  def getGetPath(self, action=False, resource=False, params = {}, direct=False, controller=False, ignoreajax=False):
    newpath = self.getPath(action, resource, direct, controller, ignoreajax)
    p = self.getUrlParms()
    p.update(params)
    if len(p) > 0 : 
       newpath = newpath + '?' + urllib.urlencode(p)
    return newpath

  # Reconstruct the path, changing the action, controller
  # direct means do not use the portal (i.e. make a servlet like URL)
  # ignoreajax means - even if we are in a div, generate the non-div URL
  def getPath(self, action=False, resource=False, direct=False, controller=False, ignoreajax=False):
    '''Retrieve the raw path to a controller/action pair.   Does not handle 
    when parameters are needed when cookies are not set.  Do not use
    directly from tool code.'''

    # TODO: Get mad if action, controller, or resource have nasty characters - maybe use preg
    addajax = self.div != False and ignoreajax != True
    addportal = self.portal != False and direct != True and addajax == False

    newpath = "/"
    # We cannot both be the whole portal screen and told to be in a div - pick div
    if addportal:
      newpath = "/portal/"

    if controller != False:
      newpath = newpath + controller + "/"
    elif self.controller != False :
      newpath = newpath + self.controller + "/"

    if addajax:
      newpath = newpath + self.portlet_ajax_prefix + self.div + "/"

    if action != False :
      newpath = newpath + action + "/"
    elif self.action != False : 
      newpath = newpath + self.action + "/"
    # We need some action if they gave us a resource
    elif resource != False : 
      newpath = newpath + "action/"
 
    if resource != False :
      newpath = newpath + resource + "/"

    # logging.info("self.div=%s ignoreajax=%s addajax=%s addportal=%s newpath=%s" % ( self.div, ignoreajax, addajax, addportal, newpath) )
    return newpath

# This is some hard coded URL parsing
# Some example URLs
# /controller/action/resource
# /controller/portlet_ajax_divname/action/resource
# /portal/controller/action/resource

  def parsePath(self):
    '''Returns a tuple which is the controller, action and the rest of the path.
    The "rest of the path" does not start with a slash.'''
    str = self.request.path
    # self.debug("Parsing request path: "+self.request.path)
    xwords = str.split("/")
    words = list()
    for word in xwords:
       if len(word.strip()) > 0 :  words.append(word)

    if len(words) > 0 and words[0] == 'portal' :
       del words[0]
       self.portal = True

    if len(words) > 0 :
       self.controller = words[0]
       del words[0]

    if len(words) > 0 and words[0].startswith(self.portlet_ajax_prefix) : 
       div = words[0][len(self.portlet_ajax_prefix):].strip()
       del words[0]
       if len(div) > 0 : 
         self.div = div

    if len(words) > 0 :
       self.action = words[0]
       del words[0]
    if len(words) > 0 :
       self.resource = "/".join(words)
    # self.debug("Portal=%s div=%s controller=%s action=%s resource=%s" % (self.portal, self.div, self.controller, self.action, self.resource))

  def debug(self, str):
    logging.info(str)
    self.dStr = self.dStr + str + "\n"

  def getDebug(self):
    return self.dStr

  def requestdebug(self, web):
    # Drop in the request for debugging
    reqstr = web.request.path + "\n"
    for key in web.request.params.keys():
      value = web.request.get(key)
      if len(value) < 100: 
         reqstr = reqstr + key+':'+value+'\n'
      else: 
         reqstr = reqstr + key+':'+str(len(value))+' (bytes long)\n'
    return reqstr

  def getUrlParms(self) :
    retval = { }
    if self.session != None and self.session.foundcookie is False:
        retval =  { self.session.cookiename: self.session.sid }
    return retval

  def getFormFields(self) :
    retval = ''
    if ( self.session != None ) and self.session.foundcookie is False:
       retval = '<input type="hidden" name="%s" value="%s">\n' % (self.session.cookiename, self.session.sid)
    return retval

  def getAttributeString(self, attributes = {} ) :
    ret = ''
    for (key, value) in attributes.items() :
      if len(ret) > 0 : ret = ret + ' '
      ret = ret + key + '="' + value + '"'
    return ret
    
  def getAnchorTag(self, text, attributes = {},  params = {}, action=False, resource=False, controller=False):
    fullurl = self.getGetPath(action=action, resource=resource, params=params, controller=controller, ignoreajax=True)
    if self.div == False or self.javascript_allowed == False:
      ret = '<a href="%s" %s>%s</a>' % (fullurl, self.getAttributeString(attributes), text)
    else :
      url = self.getGetPath(action=action, resource=resource, params=params, controller=controller)
      ret = '<a href="%s" onclick="$(\'#%s\').load(\'%s\');return false;" %s>%s</a>' % (fullurl, self.div, url, self.getAttributeString(attributes), text)
    return ret

  def getFormTag(self, attributes = {},  params = {}, action=False, resource=False, controller=False):
    fullurl = self.getGetPath(action=action, resource=resource, params=params, controller=controller, ignoreajax=True)
    ret = '<form action="%s" method="post" %s id="myform">' % (fullurl, self.getAttributeString(attributes))
    if self.div != False and self.javascript_allowed != False:
      url = self.getGetPath(action=action, resource=resource, params=params, controller=controller)
      ret = ret + """
<script type="text/javascript"> 
    $(document).ready(function() {
        $('#myform').ajaxForm({
            target: '#fred',
            url: '%s'
        });
    });
</script> 
""" % ( url ) 

    fields = self.getFormFields()
    if len(fields) > 0 :
        ret = ret + '\n' + self.getFormFields()
    return ret

  # TODO: What about if Javascript is turned off?  Maybe generate both href and button and when JS is on flip which is hidden
  def getFormButton(self, text, attributes = {},  params = {}, action=False, resource=False, controller=False):
    fullurl = self.getGetPath(action=action, resource=resource, params=params, controller=controller, ignoreajax=True)
    url = self.getGetPath(action=action, resource=resource, params=params, controller=controller)
    ret = '<a href="%s" %s id="buttonhref">%s</a>' % (fullurl, self.getAttributeString(attributes), text)
    if self.javascript_allowed == False:
	pass
    elif self.div == False:
      ret = ret + '<button onclick="window.location=\'%s\'; return false;" %s id="buttonbutton" style="display:none;">%s</button>' % (url, self.getAttributeString(attributes), text)
    else :
      ret = ret + """<button onclick="try{$('#%s').load('%s');return false;} catch(err){ window.location='%s'; return false; }" %s id="buttonbutton" style="display:none;">%s</button>""" % (self.div, url, fullurl, self.getAttributeString(attributes), text)
    
    if self.javascript_allowed != False:
      ret = ret + """
<script type="text/javascript"> 
document.getElementById('buttonhref').style.display="none";
document.getElementById('buttonbutton').style.display="inline";
</script>
"""
    return ret

  def getFormSubmit(self, text, attributes ={ } ) :
    return '<input type="submit" value="%s" %s>' % ( text, self.getAttributeString(attributes))

  def doRender(self, tname = "index.htm", values = { }):
    if tname.find("_") == 0: return None
    # Read the stack to find the file for our caller
    try:
      callerfile = inspect.stack()[1][1]
    except:
      callerfile = __file__
   
    temp = os.path.join(os.path.dirname(callerfile),
           'templates/' + tname)
    if not os.path.isfile(temp):
      return None
  
    # Make a copy of the dictionary and add the path and session
    newval = dict(values)
    newval['path'] = self.request.path
  
    outstr = template.render(temp, newval)
    return outstr

