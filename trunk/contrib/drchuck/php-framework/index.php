<?php
require_once("lti/launch.php");
require_once("lti/setup.php");

print "<pre>\n";
if ( $LTI ) {
  print "Successful startup of LTI runtime\n";
  print "\n";
  print "User Data\n";
  print_r($LTI->user());
  print "Course Data\n";
  print_r($LTI->course());
  print "Membership Data\n";
  print_r($LTI->memb());
  print "Organization Data\n";
  print_r($LTI->org());
  print "Launch Data\n";
  print_r($LTI->launch());
} else {
  print "LTI Runtime failed to start\n";
}
print "\nDEBUG LOG\n";
print getDebugLogPre();
print "\n";
print "</pre>\n";

?>



