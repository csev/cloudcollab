<?php
require_once("debug.php");
require_once("nonce.php");
require_once("object.php");
/*
  HTTP/1.1 400 Bad Request
  Content-Type: application/xml
  				
  <launchResponse>
      <status>fail</status>
      <code>BadPasswordDigest</code>
      <description>The password digest was invalid</description>
  </launchResponse>
*/

// The LTI Object should not exist yet
$LTI = false;

function lti_launchfail($msg) {
    // Do status 400
    if ( $_REQUEST[action] == 'launchresolve' ) {
      print "<launchResponse>\n";
      print "<status>fail</status>\n";
      print "<code>BadPasswordDigest</code>\n";
      print "<description>$msg</description>\n";
      print "</launchResponse>\n";
    } else {
      print "Error in the launch POST data:\n";
      print $msg;
    }
}

// Only do the launch processing if we have an action parameter
if ( $_REQUEST[action] == 'launchresolve' || $_REQUEST[action] == 'direct'
     || $_REQUEST[action] == 'launchhtml' ) {

  DPRT("Handling incoming Launch POST");

  if ( $_REQUEST[sec_nonce] && $_REQUEST[sec_created] &&
       $_REQUEST[sec_digest] &&
       $_REQUEST[user_id] && $_REQUEST[course_id] &&
       // $_REQUEST[launch_resource_id] && $_REQUEST[user_role] ) {
       $_REQUEST[user_role] ) {
    // Good to continue
  } else {
     lti_launchfail("Missing required launch parameter (sec_nonce, sec_created, sec_digest, user_id, course_id, launch_request_id, and user_role) see simplelti.appspot.com");
     exit();
  }

  // Make the time difference large to be tolerant - but force it
  // to run through the time check code
  if ( checkNonce($_REQUEST[sec_nonce], $_REQUEST[sec_created], 
                  $_REQUEST[sec_digest], "secret", 10000000) ) {
     DPRT("Nonce validated");
  } else {
     lti_launchfail("Nonce computation failed see simplelti.appspot.com");
     exit();
  }

  require_once("db.php");

  // Check to see if this is new or a replay
  $digest = mysql_real_escape_string($_REQUEST[sec_digest]);
  $quer = "SELECT id FROM lti_digest WHERE digest='$digest'";
  DPRT($quer);
  $result = mysql_query($quer);
  $num_rows = mysql_num_rows($result);
  DPRT($num_rows);
  if ( $num_rows > 0 ) {
     DPRT("Reused existing launch - only do this when debugging");
  } else {
     DPRT("New Launch $digest");
  }

  // Clean up out nonce/digest table - for now every time
  mysql_query("delete from lti_digest where created_at < date_sub(now(), interval 1 hour)");

  // Log this digest
  $reqstr = mysql_real_escape_string(print_r($_REQUEST,TRUE));
  $quer = "insert into lti_digest (created_at, digest, request) values (NOW(), '$digest', '$reqstr');";
  mysql_query($quer);

  require_once("orm.php");

  $orgid = $_REQUEST[org_id];
  if ( $orgid ) {
    $org = new ORM("org", "org_id", "lti_org");
    $org->read($orgid);

    // Welcome new orgs - insecure :)
    // TODO: Really handle organization
    if ( ! $org->id() ) {
      $org->setall($_REQUEST, '/^org_/');
      $org->setall( array( "secret" => "secret") );
      $org->insert($orgid);
    }

    if ( $org->id() ) {
       $orgdata = $org->data();
       $orgsecret = $orgdata[secret];
       DPRT("org secret from database $orgsecret");
       if ( checkNonce($_REQUEST[sec_nonce], $_REQUEST[sec_created], 
                       $_REQUEST[sec_org_digest], $orgsecret, 10000000) ) {
         DPRT("Organization secret matches");
      } else {
         DPRT("Organiztion secret failed");
         $org->clear();  // Get rid of the data because we cannot trust it
      }
    }
  }

  $userid = $_REQUEST[user_id];
  $courseid = $_REQUEST[course_id];

  // Add the user if necessary
  $usr = new ORM("user", "user_id", "lti_user");
  $usr->read($userid);
  $usr->setall($_REQUEST, '/^user_/');
  if ( $usr->id() ) {
     $usr->update();
  } else {
     $usr->insert($userid);
  }

  // Add the course if necessary
  $crs = new ORM("course", "course_id", "lti_course");
  $crs->read($courseid);
  $crs->setall($_REQUEST, '/^course_/');
  if ( $crs->id() ) {
     $crs->update();
  } else {
     $crs->insert($courseid);
  }

  DPRT("User's ID = ".$usr->id());
  DPRT("Course ID = ".$crs->id());
  if ( $org ) {
    DPRT("Org    ID = ".$org->id());
  }

  $userrole = $_REQUEST[user_role];
  DPRT("Role = $userrole");
  error_log("Role = $userrole",0);
  $memb = new ORM("membership", false,"lti_membership");
  if ( ! $memb ) return false;

  $memb->read( array( "course_id" => $crs->id(), "user_id" => $usr->id()) ) ;
  $roleid = 1;
  if ( strtolower($userrole) == "instructor" ) $roleid = 2;
  if ( strtolower($userrole) == "administrator" ) $roleid = 2;
  $memb->setall( array( "course_id" => $crs->id(), "user_id" => $usr->id(),
                        "role_id" => $roleid ) ) ;
  if ( $memb->id() ) {
     $memb->update();
     DPRT("Updated membership=$memb->id() ");
  } else { 
     $memb->insert();
     DPRT("Added membership=$memb->id()");
  }

  // Create/reuse the launch record
  $launch = new ORM("launch", false,"lti_launch");
  if ( ! $launch ) return false;

  $launchkeys = array("course_id" => $crs->id(), "user_id" => $usr->id());
  if ( $org && $org->id() ) {
    $launchkeys[org_id] = $org->id();
  } else { 
    $launchkeys[org_id] = -1;
  }

  $launch->read( $launchkeys );
  $launch->setall( $launchkeys );  // Set the foreign keys
  $launch->setall($_REQUEST, '/^launch_/');
  $launchpassword = md5(uniqid(rand(), true));

  $launch->set("password", $launchpassword);
  if ( $launch->id() ) {
     $launch->update();
     DPRT("Updated launch=$launch->id()");
  } else { 
     $launch->insert();
     DPRT("Added launch=$launch->id()");
  }

  // Log this digest
  $reqstr = mysql_real_escape_string(print_r($_REQUEST,TRUE));
  $quer = "insert into lti_digest (created_at, digest, request) values (NOW(), '$digest', '$reqstr');";
  mysql_query($quer);

  // Time to return a response, we either return a web service
  // response, debug outtput, or redirect back to ourselves

  $theurl = $_SERVER[SCRIPT_URI];
  $theuri = $_SERVER[REQUEST_URI];
  $i = strpos($theuri,'?') ;
  if ( $i > 0 ) {
    $theurl = $theurl . substr($theuri,$i) . '&';
  } else {
    $theurl = $theurl . '?';
  }
  $theurl = $theurl.'id='.$launch->id().'&password='.$launchpassword;
  
  if ( $launch && $launch->data() ) {
      $LTI = new LTIObject($launch->data());
      DPRT("User Data");
      DPRTR($LTI->user());
      DPRT("Course Data");
      DPRTR($LTI->course());
      DPRT("Membership Data");
      DPRTR($LTI->memb());
      DPRT("Organization Data");
      DPRTR($LTI->org());
  }

  DPRT("Request Dump");
  DPRTR($_REQUEST);
  DPRT("Server Dump");
  DPRTR($_SERVER);

  dumpDebugLog();

  // The web service response
  if ( $_REQUEST[action] == 'launchresolve' ) {
    print"<launchResponse>\n";
    print"   <status>success</status>\n";
    print"   <type>iframe</type>\n";
    print"   <launchUrl>".htmlspecialchars($theurl)."</launchUrl>\n";
    print"   <launchdebug>\n";
    print getDebugLogXML();
    print"   </launchdebug>\n";
    print"</launchResponse>\n";
  } else if ( $_REQUEST[action] == 'direct' && ! $_REQUEST[ltidebugpause] ) {
    if ( ! headers_sent() ) {
      header("Location: $theurl");
    } else {
      print '<script language="JavaScript">'."\n";
      print '  window.location="'.$theurl.'";'."\n";
      print "</script>";
    }
  } else {
      print '<a href="'.$theurl.'" target=_new >Click Here</a>'."\n";
      print "\n<pre>\nDEBUG LOG\n";
      print getDebugLogXML();
      print "</pre>\n";
  }
  exit();

} // End of the launch processing
