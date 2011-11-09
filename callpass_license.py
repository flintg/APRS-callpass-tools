import os, sys, time
import urllib

try:	import json
except ImportError:
	try:
		import simplejson as json
	except ImportError:
		raise ImportError('Could not import json or simplejson. Please install one of these options!')


class license:

	def __init__(self, callsign):
		self.callsign = callsign
		
		self.validate()
		self.hash()


	def validate(self):
		
		# Fetch license data.
		api_url = 'http://callook.info/%s/json'
		page = urllib.urlopen( api_url % urllib.quote(self.callsign) ); data = page.read(); page.close()
		data = json.loads(data)
		
		# Something is up server-side. Discontinue.
		if not str(data['status']).upper() == 'VALID' and not str(data['status']).upper() == 'INVALID':
			self.status = data['status']
			return self.status
		else: self.status = 'OK'
		
		# Check validity, exit if false
		if str(data['status']).upper() == 'VALID': self.valid = True
		else: self.valid = False; self.reason = 'The callsign specified does not have a valid license!'; return self.valid
		
		# Check expiry
		# Turn dates into YYYYMMDD - comparable integers
		expdate  = data['otherInfo']['expiryDate'].split('/')
		expdate  = int(expdate[2]+expdate[0]+expdate[1])
		currdate = int(time.strftime('%Y%m%d', time.gmtime(time.time())))
		
		if currdate > expdate: self.valid = False; self.reason = 'The callsign specified does not have a valid license!'
		
		return self.valid


	def hash(self):
		# This method derived from the xastir project under a GPL license.
		
		hash = 0x73e2	# seed value, non-negotiable
		i = 1			# loop switch
		
		for char in self.callsign.upper():
			
			hash = ( hash ^ ord(char)<<8 ) if i else ( hash ^ ord(char) )
			i = False if i else True
			
		self.hash = str( hash & 0x7fff )
		return self.hash
