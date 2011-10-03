#!/usr/bin/env python

import os
import urllib
import time
from subprocess import Popen, PIPE
try:
	import json
except ImportError:
	try:
		import simplejson as json
	except ImportError:
		raise ImportError('Could not import json or simplejson. Please install one of these options!')


# Do this check.
proc = Popen(['callpass', 'bob'], stdout=PIPE, stderr=PIPE)
proc.wait()
if len(proc.stderr.read()) > 1:
	raise EnvironmentError("This system does not have prerequisites for APRS callsign passcode generation installed, or they are not in the user's path!")
if len(proc.stdout.read()) < 1:
	raise EnvironmentError("The APRS callsign passcode generation tool does not return a passcode!")
# /check


def validate_callsign(callsign):
	'''
	Checks the FCC database via HTTP API for the given callsign.
	If exists, checks the expiration date.
	
	If valid, returns (True)
	If invalid, returns (False, reason)
	'''
	
	api_url = 'http://data.fcc.gov/api/license-view/basicSearch/getLicenses?format=json&searchValue='
	page = urllib.urlopen( api_url+urllib.quote(callsign) ); data = page.read(); page.close()
	data = json.loads(data)
	
	if not str(data['status']).upper() == 'OK':
		errcode = data['Errors']['Err'][0]['code']
		if errcode == 110:
			errmsg = 'Callsign could not be found!'
		else:
			errmsg = data['Errors']['Err'][0]['msg']
		return (False, errmsg)
	
	else:
	
		license = False
		for lic_entry in data['Licenses']['License']:
			if not str(lic_entry['callsign']).upper() == str(callsign).upper():
				continue
			license = lic_entry
			break
		if not license:
			return (False, 'Callsign could not be found!')
		
		expdate = license['expiredDate'].split('/')
		expdate = int(expdate[2]+expdate[0]+expdate[1])
		currdate = int(time.strftime('%Y%m%d', time.gmtime(time.time())))
		# Dates: YYYYMMDD
		# comparable integers
		if currdate > expdate:
			return (False, 'Your license is expired!')
		
	return (True,)


def get_code(callsign):
	'''
	Validates the callsign then calculates the APRS-IS code.
	
	If successful, will return a tuple of (True, (int)passcode)
	If failure occurs, will return tuple (False, (str)reason)
	'''
	
	result = validate_callsign(callsign)
	if result[0] is not True:
		return result
	
	proc = Popen(['callpass', callsign], stdout=PIPE)
	proc.wait()
	result = proc.stdout.read()
	result = result.rsplit(' ', 1)
	code = int(result[1])
	
	return (True, code)


def start_web_daemon(port=80):
	'''
	Starts the callpass program as an HTTP server, then forks into the background.
	* Providing a port is optional.
	'''
	
	print '[*] Starting APRS code web interface',
	
	try:
		int(port)
	except ValueError:
		port = 8080 # Default port
		print
		print '[i] Given port was not an integer, defaulting to %d!' % (port)
	else:
		print 'on port', port
	
	bad_files = []
	required_files = ['index.html', 'code.html', 'error.html', 'style.css']
	# each of these will become a variable name
	# This could be a nasty discussion, but I figured if you're
	# going to read the file, the kernel is just going to load
	# it into RAM IO buffers, so lets keep it in memory to avoid
	# using more I/O or possibly waiting for disk priority.
	# Besides, these files barely manage half a MB alone.
	
	for file in required_files:
		if not os.path.exists( os.path.join(os.curdir, file) ):
			bad_files.append(file)
	if len(bad_files):
		print '[!] Required HTML file(s) are missing!'
		for file in bad_files:
			print "\t%s" % file
		return False
	
	for file in required_files:
		try:
			f = open(file)
			vars()[file] = f.read()
			f.close()
		except:
			bad_files.append(file)
	if len(bad_files):
		print '[!] Error opening required HTML file(s)!'
		for file in bad_files:
			print "\t%s" % file
		return False
	
	print '[!] Sorry, but there is no daemon yet! (WIP)'
	return
	# Nothing is set up that far yet! :(
	# Plan to use socket.SimpleHTTPServer for this
	
	print '[~] Please note, if you customize or change the'
	print '      files, you will have to restart this daemon!'
	# Actually start the daemon
