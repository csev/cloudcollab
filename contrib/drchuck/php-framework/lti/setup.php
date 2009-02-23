<?php
// Now we are in the tool startup code with 3 possible scenarios:
// (1) We are handling a GET request with id 
// (2) We already have a set-up PHP session that we like
// (3) None of the above 

// From here on in, we need a session
session_start();

require_once("debug.php");
require_once("db.php");
require_once("orm.php");
require_once("object.php");

function clearlogin() {
    unset($_SESSION['lti_launch_id']);
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
   // If we have an id on the URL, accept it, attempt to set the session.
   
   if ( $_REQUEST[lti_launch_id] ) {
       $launchid = $_REQUEST[lti_launch_id];
   } else  if (  ! empty($_SESSION['lti_launch_id']) ) {
       $launchid = $_SESSION[lti_launch_id];
   } else {
       unset($_SESSION['lti_launch_id']);
       redirect_login();
       $launchid = false;
   }

   if ( $launchid ) {
       $launch = new ORM("launch", false,"lti_launch");
       if ( ! $launch ) {
           throw new Exception("LTI Runtime - Datebase unable to instance user");
       }
    
       $launch->get($launchid);
       if ( ! $launch->id() ) {
           throw new Exception("LTI Runtime - Launch session not found");
       }
    
       $launchdata = $launch->data();
    
       $_SESSION['lti_launch_id'] = $launch->id();

        if ( $launch && $launch->data() ) {
            $LTI = new LTIObject($launch->data());
        }
    }
}
catch(Exception $e ) {
    DPRT($e->getMessage());
    redirect_login();
    $LTI = false;
}
?>
