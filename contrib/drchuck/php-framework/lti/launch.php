<?php

// TODO: Add Options for nonce time, etc - look at the Python code

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

$Settings = array(
              'nonce_time' => 10000000,
              'allow_digest_reuse' => true,
              'digest_expire' => "date_sub(now(), interval 1 hour)",
              'digest_cleanup_count'  => 100,
              'launch_expire' => "date_sub(now(), interval 1 day)",
              'launch_cleanup_count' => 100,
              'auto_create_orgs'  => true,
              'default_org_secret'  => "secret",
              'auto_create_courses'  => true,
              'default_course_secret'  => "secret");

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
    // Don't put this into production - can reveal secrets
    print "\n<!--\n".getDebugLogXML()."\n-->\n";
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

  // Check the time - reject if too old
  if ( ! checkTime($_REQUEST[sec_created], $Settings["nonce_time"]) ) {
     lti_launchfail("Nonce computation failed (expired) see simplelti.appspot.com");
     exit();
  }

  // Check to see if the digest is right and within the specified time.

  require_once("db.php");

  // Check the digest for one-time use - discard if a replay
  $digest = mysql_real_escape_string($_REQUEST[sec_digest]);
  $quer = "SELECT id FROM lti_digest WHERE digest='$digest'";
  DPRT($quer);
  $result = mysql_query($quer);
  $num_rows = mysql_num_rows($result);
  DPRT($num_rows);
  if ( $num_rows > 0 ) {
     if ( $Settings['allow_digest_reuse'] ) {
       DPRT("Reused existing launch - only do this when debugging");
     } else {
       lti_launchfail("Cannot reuse SimpleLTI security digest");
       exit();
     }
  } else {
     DPRT("New Launch $digest");
  }

  require_once("orm.php");

  // Look through courses to see if we match a secret
  $courseid = $_REQUEST[course_id];
  $validated = false;
  $coursefound = false;

  $crs = new ORM("course", false, "lti_course");
  $sql = "SELECT * FROM lti_course WHERE course_id = '".mysql_real_escape_string($courseid)."'";
  DPRT($sql);
  $result = mysql_query($sql);
  while($row = mysql_fetch_array($result))
  {
      $coursefound = true;
      $crs->load_from_row($result, $row);
      $coursesecret = $crs->data(secret);
      if ( $coursesecret == NULL ) continue;
      if ( checkNonce($_REQUEST[sec_nonce], $_REQUEST[sec_created], 
                  $_REQUEST[sec_digest], $coursesecret,  $Settings["nonce_time"]) ) {
         DPRT("Nonce validated using secret from course");
         $validated = true;
         break;
     }
     $crs->clear();  // This data is not valid
  }

  // If we have not yet validated, and we found no matching courses at all, 
  // we might be auto-creating courses 
  $coursecreate = false;
  if ( ! $validated && ! $coursefound && $Settings['auto_create_courses'] ) {

      if ( checkNonce($_REQUEST[sec_nonce], $_REQUEST[sec_created], 
                  $_REQUEST[sec_digest], $Settings["default_course_secret"],  $Settings["nonce_time"]) ) {
         DPRT("Nonce validated from default secret");
         $coursecreate = true;
      } else {
         lti_launchfail("Nonce computation failed (default secret) see simplelti.appspot.com");
         exit();
      }
  } else if ( ! $validated ) {
      if ( $coursefound ) {
        lti_launchfail("Nonce computation failed (bad secret) see simplelti.appspot.com");
      } else {
        lti_launchfail("Nonce computation failed (no course) see simplelti.appspot.com");
      }
      exit();
  }

  // Clean up out nonce/digest table - for now every time - later random number
  $expirestr = "date_sub(now(), interval 1 hour)";
  if ( $Settings['digest_expire'] ) $expirestr = $Settings['digest_expire'];
  $sql = "delete from lti_digest where created_at < $expirestr";
  DPRT($sql);
  mysql_query($sql);

  // Log this digest - We only log the good digests - not the failed ones - we
  // don't want a DOS where our data grows
  $reqstr = mysql_real_escape_string(print_r($_REQUEST,TRUE));
  $quer = "insert into lti_digest (created_at, digest, request) values (NOW(), '$digest', '$reqstr');";
  mysql_query($quer);

/* If the organization is signed, we scope the course and user to the
   organization - the organization is the top object and course/user
   are children.

   org.course_id = -1 (this is a global org)
   user.org_id <> 0 
   course.org_id <> 0
   
   If the organization is not signed, the course is all we have so the
   course is "globally scoped" and the org and user are children 
   of the course.
   
   course.org_id = -1 - (this is a global course)
   org.course_id <> 0
   user.course_id <> 0 , user.org_id = null (org_id is null because user is not global)
*/
   
  $orgid = $_REQUEST[org_id];
  $orgsigned = false;
  if ( $orgid ) {
    $org = new ORM("org", false, "lti_org");
    $org->read( array( "org_id" => $orgid, "course_id" => -1) );
    if ( $org->id() ) {
       $orgdata = $org->data();
       $orgsecret = $orgdata[secret];
       DPRT("org secret from database $orgsecret");
       if ( checkNonce($_REQUEST[sec_nonce], $_REQUEST[sec_created], 
                       $_REQUEST[sec_org_digest], $orgsecret, 10000000) ) {
         DPRT("Organization secret matches");
         $orgsigned = true;
      } else {
         DPRT("Organiztion secret failed");
         $org->clear();  // Get rid of the data because we cannot trust it
      }
    }
  }

  // The course is signed from the first nonce computation - it may also
  // be part of an organization
  // Make the course belong to an organization
  if ( $coursecreate && $Settings["auto_create_courses"] ) {
    $crs->setall($_REQUEST, '/^course_/');
    if ( $orgsigned ) {
      $crs->setall( array( "course_id" => $courseid, "org_id" => $org->id()) ) ;
    } else {
      $crs->setall( array( "course_id" => $courseid, "org_id" => -1 ) ) ;
    }
    $crs->setall( array("secret" => $Settings["default_course_secret"] ) ) ;
    DPRT("Inserting course $courseid");
    $crs->insert();
  } 
  
  // If we don't have an organization by now, we make a course-scoped
  // Organization and set its parent course.
  if ( ! $orgsigned && $orgid ) {
    $org = new ORM("org", false, "lti_org");
    $org->read( array( "org_id" => $orgid, "course_id" => $crs->id()) ) ;
    $org->setall($_REQUEST, '/^org_/');
    $org->setall(array("course_id" => $crs->id()));

    if ( $org->id() ) {
      $org->update();
    } else if ( $Settings["auto_create_orgs"] ) {
      $org->insert();
    } else {
       lti_launchfail("Organization creation not allowed");
       exit();
    }
  }

  // Make the user organizational scoped or course scoped
  // We never set user.org_id to be -1 - there is no such thing as 
  // a "global" user - they are either course or organzation scoped.
  $userid = $_REQUEST[user_id];
  // Add the user if necessary
  $usr = new ORM("user", false, "lti_user");
  if ( $orgsigned ) {
    $usr->read( array( "user_id" => $userid, "org_id" => $org->id()) ) ;
    $usr->setall( array( "user_id" => $userid, "org_id" => $org->id()) ) ;
  } else {
    $usr->read( array( "user_id" => $userid, "course_id" => $crs->id()) ) ;
    $usr->setall( array( "user_id" => $userid, "course_id" => $crs->id()) ) ;
  }
  $usr->setall($_REQUEST, '/^user_/');
  if ( $usr->id() ) {
     $usr->update();
  } else {
     $usr->insert();
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
    // Make sure to never get a org with a primary key of -1
    $launchkeys[org_id] = -1;
  }

  $launch->read( $launchkeys );
  $launch->setall( $launchkeys );  // Set the foreign keys
  $launch->setall($_REQUEST, '/^launch_/');
  $launchpassword = md5(uniqid(rand(), true));

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
  $theurl = $theurl.'lti_launch_id='.$launch->id();
  
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
