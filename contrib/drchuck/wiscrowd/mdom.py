from xml.dom import minidom
import string

def mdom_parse(str) :
    doc = minidom.parseString(str)
    retval = dict()
    mdom_descend(retval, doc, "/")
    return retval

def mdom_descend(di, node, pth) :
    for e in node.childNodes:
      # print pth 
      # print e.nodeType 

      if e.attributes:
        newpath = pth
        if newpath <> "/":
           newpath = newpath + "/"
        newpath = newpath + e.localName 
        for  key, val in e.attributes.items():
	  if val != None and isinstance(val,unicode) and len(string.strip(val)) > 0 :
            # print "attrib " + newpath + "="  + val
            di[newpath + "!" + key ] = val

      if e.nodeType == e.TEXT_NODE:
        if e.data != None and isinstance(e.data,unicode) and len(string.strip(e.data)) > 0 :
           # print "text " + pth + "="  + e.data
           di[pth] = e.data

      if e.nodeType == e.ELEMENT_NODE:
        # print "element" + e.localName
        if e.hasChildNodes():
          newpath = pth
          if newpath <> "/":
             newpath = newpath + "/"
          mdom_descend(di, e, newpath + e.localName)

def main():
    input = '''<launchRequest>
  <launchData>
    <user a="123">
      <eid>admin@umich.edu</eid>
      <email>admin@umich.edu</email>      <firstName>Sakai</firstName>
      <fullName>Sakai Administrator</fullName>
      <id>admin</id>
      <lastName>Administrator</lastName>
      <locale>en-us</locale>
      <role>Administrator</role>
    </user>
  </launchData>
  <launchDefinition>
    <course>
      <id>bdac3eca-556f-40fc-a1ab-b60afcf08dba</id>
      <title>sacha test</title>
    </course>
    <resourceid>70357733-4be8-4c86-83c1-2ff396098f89</resourceid>
  </launchDefinition>
</launchRequest>
'''
    a = mdom_parse(input)
    print a
    print a.get('/launchRequest/launchData/user/eid', "missing")

if __name__ == '__main__':
  main()


