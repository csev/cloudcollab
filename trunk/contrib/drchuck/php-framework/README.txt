Sun Jan 11 09:54:46 EST 2009

Welcome to the 0.001 version of the SimpleLTI Tool Producer
Framework written in PHP.

It is pretty early and insecure 
  - All passwords are secret
  - It accepts any organizations

But it is fine for development.

Steps to make this run.

(1) Make a database in MySql alled "lti" 
    with an account and password

(2) Create all the tables in the lti/DATAMODEL.sql file

(3) Copy lti/db-template.php to db.php and put in the right data

(4) Go to the directory on your server.  I use:

    http://localhost/~csev/lti-dist/

    It will say "not properly launched" because
    it really expects to have you coming from 
    an LMS.  But it does tell you how to get to the
    Fake built in LMS :)
    
(6) Just submit the launch parameters - unless 
    you want to play with roles, etc.

(7) You should see "Successful startup" and
    a little debug print.  Don't press refresh on
    this screen because the password is one-time
    use as it passes from launch.php to index.php.

The pattern is this:

  go to index.php
     session does not exist  
     redirect to login.php
  in login.php
     complain a bit and then link to login.htm
  in login.htm
     make some data and post to launch.php
  in launch.php
     check the post data - if asked for "direct"
     make a launch session id/pw and redirect
     to index.php with id/pw
  in index.php
     in lti.php
        notice the id/pw parameters
        look up and check launch session
        set launch session cookie 
        create the $LTI variable using the ORM
        fall through into index.php
     check to see if $LTI exists, if so,
        print out some groovy stuff and 
        the debug log.

Files:

README.txt       This file
DATAMODEL.sql    The Data Model
UNITOUTPUT.txt   Sample Unit test output
db.php           Sets up the Mysql Connection
debug.php        My debugging/logging framework
launch.php       The url that receives Launch Requests
login.htm        The fake LMS that sends launch Requests
login.php        Where you get redirected to when lti.php
                 cannot establish a launch session
lti.php          The code to establish the launch context
                 Like Sakai's RequestFilter
nonce.php        Utility code for checking nonces
orm.php          My object relational mapper like 
                 ActiveRecord - look in tests/orm_unit.php
                 for documentation.
tests            Contains the unit test framework and the
                 unit tests.  Good documentation for 
                 the ORM.

index.php        The tool code itself - this is where 
                 the magic comes together - this is where
                 you write your tool code - the require of 
                 lti.php is all the framework you need.
                 In addition to the course(), you can get the
                 user(), org(), and launch().  You can either 
                 get all the data - or specifiy a key

                     $LTI->org('org_name')
 
                 on the method call.


-- Charles Severance

