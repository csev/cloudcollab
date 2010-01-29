import logging
import urllib
import os
import pickle
import inspect
import random
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
    self.context_id = False
    self.div = False
    self.renderfragment = False
    self.portal = False
    self.action = False
    self.controller = False
    self.resource = False
    self.session = None
    self.proxyurl = None
    
    # Set this to False to supppress rediret after post
    self.redirectafterpost = True

    self.dStr = ''

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
      self.session = Session(self)
    else:
      self.session = None

    # Set all of the path based variables
    self.parsePath()
    return True

  def get(self):
    output = self.handleget()
    self.writeoutput(output)

  def post(self):
    output = self.handlepost()
    self.writeoutput(output)

  def writeoutput(self,output):
    if output is None : return
    if self.div is False and self.renderfragment is False:
       rendervars = dict()
       rendervars['fragment'] = output
       if self.portlet_title != None:
          rendervars['title'] = self.portlet_title
       newoutput = self.doRender('index.htm', rendervars)
       output = newoutput
    self.response.out.write(output)

  def handleget(self):
    if not self.setup(): return
    portlet_info = "_portlet_info"  
    if isinstance(self.context_id, str) : portlet_info = portlet_info+self.context_id
    logging.info("handleget action=%s" % self.action)
    if self.action == "post-redirect":
      info = self.session.get(portlet_info, None)
    else:  
      info = self.doaction()
      info = pickle.dumps( info ) 
      info = pickle.loads( info )

    self.session.delete_item(portlet_info)
    output = self.getview(info)
    return output

  # TODO: Eventually check content type...  Probably if this 
  # is not HTML, we just return the output - hmmm.
  # Or do we let the self.doaction tell us not to redirect
  # somehow - not a bad idea

  def handlepost(self):
    if not self.setup(): return
    portlet_info = "_portlet_info"  
    if isinstance(self.context_id, str) : portlet_info = portlet_info+self.context_id
    info = self.doaction()
    if (not isinstance(self.div, str) ) and self.redirectafterpost is True:
      self.session[portlet_info]  = info 
      redirecturl = self.getGetPath(action="post-redirect")
      logging.info("Redirect after POST %s" % redirecturl)
      self.redirect(redirecturl)
      return None
    else:
      info = pickle.dumps( info ) 
      info = pickle.loads( info )
      # Would be nice to remove the POST data from the 
      # Request at this point
      output = self.getview(info)

    self.session.delete_item(portlet_info)
    return output

  def doaction(self):
    logging.info("Your portlet is missing a doaction() method")

  def getview(self, info):
    logging.info("Your portlet is missing a getview() method")
    return "This portlet is missing a getview() method."

  # For now return the parameters all the time - even for the post
  def getPostPath(self, action=False, resource=False, direct=False, controller=False, ignoreajax=False, context_id=False):
    return self.getGetPath(action=action, params={}, resource=resource, direct=direct, controller=controller, ignoreajax=ignoreajax, context_id=context_id)

  def ajax_url(self, params={}, action=False, resource=False, controller=False, context_id=False):
    return self.getGetPath(action=action, params=params, resource=resource, direct=True, controller=controller, ignoreajax=True, context_id=context_id)

  # TODO: Do we want to allow a different action, etc?  Hmmm.
  # Typical use is just to change the resource
  def resource_url(self, params={}, action=False, resource=False, controller=False, context_id=False):
    return self.getGetPath(action=action, params=params, resource=resource, direct=True, controller=controller, ignoreajax=True, context_id=context_id)

  def getGetPath(self, action=False, resource=False, params = {}, direct=False, controller=False, ignoreajax=False, context_id=False):
    newpath = self.getPath(action, resource, direct, controller, ignoreajax, context_id)
    p = self.getUrlParms()
    p.update(params)
    if len(p) > 0 : 
       newpath = newpath + '?' + urllib.urlencode(p)
    return newpath

  # Reconstruct the path, changing the action, controller
  # direct means do not use the portal (i.e. make a servlet like URL)
  # ignoreajax means - even if we are in a div, generate the non-div URL
  def getPath(self, action=False, resource=False, direct=False, controller=False, ignoreajax=False, context_id=False):
    '''Retrieve the raw path to a controller/action pair.   Does not handle 
    when parameters are needed when cookies are not set.  Do not use
    directly from tool code.'''

    # TODO: Get mad if action, controller, or resource have nasty characters - maybe use preg
    addajax = self.div != False and ignoreajax != True
    addportal = self.portal != False and direct != True and addajax == False

    # If we have a proxyurl, it is to the controller level
    if self.proxyurl != None:
        newpath = self.proxyurl
    else:
        newpath = "/"
        # We cannot both be the whole portal screen and told to be in a div - pick div
        if addportal:
            newpath = "/portal/"
  
        if controller != False:
            newpath = newpath + controller + "/"
        elif self.controller != False :
            newpath = newpath + self.controller + "/"

    if isinstance(context_id, str) :
        newpath = newpath + context_id + "/"
    elif isinstance(self.context_id, str) :
        newpath = newpath + self.context_id + "/"

    if addajax:
        newpath = newpath + self.portlet_ajax_prefix + self.div + "/"

    if action != False :
        newpath = newpath + action + "/"
    # Keep the old action if we have a resource
    elif resource != False and self.action != False : 
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
# /controller/1234567/action/resource
# /portal/controller/1234567/action/resource

  def parsePath(self):
    '''Returns a tuple which is the controller, action and the rest of the path.
    The "rest of the path" does not start with a slash.'''
    str = self.request.path
    # logging.info("Parsing request path: "+self.request.path)
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

    if len(words) > 0 and len(words[0]) > 1 and words[0][1] >= "0" and words[0][1] <= "9" :
       self.context_id = words[0]
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
    
  def url_for(self, params={}, attributes={}, action=False, resource=False, controller=False):
    return self.getGetPath(action=action, params=params, resource=resource, controller=controller, ignoreajax=True)

  def link_to(self, text, params={}, attributes={}, action=False, resource=False, controller=False):
    fullurl = self.getGetPath(action=action, params=params, resource=resource, controller=controller, ignoreajax=True)
    if self.div == False or self.javascript_allowed == False:
      ret = '<a href="%s" %s>%s</a>' % (fullurl, self.getAttributeString(attributes), text)
    else :
      url = self.getGetPath(action=action, resource=resource, params=params, controller=controller)
      ret = '<a href="%s" onclick="$(\'#%s\').load(\'%s\');return false;" %s>%s</a>' % (fullurl, self.div, url, self.getAttributeString(attributes), text)
    return ret

  def form_tag(self, params={}, attributes={}, action=False, resource=False, controller=False):
    fullurl = self.getGetPath(action=action, params=params, resource=resource, controller=controller, ignoreajax=True)
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

  # Get clever button tolerant of JavasSript being turned off!
  def form_button(self, text, attributes = {},  params = {}, action=False, resource=False, controller=False):
    fullurl = self.getGetPath(action=action, resource=resource, params=params, controller=controller, ignoreajax=True)
    url = self.getGetPath(action=action, resource=resource, params=params, controller=controller)
    buttonid = "butt_" + str(int(random.random() * 1000000))
    hrefid = "href_" + str(int(random.random() * 1000000))

    ret = '<a href="%s" %s id="%s">%s</a>' % (fullurl, self.getAttributeString(attributes), hrefid, text)
    if self.javascript_allowed == False:
	pass
    elif self.div == False:
      ret = ret + '<button onclick="window.location=\'%s\'; return false;" %s id="%s" style="display:none;">%s</button>' % (url, self.getAttributeString(attributes), buttonid, text)
    else :
      ret = ret + """<button onclick="try{$('#%s').load('%s');return false;} catch(err){ window.location='%s'; return false; }" %s id="%s" style="display:none;">%s</button>""" % (self.div, url, fullurl, self.getAttributeString(attributes), buttonid, text)
    
    if self.javascript_allowed != False:
      ret = ret + """
<script type="text/javascript"> 
document.getElementById('%s').style.display="none";
document.getElementById('%s').style.display="inline";
</script>
""" % (hrefid, buttonid)
    return ret

  def form_submit(self, text="Submit", attributes={} ) :
    return '<input type="submit" value="%s" %s>' % ( text, self.getAttributeString(attributes))

  def doRender(self, tname = 'index.htm', values = { }):
    if tname.find('_') == 0: return None
    # Read the stack to find the file for our caller
    try:
      callerfile = inspect.stack()[1][1]
    except:
      callerfile = __file__
   
    temp = os.path.join(os.path.dirname(callerfile),
           'templates/' + tname)
    if not os.path.isfile(temp):
      raise NameError("Warning could not find template %s" % temp)

    # Check to see if we are supposed to be rendering 
    # A non-html file
    binary = False
    if temp.endswith(".jpg") or temp.endswith(".jpeg") :
        self.response.headers['Content-Type'] = 'image/jpeg'
        binary = True
    elif temp.endswith(".gif") :
        self.response.headers['Content-Type'] = 'image/gif'
        binary = True
    elif temp.endswith(".png") :
        self.response.headers['Content-Type'] = 'image/png'
        binary = True

    if binary:
        outstr = open(temp, "rb").read()
        self.response.out.write(outstr)
        return True
  
    # Make a copy of the dictionary and add the path and session
    newval = dict(values)
    newval['path'] = self.request.path
  
    outstr = template.render(temp, newval)
    outstr = self.epy(outstr)
    return outstr

  # Processes EMbedded Python structures {! form_tag(action="view") !}
  def epy(self, text):
    epy_macros = { 
       "url_for" : "self.url_for",
       "form_tag" : "self.form_tag",
       "form_submit" : "self.form_submit" ,
       "form_button" : "self.form_button",
       "link_to" : "self.link_to",
       "resource_url" : "self.resource_url",
       "ajax_url" : "self.ajax_url" }
    state = 0
    output = ""
    epy = ""
    for ch in text:
      # print ch, state
      if ch == "{" and state == 0:
        state = 1
      elif state == 1 and ch == "!":
        state = 2
        epy = ""
        continue
      elif state == 1 and ch != "!":
        output = output + "{"
        state = 0
      elif state == 2 and ch == " " and epy == "":
        continue
      elif state == 2 and ch == "!":
        state = 3
      elif state == 3 and ch != "}":
        epy = epy + "!"
        state = 2
      elif state == 3 and ch == "}":
        epy = epy.strip()
        # logging.info("FOUND EPY"+ epy)
        if ( len(epy) > 2 ) :
          for (macro, text) in epy_macros.items():
             if epy == macro:
               epy = text+"()"
               break
             if epy.startswith(macro):
               epy = epy.replace(macro, text)
               break
          # logging.info("DERIVED EPY"+ epy)
          epy = str(eval(epy))
	  # logging.info("Evaluated EPY "+ epy)
        output = output + epy 
        epy = ""
        state = 0
        continue
      
      if state == 0 : output = output + ch
      if state == 2 : epy = epy + ch
    
    return output
