/**********************************************************************************
 * $URL$
 * $Id$
 **********************************************************************************
 *
 * Copyright (c) 2009 IMS Global Learning Consortium, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 * implied. See the License for the specific language governing
 * permissions and limitations under the License. 
 *
 **********************************************************************************/
package org.imsglobal.simplelti;

import java.util.Locale;
import java.util.UUID;
import java.util.Date;
import java.util.TimeZone;
import java.util.Properties;
import java.text.DateFormat;
import java.text.SimpleDateFormat;

import java.io.UnsupportedEncodingException;
import java.security.NoSuchAlgorithmException;
import java.security.MessageDigest;

import java.net.Socket;
import java.net.URL;
import java.net.URLConnection;
import java.net.URLEncoder;
import java.net.HttpURLConnection;

import java.util.Map;
import java.util.List;

import org.imsglobal.simplelti.XMLMap;

import java.io.PrintWriter;
import java.io.InputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.io.OutputStream;
import java.io.BufferedReader;
import java.io.InputStreamReader;

/* Leave out until we have JTidy 0.8 in the repository 
import org.w3c.tidy.Tidy;
import java.io.ByteArrayOutputStream;
*/

/**
 * Some Utility code for IMS Simple LTI
 * http://www.anyexample.com/programming/java/java_simple_class_to_compute_sha_1_hash.xml
 */
public class SimpleLTIUtil {

/*
   	public static void main(String[] av)
   	{
		String testDates[] = {
			"2008-06-17T22:29:17Z",
			"2008-06-17T18:29:17-0400",
			"2008-06-17T22:29:17" }; // Will assume GMT
	
		Date first = parseISO8601(testDates[0]);
		System.out.println(testDates[0]+" -> "+first);
        	for(int i=1; i<testDates.length; i++) 
		{
			Date next = parseISO8601(testDates[i]);
			if ( next == null )
			{
				System.out.println(testDates[i]+" ***** Parse failed");
				continue;
			}
			System.out.println(testDates[i]+" -> "+next);
			if ( first.getTime() != next.getTime() )
			{
				System.out.println("Mismatch first="+first+" test="+testDates[i]+" new="+next);
			}
		}
   	}
*/

    /** To turn on really verbose debugging */
    private static boolean verbosePrint = false;

    // Simple Debug Print Mechanism
    public static void dPrint(String str)
    {
        if ( verbosePrint ) System.out.println(str);
    }

	public static String BASE64SHA1(String text) 
	{
		// System.out.println("BASE64SHA1 text="+text);
		String key = null;
		try
		{
			MessageDigest md;
			md = MessageDigest.getInstance("SHA-1");
			byte[] sha1hash = new byte[40];
			md.update(text.getBytes("utf-8"), 0, text.length());
			sha1hash = md.digest();
			key = new sun.misc.BASE64Encoder().encode(sha1hash);
		}
		catch(NoSuchAlgorithmException e)
		{
		}
		catch(UnsupportedEncodingException e)
		{
		}
		// System.out.println("BASE64SHA1 returning key "+key);
		return key;
    	}

	/** Encode a plaintext string into Base64 using UTF-8
	 */
	public static String encodeBase64(String unencoded)
 	{
		if ( unencoded == null ) return null;
		try 
		{
			byte[] bytes = unencoded.getBytes("UTF8");
			String encoded = new sun.misc.BASE64Encoder().encode(bytes);
			// System.out.println("enencoded="+unencoded+" encoded="+encoded);
			return encoded;
		}
		catch (UnsupportedEncodingException ex)
		{
			return null;
		}
	}

	// http://www.dynamicobjects.com/d2r/archives/003057.html
	public static SimpleDateFormat RFC822DATEFORMAT 
		= new SimpleDateFormat("EEE', 'dd' 'MMM' 'yyyy' 'HH:mm:ss' 'Z", Locale.US);

	// Parse a subset of the ISO8601 dates - in preference order
	private static String outBoundISO8601 = "yyyy-MM-dd'T'HH:mm:ss'Z'";   // Assume GMT
 	private static String inBoundISO8601B = "yyyy-MM-dd'T'HH:mm:ssZ";  // Accept TimeZone offset
 	private static String inBoundISO8601C = "yyyy-MM-dd'T'HH:mm:ss";  // Assume GMT

	public static Date parseISO8601(String str)
	{
                SimpleDateFormat formatter = new SimpleDateFormat(outBoundISO8601);
                try {
			formatter.setTimeZone(TimeZone.getTimeZone("GMT"));
                	Date dt = formatter.parse(str);
                	// System.out.println("Outbound="+dt);
			return dt;
                } catch (Exception e) {
               		// Keep on trying 
                }
                formatter = new SimpleDateFormat(inBoundISO8601B);
                try {
			// This should have timezone for us to read
			formatter.setLenient(true);
                	Date dt = formatter.parse(str);
                	// System.out.println("Inbound B="+dt);
			return dt;
                } catch (Exception e) {
               		// Keep on trying 
                }
                formatter = new SimpleDateFormat(inBoundISO8601C);
                try {
			formatter.setTimeZone(TimeZone.getTimeZone("GMT"));
			formatter.setLenient(true);
                	Date dt = formatter.parse(str);
                	// System.out.println("Inbound C="+dt);
			return dt;
                } catch (Exception e) {
               		// Keep on trying 
                }
		return null;
	}

	public static String getDateAsRFC822String()
	{
		return getDateAsRFC822String(new Date());
        }
	public static String getDateAsRFC822String(Date date)
	{
		return RFC822DATEFORMAT.format(date);
	}

	/* 
	 * We are going to force our dates to GMT and stick a Z on the end
         *       (eg 1997-07-16T19:20:30Z)
         */
	public static String getDateAsISO8601String()
	{
		return getDateAsISO8601String(new Date());
        }

	public static String getDateAsISO8601String(Date date)
	{
		SimpleDateFormat formatter = new SimpleDateFormat(outBoundISO8601);
		formatter.setTimeZone(TimeZone.getTimeZone("GMT"));
		String result = formatter.format(date);
		return result;
	}

	// PasswordDigest = Base64 \ (SHA1 (Nonce + CreationTimestamp + Password))
	// X-WSSE: UsernameToken Username="ltitc", PasswordDigest="5BSxco0uWjGtYrTDaxgcUnEfviA=",  
	//      Nonce="13294281-1645-42c6-93a8-2f486cff2f7c", Created="2008-05-08T00:14:06-04:00"
        public static String getNonce()
	{
		return UUID.randomUUID().toString();
        }

        public static String getDigest(String nonce, String timestamp, String password)
        {
		String presha1 = nonce + timestamp + password;
		// System.out.println("presha1="+presha1);
		String digest = SimpleLTIUtil.BASE64SHA1(presha1);
		// System.out.println("digest="+digest);
		return digest;
	}


	private static void setErrorMessage(Properties retProp, String message)
	{
		retProp.setProperty("message",message);
		retProp.setProperty("status","fail");
        }

    public static boolean validateDescriptor(String descriptor)
    {
        Map<String,Object> tm = XMLMap.getFullMap(descriptor);

        if ( tm == null )
        {
                return false;
        }

        // We demand an endpoint
        String lti2EndPoint = XMLMap.getString(tm,"/toolInstance/launchurl");
        if ( lti2EndPoint == null || lti2EndPoint.trim().length() < 1 )
        {
                return false;
        }
        return true;
    }

    public static void addNonce(Properties newMap, String lti2Password, String org_id, String org_secret)
    {
        // Setup the normal digest
        String nonce = SimpleLTIUtil.getNonce();
        String created = SimpleLTIUtil.getDateAsISO8601String();
        String sec_digest = null;
        String sec_org_digest = null;
        if ( lti2Password != null ) {
                sec_digest = SimpleLTIUtil.getDigest(nonce, created, lti2Password);
        }

        if ( org_id != null && org_secret != null ) {
                sec_org_digest = SimpleLTIUtil.getDigest(nonce, created, org_secret);
        }
        if ( sec_digest != null || sec_org_digest != null ) {
                newMap.setProperty("sec_nonce", nonce);
                newMap.setProperty("sec_created", created);
        }
        if ( sec_digest != null ) newMap.setProperty("sec_digest", sec_digest);
        if ( sec_org_digest != null ) newMap.setProperty("sec_org_digest", sec_org_digest);
        if ( org_id != null ) {
                newMap.setProperty("org_id", org_id);
	}

    }

    public static Properties doLaunch(String lti2EndPoint, Properties newMap)
    {
        Properties retProp = new Properties();
	retProp.setProperty("status","fail");

	String postData = "";
	// Yikes - iterating through properties is nasty
	for(Object okey : newMap.keySet() ) {
		if ( ! (okey instanceof String) ) continue;
		String key = (String) okey;
                if ( key == null ) continue;
		String value = newMap.getProperty(key);
		if ( value == null ) continue;
		if ( value.equals("") ) continue;
		// Should this be UTF-8 ???
		value = URLEncoder.encode(value);
		if ( postData.length() > 0 ) postData = postData + "&";
                        postData = postData + URLEncoder.encode(key) + "=" + value;
	}
        if ( postData != null) retProp.setProperty("_post_data",postData);
        dPrint("LTI2 POST="+postData);

	String postResponse = null;

        URLConnection urlc = null;
        try 
        {
                // Thanks: http://xml.nig.ac.jp/tutorial/rest/index.html
                URL url = new URL(lti2EndPoint);

                InputStream inp = null;
                // make connection, use post mode, and send query
                urlc = url.openConnection();
                urlc.setDoOutput(true);
                urlc.setAllowUserInteraction(false);
                PrintStream ps = new PrintStream(urlc.getOutputStream());
                ps.print(postData);
                ps.close();
                dPrint("Post Complete");
                inp = urlc.getInputStream();

                // Retrieve result
                BufferedReader br = new BufferedReader(new InputStreamReader(inp));
                String str;
                StringBuffer sb = new StringBuffer();
                while ((str = br.readLine()) != null) {
                        sb.append(str);
                        sb.append("\n");
                }
                br.close();
                postResponse = sb.toString();

                if ( postResponse == null ) {
                	setErrorMessage(retProp, "Launch REST Web Service returned nothing");
                        return retProp;
                }
        }
        catch(Exception e) 
        {
                // Retrieve error stream if it exists
                if ( urlc != null && urlc instanceof HttpURLConnection ) 
                {
                    try {
                            HttpURLConnection urlh = (HttpURLConnection) urlc;
                            BufferedReader br = new BufferedReader(new InputStreamReader(urlh
                                        .getErrorStream()));
                            String str;
                            StringBuffer sb = new StringBuffer();
                            while ((str = br.readLine()) != null) {
                                    sb.append(str);
                                    sb.append("\n");
                            }
                            br.close();
                            postResponse = sb.toString();
                            dPrint("LTI ERROR response="+postResponse);
                    } 
                    catch(Exception f)
                    {
                            dPrint("LTI Exception in REST call="+e);
                            // e.printStackTrace();
                            setErrorMessage(retProp, "Failed REST service call. Exception="+e);
                            postResponse = null;
                            return retProp;
                    }
                }
		else 
                {
			dPrint("LTI General Failure"+e.getMessage());
                        // e.printStackTrace();
                }
        }

        if ( postResponse != null) retProp.setProperty("_post_response",postResponse);
        dPrint("LTI2 Response="+postResponse);
        // Check to see if we received anything - and then parse it
        Map<String,String> respMap = null;
        if ( postResponse == null ) {
                setErrorMessage(retProp, "Web Service Returned Nothing");
                return retProp;
        } else {
                if ( postResponse.indexOf("<?xml") != 0 ) {
                   int pos = postResponse.indexOf("<launchResponse");
                   if ( pos > 0 ) {
                      System.out.println("Warning: Dropping first "+pos+" non-XML characters of response to find <launchResponse");
                      postResponse = postResponse.substring(pos);
		   }
                }
                respMap = XMLMap.getMap(postResponse);
        }
        if ( respMap == null) {
		String errorOut = postResponse;
                if ( errorOut.length() > 500 ) {
                       errorOut = postResponse.substring(0,500);
                }
                System.out.println("Error Parsing Web Service XML:\n"+errorOut+"\n");
                setErrorMessage(retProp, "Error Parsing Web Service XML");
                return retProp;
        }

        // We will tolerate this one backwards compatibility
        String launchUrl = respMap.get("/launchUrl");
	String launchWidget = null;

	if ( launchUrl == null ) {
		launchUrl = respMap.get("/launchResponse/launchUrl");
	}

	if ( launchUrl == null ) {
		launchWidget = respMap.get("/launchResponse/widget");

/* Remove until we have jTidy 0.8 or later in the repository
                if ( launchWidget != null && launchWidget.length() > 0 ) {
			System.out.println("Pre Tidy:\n"+launchWidget);
			Tidy tidy = new Tidy();
			tidy.setIndentContent(true);
			tidy.setSmartIndent(true);
			tidy.setPrintBodyOnly(true);
			tidy.setTidyMark(false);
			// tidy.setQuiet(true);
			// tidy.setShowWarnings(false);
			InputStream is = new ByteArrayInputStream(launchWidget.getBytes());
			OutputStream os = new ByteArrayOutputStream();
			tidy.parse(is,os);
			String tidyOutput = os.toString();
			System.out.println("Post Tidy:\n"+tidyOutput);
			if ( tidyOutput != null && tidyOutput.length() > 0 ) launchWidget = os.toString();
		}
*/
	}

        dPrint("XXX launchUrl = "+launchUrl);
        dPrint("launchWidget = "+launchWidget);

	if ( launchUrl == null && launchWidget == null ) 
        {
                String eMsg = respMap.get("/launchResponse/code") + ":" 
			+ respMap.get("/launchResponse/description");
                setErrorMessage(retProp, "Error on Launch:"+eMsg);
		return retProp;
        }

        if ( launchUrl != null ) retProp.setProperty("launchurl",launchUrl);
        if ( launchWidget != null ) retProp.setProperty("launchwidget",launchWidget);
	String postResp = respMap.get("/launchResponse/type");
        if ( postResp != null ) retProp.setProperty("type",postResp);
	retProp.setProperty("status","success");

	return retProp;
    }

    // Set the HTML Text in the htamltext property
    public static void generateHtmlText(Properties retProp, Properties newMap,
                                        String lti2FrameHeight)
    {

        // launchurl=http://www.youtube.com/v/f90ysF9BenI, status=success, type=iFrame

        String status = retProp.getProperty("status");
        String launchurl = retProp.getProperty("launchurl");
        if ( ! "success".equalsIgnoreCase(status) )
        {
                return;
        }
        String theType = retProp.getProperty("type");
        // Check to see if we got a POST
        String htmltext = null;
        if ( "iframe".equalsIgnoreCase(theType) )
        {
                // Not good
                if ( launchurl == null ) return;
                StringBuffer text = new StringBuffer();
                text.append("<iframe ");
                text.append("title=\"Site Info\" ");
                if ( lti2FrameHeight == null ) lti2FrameHeight = "1200";
                text.append("height=\""+lti2FrameHeight+"\" \n");
                text.append("width=\"100%\" frameborder=\"0\" marginwidth=\"0\"\n");
                text.append("marginheight=\"0\" scrolling=\"auto\"\n");
                text.append("src=\""+launchurl+"\">\n");
                text.append("Your browser does not support iframes. <br>");
                text.append("<a href=\""+launchurl+"\" target=\"_new\">Press here for content</a>\n");
                text.append("</iframe>");
                htmltext = text.toString();
                retProp.setProperty("htmltext",htmltext);
        }
        else if ( "widget".equalsIgnoreCase(theType) )
        {
                htmltext = retProp.getProperty("launchwidget");
                retProp.setProperty("htmltext",htmltext);
        }
        else  // Post or otherwise
        {
                // Not good
                if ( launchurl == null ) return;
                StringBuffer text = new StringBuffer();
                text.append(postText1);
                text.append("<form action=\""+launchurl+"\" name=\"ltiLaunchForm\" method=\"post\">\n" );
                for(Object okey : newMap.keySet() )
                {
                        if ( ! (okey instanceof String) ) continue;
                        String key = (String) okey;
                        if ( key == null ) continue;
                        String value = newMap.getProperty(key);
                        if ( value == null ) continue;
                        if ( "action".equalsIgnoreCase(key) ) continue;
                        if ( key.startsWith("internal_") ) continue;
                        if ( key.startsWith("_") ) continue;
                        if ( value.equals("") ) continue;
                        // Should this be UTF-8 ???
                        // value = URLEncoder.encode(value);
                        // key = URLEncoder.encode(key);
                        text.append("<input type=\"hidden\" size=\"40\" name=\"");
                        text.append(key);
                        text.append("\" value=\"");
                        text.append(value);
                        text.append("\"/>\n");
                }
                text.append(postText2);
                htmltext = text.toString();
                retProp.setProperty("htmltext",htmltext);
        }
    }

    private final static String postText1 =
"<head>\n" +
"  <script language=\"javascript\"> \n" +
"    function go() { \n" +
"        document.ltiLaunchForm.submit(); \n" +
"    } \n" +
" </script> \n" +
"</head>\n" +
"<body onLoad=\"NOgo()\">\n";

    private final static String postText2 =
" <input type=\"hidden\" size=\"40\" name=\"action\" value=\"direct\"/>\n" +
" <input type=\"submit\" value=\"Continue\">  If you are not redirected in 15 seconds press Continue.\n" +
"</form>\n";

    // Determine if a post launch was requested
    public static boolean isPostLaunch(Properties props)
    {
	String launchType = props.getProperty("type");
	if (launchType == null ) return true;
	launchType = launchType.toLowerCase();
	return "post".equals(launchType);
    }

    // Determine if a post launch is desired 
    public static boolean isPostLaunch(String descriptor)
    {
	Map<String,Object> tm = XMLMap.getFullMap(descriptor);
	if ( tm == null ) return false;
	String launchTypes = XMLMap.getString(tm,"/toolInstance/accept_targets");
System.out.println("Launchtypes = "+launchTypes);
	if ( launchTypes != null ) launchTypes = launchTypes.toLowerCase();
	if ( launchTypes == null || launchTypes.startsWith("post") )
	{
		return true;
	}
	return false;
    }

    // Return HTML for a POST launch

    // Set the HTML Text in the htamltext property
    public static String postLaunchHTML(Properties newMap) {
System.out.println("newMap = "+newMap);
		String launchurl = newMap.getProperty("launchurl");
System.out.println("launchurl = "+launchurl);
                if ( launchurl == null ) return null;
                StringBuffer text = new StringBuffer();
                text.append(postText1);
                text.append("<form action=\""+launchurl+"\" name=\"ltiLaunchForm\" method=\"post\">\n" );
                for(Object okey : newMap.keySet() )
                {
                        if ( ! (okey instanceof String) ) continue;
                        String key = (String) okey;
                        if ( key == null ) continue;
                        String value = newMap.getProperty(key);
                        if ( value == null ) continue;
                        if ( key.startsWith("internal_") ) continue;
                        if ( key.startsWith("_") ) continue;
                        if ( "action".equalsIgnoreCase(key) ) continue;
                        if ( "launchurl".equalsIgnoreCase(key) ) continue;
                        if ( value.equals("") ) continue;
                        // Should this be UTF-8 ???
                        // value = URLEncoder.encode(value);
                        // key = URLEncoder.encode(key);
                        text.append("<input type=\"hidden\" size=\"40\" name=\"");
                        text.append(key);
                        text.append("\" value=\"");
                        text.append(value);
                        text.append("\"/>\n");
                }
                text.append(postText2);
                String htmltext = text.toString();
System.out.println("htmltext="+htmltext);
	return htmltext;
    }

    public static Properties getToolSettings(String str)
    {
	Map<String,Object> tm = XMLMap.getFullMap(str);
	return getToolSettings(tm);
    }

    public static Properties parseDescriptor(String descriptor)
    {
      
        Map<String,Object> tm = null;
        try
        {
                tm = XMLMap.getFullMap(descriptor);
        } 
        catch (Exception e) {
                System.out.println("Exception parsing SimpleLTI descriptor"+e.getMessage());
		return null;
        }

        dPrint("tm="+tm);
        if ( tm == null )
        {
                // TODO: Need to send back an error code
                return null;
        }

        // We demand an endpoint
        String lti2EndPoint = XMLMap.getString(tm,"/toolInstance/launchurl");
        if ( lti2EndPoint == null || lti2EndPoint.trim().length() < 1 )
        {
                // TODO: Need to send back an error code
                return null;
        }

        Properties retval = getToolSettings(tm);

        String lti2ToolId = XMLMap.getString(tm,"/toolInstance/tool_id");
        String lti2LaunchTypes = XMLMap.getString(tm,"/toolInstance/accept_targets");

        if ( lti2EndPoint != null ) retval.setProperty("launchurl", lti2EndPoint);
        if ( lti2ToolId != null ) retval.setProperty("tool_id", lti2ToolId);
        if ( lti2LaunchTypes != null ) retval.setProperty("accept_targets", lti2LaunchTypes);
        return retval;
    }

    public static Properties getToolSettings(Map<String,Object> tm)
    {
	Properties retVal = new Properties();
        if ( tm == null ) return retVal;
        List<Map<String,Object>> theList = XMLMap.getList(tm, "/toolInstance/tool-settings/setting");
        for ( Map<String,Object> setting : theList) {
                dPrint("Setting="+setting);
                String key = XMLMap.getString(setting,"/!key"); // Get the key atribute
                String value = XMLMap.getString(setting,"/"); // Get the value
                dPrint("key="+key+" val="+value);
		retVal.setProperty(key,value);
        }
	return retVal;
    }

    public static String getFrameHeight(String str)
    {
        String frameHeight = getToolSettings(str).getProperty("frameheight");
	if ( frameHeight == null ) frameHeight = "1200";
	return frameHeight;
    }

}
