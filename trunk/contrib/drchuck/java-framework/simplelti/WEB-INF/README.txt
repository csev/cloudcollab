Thu Mar 19 08:30:38 EDT 2009

Developer Guide

The source code is in the classes folder.   To compile, 

cd classes
javac -cp .:../../../../common/lib/servlet-api.jar SimpleLTIServlet.java

There is no persistence in this code - it simply uses hash maps to 
pass information from the launch into the "session".  In a real 
producer, you would end up with tables for courses, users, organizations,
memberships, and launches - or find  way to place the necessary information
in existing tables.

I include a data model used in PHP in the file DATAMODEL.sql - but 
it is not used in this servlet.

For details on the protocol and all the fields which come acoss the 
web service call, - see simplelti.appspot.com

/Chuck
www.dr-chuck.com
