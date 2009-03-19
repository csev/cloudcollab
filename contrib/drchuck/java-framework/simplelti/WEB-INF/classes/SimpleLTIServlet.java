import java.io.*;
import javax.servlet.*;
import javax.servlet.http.*;

import java.util.HashMap;
import java.util.UUID;

import org.imsglobal.simplelti.SimpleLTIUtil;

/* This is a very simple servlet which implements 
   IMS Simple Learning Tools Interoperability (simplelti.appspot.com)
   Its main purpose is as sample code and can be freely reused.

   It is Copyright 2009, IMS Global Learning 
   Under the Apache 2.0 license

   It is written by Charles Severance (csev@umich.edu) www.dr-chuck.com
*/

public class SimpleLTIServlet extends HttpServlet {

    public final String myPath = "http://localhost:8080/simplelti/launch";

    // A simple mechanism to emulate organizational passwords
    HashMap<String, String> orgs = null;

    // A simple mechanism to keep used digests
    HashMap<String, String> digests = null;

    // A Simple Mechanism to track launches
    HashMap<String, String> launches = null;

    public static final String iframeresponse = "<launchResponse>\n" +
      "   <status>success</status>\n" +
      "   <type>iFrame</type>\n" +
      "   <launchUrl>LAUNCHURL</launchUrl>\n" +
      "</launchResponse>\n";

    public static final String errorresponse = "<launchResponse>\n" +
      "    <status>fail</status>\n" +
      "    <code>BadPasswordDigest</code>\n" +
      "    <description>DESC</description>\n" +
      "</launchResponse>\n";

    public void init()
    {
	System.out.println("SimpleLTIServlet initialized - check path:");
	System.out.println(myPath);
        orgs = new HashMap<String, String> ();
        orgs.put("umich.edu", "secret");
        digests = new HashMap<String, String> ();
        launches = new HashMap<String, String> ();
    }

    public void doGet(HttpServletRequest request,
                      HttpServletResponse response)
        throws IOException, ServletException
    {

	String launchid = request.getParameter("launchid");
        System.out.println("Processing GET request launchid="+launchid);
       	PrintWriter out = response.getWriter();
	
      	out.println("<html>");
       	out.println("<body bgcolor=\"white\">");
        if ( launchid == null ) {
	    out.println("GET request expects launch ID\n");
        } else {
	    String launchdata = launches.get(launchid);
            if ( launchdata == null ) {
               out.println("No data found for launch="+launchid);
            } else {
               out.println("Launch found id="+launchid+"<br/>\n");
	       out.println(launchdata);
  	   }
    	}
       	out.println("</body>");
       	out.println("</html>");
    }

    public void doPost(HttpServletRequest request,
                      HttpServletResponse response)
        throws IOException, ServletException
    {

	String action = request.getParameter("action");
	String nonce = request.getParameter("sec_nonce");
	String created = request.getParameter("sec_created");
	String org_digest = request.getParameter("sec_org_digest");
	String course_id = request.getParameter("course_id");
	String org_id = request.getParameter("org_id");
	String user_id = request.getParameter("user_id");

        if ( action == null || nonce == null || created == null || org_digest == null || 
             course_id == null || org_id == null || user_id == null ) {
                doError(request, response, "Missing required parameter");
		return;
        }
        action = action.toLowerCase();

        String org_secret = orgs.get(org_id);
        if ( org_secret == null ) {
                doError(request, response, "No organizational secret found");
		return;
        }

        // Check the signature
        String test_org_digest = SimpleLTIUtil.getDigest(nonce, created, org_secret);
        if ( ! test_org_digest.equals(org_digest) ) {
                doError(request, response, "Organizational secret does not match");
		return;
        }

        // Check for digest reuse
        String old_digest = digests.get(org_digest);
        if ( old_digest != null ) {
                // doError(request, response, "Digest reused");
		// return;
		System.out.println("Digest reuse tolerated during testing");
	}
	digests.put(org_digest, "used");

        // At this point, the signature has been validated so we can trust
        // The material - create the course (also indexed by org_id)

        // course_id is unique within org_id (multi-tenancy)
	String course_code = request.getParameter("course_code");
        System.out.println("Create course org_id="+org_id+" course_id="+course_id+" course_code="+course_code);

        // user_id is unique within org_id (multi-tenancy)
	String firstname = request.getParameter("user_firstname");
	String lastname = request.getParameter("user_lastname");
	String email = request.getParameter("user_email");
        System.out.println("Create user org_id="+org_id+" user_id="+user_id+
                           " email="+email+" "+lastname+", "+firstname);

	// Role is either Instructor or Student or Admin - generally treat admin as student
	String role = request.getParameter("user_role");
	if ( role == null ) role = "student";
        role = role.toLowerCase();
        boolean isInstructor = role.equals("instructor");
	// The membership should be keyed by the primary key of the user and
	// course rows, not the user_id and course_id - because of multi-tenancy
	System.out.println("Create membership org_id="+org_id+" course_id"+course_id+" user_id="+user_id+" instructor="+isInstructor);
        
        // Now we create a session logging in the user, and setting the course, etc
        // We call this a launch.  Normally it lives in a table - for now we put
	// in a big string in our launch map.
        String launchid = UUID.randomUUID().toString();
	String launchdata = "org_id="+org_id+" course_id="+course_id+" course_code="+course_code+"\n" + 
                            " user_id="+user_id+" email="+email+"\n" + 
			    " role="+role+"\n";

        System.out.println("Launchid="+launchid);
        launches.put(launchid, launchdata);

        String returl = myPath + "?launchid="+launchid;
        
        if ( "launchresolve".equals(action) || "launchhtml".equals(action) ) {
        	if ( "launchresolve".equals(action) ) {
        		response.setContentType("application/xml");
		} else {
        		response.setContentType("text/html");
		}
        	PrintWriter out = response.getWriter();
	        String outstr = iframeresponse.replace("LAUNCHURL", returl);
        	if ( "launchhtml".equals(action) ) {
			outstr = outstr.replace("<","&lt;");
			outstr = outstr.replace(">","&gt;");
			out.println("<pre>");
                	out.println(outstr); 
			out.println("</pre>");
		} else {
                	out.println(outstr); 
		}
		System.out.println("Returned XML Response="+ returl);
        } else {
                response.setContentType("text/plain");
                response.sendRedirect(returl);
        	PrintWriter out = response.getWriter();
		out.println("Redirected to "+returl);
		System.out.println("Redirected to "+ returl);
	}

    }

    public void doError(HttpServletRequest request,
                      HttpServletResponse response, String message)
        throws IOException, ServletException
    {
        	response.setContentType("text/html");
        	PrintWriter out = response.getWriter();
	
        	out.println("<html>");
        	out.println("<body bgcolor=\"white\">");
		out.println(message);
        	out.println("</body>");
        	out.println("</html>");
	  	System.out.println("Error processing request: " + message);
     }
}




