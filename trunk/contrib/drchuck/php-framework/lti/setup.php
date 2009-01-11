<?php
// Now we are in the tool startup code with 3 possible scenarios:
// (1) We are handling a GET request with id and password
// (2) We already have a set-up PHP session that we like
// (3) None of the above 

// From here on in, we need a session
session_start();

require_once("debug.php");
require_once("db.php");
require_once("orm.php");
require_once("object.php");

function clearlogin() {
    unset($_SESSION['lti_launch']);
}

// Redirect to login if we can
function redirect_login() {
    global $LTI_LOGIN;
    if ( $LTI_LOGIN ) {
        if ( headers_sent() ) {
            print "Headers already sent, unable to redirect to login page.\n";
        } else {
            $host = $_SERVER['HTTP_HOST'];
            $uri = rtrim(dirname($_SERVER['PHP_SELF']), '/\\');
            header("Location: http://$host$uri/$LTI_LOGIN");
            clearlogin();
            exit();
       }
    }
}

$launchdata = false;
try {
   // Deal with the situation where we see id/pw the first time
   // with an empty session or - we see it a second time on refresh
   // with a session id/pw on the request that matches session
   // If we have non-empty session, and it does not match the 
   // request parameters, clear the session
   if ( ! empty($_SESSION['lti_launch']) && ! empty($_SESSION['lti_launch_password']) ) {
      if ( $_REQUEST[id] && $_REQUEST[password] ) {
         // If we have both session and request parameters - demand they match
         if ( $_SESSION['lti_launch'] != $_REQUEST[id] || 
              $_SESSION['lti_launch_password'] != $_REQUEST[password] ) {
            DPRT("Session mis-match - new session started");
            unset($_SESSION['lti_launch']);
            unset($_SESSION['lti_launch_password']);
         }
      }
    }

    // Check to see if we already have a session for this browser
    if ( ! empty($_SESSION['lti_launch']) && ! empty($_SESSION['lti_launch_password']) ) {
        $launch = new ORM("launch", false,"lti_launch");
        $launch->get($_SESSION['lti_launch']);
        if ( ! $launch->id() ) {
            unset($_SESSION['lti_launch']);
            unset($_SESSION['lti_launch_password']);
           throw new Exception("Error launch session not found");
        }
   } else if ( ( $_REQUEST[id] && $_REQUEST[password] ) ) {
       $launch = new ORM("launch", false,"lti_launch");
       if ( ! $launch ) {
           throw new Exception("LTI Runtime - Datebase unable to instance user");
       }
    
       $launch->get($_REQUEST[id]);
       if ( ! $launch->id() ) {
           throw new Exception("LTI Runtime - Launch session not found");
       }
    
       $launchdata = $launch->data();
       $launchpassword = $launchdata[password];
       DPRT("password = ".$launchpassword);
    
       if ( $launchpassword == $_REQUEST[password] ) {
           $_SESSION['lti_launch'] = $launch->id();
           $_SESSION['lti_launch_password'] = $launchpassword;
       } else { 
           $launchdata = false;
            unset($_SESSION['lti_launch']);
            unset($_SESSION['lti_launch_password']);
           throw new Exception("LTI Runtime - launch entry expired");
       }
    
       // Set the password to something else!
       $launch->set("password", "NULL");
       $launch->update();
       DPRT("Updated launch=".$launch->id());
    } else { 
        unset($_SESSION['lti_launch']);
        unset($_SESSION['lti_launch_password']);
        redirect_login();
        $launch = false;
    }

    if ( $launch && $launch->data() ) {
        $LTI = new LTIObject($launch->data());
    }
}
catch(Exception $e ) {
    DPRT($e->getMessage());
    redirect_login();
    $LTI = false;
}
?>
