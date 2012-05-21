import os, sys, time
import urllib

try: import json
except ImportError:
	try:
		import simplejson as json
	except ImportError:
		raise ImportError('Could not import json or simplejson. Please install one of these options!')


class license:
	
	status = None
	reason = None
	valid  = None
	code   = None
	
	def __init__(self, callsign):
		self.callsign = callsign.upper()
		
		if self.validate():
			self.hash()
		
		self.json = { 'callsign': self.callsign, 'status': self.status }
		if self.status is "OK": self.json['valid'] = self.valid
		if self.reason is not None: self.json['reason'] = self.reason
		if self.valid: self.json['code'] = self.code
	
	def __str__(self):
		return json.dumps(self.json)
	
	def __repr__(self):
		return "license(\"%s\")" % (self.callsign.replace('"','\\"',))
	
	def validate(self):
		
		# Fetch license data.
		api_url = 'http://callook.info/%s/json'
		page = urllib.urlopen( api_url % urllib.quote(self.callsign) );
		data = page.read();
		data = json.loads(data);
		
		# Something is up server-side. Discontinue.
		if str(data['status']).upper() not in ['VALID', 'INVALID']:
			self.status = "Error"
			self.reason = data['status']
			return False
		else: self.status = 'OK'
		
		# Check validity, exit if false
		if str(data['status']).upper() == 'VALID': self.valid = True
		else:
			self.valid = False;
			self.reason = 'No such license!';
			return self.valid
		
		# Check expiry
		# Turn dates into YYYYMMDD - comparable integers
		expdate  = data['otherInfo']['expiryDate'].split('/')
		expdate  = int(expdate[2]+expdate[0]+expdate[1])
		currdate = int(time.strftime('%Y%m%d', time.gmtime(time.time())))
		
		if currdate > expdate: self.valid = False; self.reason = 'License is expired!'
		
		return self.valid


	def hash(self):
		# This method derived from the xastir project under a GPL license.
		
		hash = 0x73e2    # seed value, non-negotiable
		i = 1            # loop switch
		
		for char in self.callsign.upper():
			
			hash = ( hash ^ ord(char)<<8 ) if i else ( hash ^ ord(char) )
			i = False if i else True
			
		self.hash = str( hash & 0x7fff )
		return self.hash
