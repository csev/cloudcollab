Sun Jan 11 19:29:52 EST 2009

Welcome to the 0.001 version of the SimpleLTI Tool Producer
Framework written in Python for the Google AppEngine.

It is pretty early and insecure 
  - All passwords are secret
  - It accepts any organization
  - It does not invalidate nonces
  - It tolerates very old launch dates

All this is to make testing practical during development.
You need to improve this to consider use in production.
All of the above need to be policies that make sense
for your application.

In a later version code will be added to accept some option
settings to handle the above choices - for now this is demo
and development.

Steps to make this run.

Open the web application - navigate to "/" - the LTI runtime
should not start up.  It should give you a link to the fake LMS.

From the fake LMS, you can launch back to / with a web service 
call.

If you use "launchhtml" it does not immediately redirect 
instead it sends back a ton of debug output and shows the
URL you would have gone to.  By using launchhtml - you 
can stop the process in the middle and examing things .

If you use "launchresolve" you get back the real web 
service response.  If you use launchresolve - you 
will see XML when you view source:

<launchResponse>
   <status>success</status>
   <type>iframe</type>
   <launchUrl>?id=1&amp;password=60e74037d20a8ef583dc55538ef5e639</launchUrl>
   <launchdebug>
     ....  A LOT OF STUFF
   </launchdebug>
</launchResponse>

If you use "direct" - the launch code will instantly redirect to the 
url with id/password.  This is because some LMS's will actually generate
code in a browser that builds the form and auto submits the launch, 
expecting to be redirected with to the tool after launch is done.

So when the framework sees "direct", after a successful launch setup 
- it just does the redirect.  So if you select "direct" and press Submit,
the next thing yu see is the tool.

The file index.py is the prototype tool.

-- Charles Severance

