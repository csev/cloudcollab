import logging
import httplib
from google.appengine.api import memcache
from google.appengine.ext import db
from core.tool import ToolRegistration
from core import learningportlet
from  datetime import datetime

# Return our Registration
def register():
     return ToolRegistration(BBRegisterHandler, "Blackboard Proxy Registration Tool", 
         """This application allows you to register a proxy Tool in Blackboard 9.""")

class BBRegisterHandler(learningportlet.LearningPortlet):

    def update(self):
        logging.info("doaction="+str(self.action))
        if not self.context.isAdmin() : return "Must be admin to use this tool"
        if self.action is False : return
        if self.action == "register" : return self.register_action()
        return "Action not found " + str(self.action)
    
    def render(self, info):
        logging.info("getview="+str(self.action))
        if not self.context.isAdmin() : return "Must be admin to use this tool"
        output = self.doRender('index.htm', {'info' : info})
        return output

    def register_action(self):
        postData = self.getSoap("session", "nosession")
        webservice = httplib.HTTP("bb9-sync.blackboard.com")
        webservice.putrequest("POST", "/webapps/ws/services/Context.WS")
        webservice.putheader("User-Agent", "Python post")
        webservice.putheader("Content-Type","application/soap+xml;charset=UTF-8;action=\"registerTool\"");
        webservice.putheader("SOAPAction", "\"\"")
        webservice.endheaders()
        webservice.send(postData)
        logging.info("Sent %s bytes" % (len(postData)))

        # get the response

        statuscode, statusmessage, header = webservice.getreply()
        logging.info("Status code %s" % ( statuscode ) )
        logging.info("Got %s headers" % ( len(header) ) )
        print "Response: ", statuscode, statusmessage
        print "headers: ", header
        res = webservice.getfile().read()
        print res
        logging.info("Rettieved %d bytes" % (len(res) ) )
        logging.info("Data"+res)
        return res

    def getSoap(self, key, secret):
        tstime = datetime.utcnow()
        nstime = tstime + 5
        logging.info("tstime = %s" % (tstime) ) 
        logging.info("nstime = %s" % (nstime) ) 
        created = tstime.strftime("%Y-%m-%dT%H:%M:%S.123Z")
        registerToolSOAP="""<soap:Envelope xmlns:con="http://context.ws.blackboard" xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
<soap:Header>
    <wsse:Security soap:mustUnderstand="true" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
       <wsu:Timestamp wsu:Id="Timestamp-16265191" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
           <wsu:Created>WSSE_TIMESTAMP</wsu:Created>
           <wsu:Expires>WSSE_TIMESTAMP</wsu:Expires>
       </wsu:Timestamp>
       <wsse:UsernameToken wsu:Id="UsernameToken-2704090" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
           <wsse:Username>WSSE_USERNAME</wsse:Username>
           <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">WSSE_PASSWORD</wsse:Password>
       </wsse:UsernameToken>
    </wsse:Security>
</soap:Header>
<soap:Body>
<con:registerTool>
<con:clientVendorId>CloudCollab</con:clientVendorId>
<con:clientProgramId>CloudCollab Proxy Server</con:clientProgramId>
<con:registrationPassword>SOAP_PASSWORD</con:registrationPassword>
<con:description><![CDATA[<?xml version="1.0" encoding="UTF-8"?>
<tool-profile ltiVersion="2.0-July08" xmlns:locale="http://www.ims.org/lti/localization">
<vendor>
<code>CloudCollab</code> <name>CloudCollab</name>
<description>CloudCollab</description>
<url>http://www.cloudcollab.org</url>
<contact><email>csev@umich.edu</email></contact>
</vendor>
<tool-info>
<code>WisCrowd Proxy Server</code>
<name>WisCrowd Proxy Server</name>
<version>1</version>
<description>Wisdom of Crowds</description>
</tool-info>
<tool-instance>
<base-urls>
<base-url type="http">http://wiscrowd.appspot.com/wiscrowd</base-url>
</base-urls>
<contact><email>csev@umich.edu</email></contact>
<security-profile>
<digest-algorithm>MD5</digest-algorithm>
</security-profile>
</tool-instance>
<required-webservices>
<tool-login>
<service name="Context.WS">
<operation>logout</operation>
</service>
</tool-login>
<ticket-login>
<service name="Context.WS">
<operation>logout</operation>
</service>
</ticket-login>
</required-webservices>
<http-actions>
<action type="view" path="http://wiscrowd.appspot.com/wiscrowd/1234/"/>
</http-actions>
<links>
<menu-link>
<category-choice>
<category>TBD - not defined by LTI yet</category>
<category platform="blackboard">system_tool</category>
</category-choice>
<name locale:key="system_tool.language.key">Google System Tool</name>
<http-actions>
<action type="menu-view" path="/12345/"/>
</http-actions>
<description locale:key="system_tool.link.description.key">Proxy System Tool Description</description>
<icons>
<icon >/images/icon1.gif</icon>
<icon platform="blackboard" style="listitem" >/favicon.ico</icon>
</icons>
</menu-link>
</links>
</tool-profile>]]></con:description>
<con:initialSharedSecret>SOAP_SHARED_SECRET</con:initialSharedSecret>
<con:requiredToolMethods/>
<con:requiredTicketMethods/>
</con:registerTool>
</soap:Body>
</soap:Envelope>
"""
        registerToolSOAP = registerToolSOAP.replace("WSSE_TIMESTAMP",created).replace("SOAP_SHARED_SECRET", secret).replace("SOAP_PASSWORD",secret)
        return registerToolSOAP
