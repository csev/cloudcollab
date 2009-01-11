Sun Jan 11 09:54:46 EST 2009

Welcome to the 0.001 version of the SimpleLTI Tool Producer
Framework written in PHP.

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

(1) Make a database in MySql called "lti" - look in 
    lti/DATAMODEL.sql for details

(2) Create all the tables in the lti/DATAMODEL.sql file

(3) Copy lti/db-template.php to db.php and put in the right data

(4) Go to the directory on your server.  I use:

    http://localhost/~csev/php-framework/

    It will say "not properly launched" because
    index.php  really expects to be getting POST data 
    from a launch request from an LMS.
    
(6) There is a fake LMS in the file lms.htm
    Open it up and press submit.  It posts back to 
    index.php - voila you are in the tool.  
    It dumps out all of the LTI provisioning data.


-- Charles Severance

