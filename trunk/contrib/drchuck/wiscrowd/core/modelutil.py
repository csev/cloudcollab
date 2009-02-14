import logging

from google.appengine.ext import db
from google.appengine.ext import webapp

def Model_Load(obj, req, prefix = None):
    '''Loop through the request keys and see if they can be put 
    into the model.   An optional prefix is used to append
    to the request keys.'''
    count = 0
    for key in req.params.keys(): 
      value = req.get(key) 
      thetype = Model_Type(obj, key)
      if ( thetype == "none" and prefix != None ) :
         if ( not key.startswith(prefix) ) : continue
         key = key[len(prefix):]
         thetype = Model_Type(obj, key)

      # logging.info("thetype = "+thetype)
      # Don't do booleans automatically
      if ( thetype == "string" or thetype == "int" ) : 
        # logging.info("setting "+key+" = "+str(value))
        setattr(obj,key,value)
        count = count + 1

    logging.info("MODEL LOAD "+str(obj.__class__)+" loaded "+str(count)+" keys")

def Model_Type(obj, key):
    try:
      attr = str(type(getattr(obj.__class__, key)))
    except :
      return "none"

    if attr.find("ext.db.StringProperty") > 0 : return "string"
    if attr.find("ext.db.ReferenceProperty") > 0 : return "reference"
    if attr.find("ext.db.DateTimeProperty")  > 0: return "datetime"
    if attr.find("ext.db.IntegerProperty")  > 0: return "int"
    if attr.find("ext.db.BooleanProperty")  > 0: return "bool"
    return "none"

def Model_Dump(obj):
    '''Dump the contents of an object and return into a string.'''
    if ( not obj ) : 
       return ""
       ret = ret + " Not populated\n"
       return ret

    ret = "Dumping " + obj.__class__.__name__  + "\n"

    for key in dir(obj.__class__) : 
      # print "Key " + key + "\n"
      typ = Model_Type(obj, key)
      # print "Typ " + typ + "\n"
      if ( typ == "string" or typ == "int" or typ == "bool" ) :
        val = getattr(obj,key)
        if key.find("secret") >= 0 : continue
	if ( not val ) : val = "None"
        ret = ret + "  " + key + "=" + str(val) + "\n";

    return ret

