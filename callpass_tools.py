#!/usr/bin/env python

import os
import urllib
import urlparse
import time
import socket

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from subprocess import Popen, PIPE

try:
	import json
except ImportError:
	try:
		import simplejson as json
	except ImportError:
		raise ImportError('Could not import json or simplejson. Please install one of these options!')

try:
	import daemon
except ImportError:
	raise ImportError('Please install the python "daemon" module! Use `[sudo] easy_install daemon` or `[sudo] pip install daemon` or download it manually: http://pypi.python.org/pypi/daemon')


# This sucks, but some sysadmins like to complain
# that APRS-IS is "hams only" and use server load
# and "community purity" as an excuse. We'll let 
# them choose. Default is to not be exclusionary.
amateurs_only = False


# This check is to determine if the tools for code
# generating are installed. Do this check.
# You either know what you need installed or you don't.
try:
	proc = Popen(['callpass', 'bob'], stdout=PIPE, stderr=PIPE)
	proc.wait()
	if len(proc.stderr.read()) > 1:
		raise EnvironmentError("This system does not have prerequisites for APRS callsign passcode generation installed, or they are not in the user's path!")
	if len(proc.stdout.read()) < 1:
		raise EnvironmentError("The APRS callsign passcode generation tool does not return a passcode!")
except:
	raise EnvironmentError("This system does not have prerequisites for APRS callsign passcode generation installed, or they are not in the user's path!")
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
	license = False
	
	if not str(data['status']).upper() == 'OK':
		errcode = data['Errors']['Err'][0]['code']
		if errcode == 110:
			errmsg = 'Callsign could not be found!'
		else:
			errmsg = data['Errors']['Err'][0]['msg']
		return (False, errmsg)
	
	
	for lic_entry in data['Licenses']['License']:
		if not str(lic_entry['callsign']).upper() == str(callsign).upper():
			continue
		license = lic_entry
		break
	if not license:
		return (False, 'Callsign could not be found!')
	
	if amateurs_only and not str(license['serviceDesc']).lower() == 'amateur':
		return (False, 'This service has been restricted to amateur operators.')
	
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


class web_daemon:
	
	default_port = 8050
	files = {}
	
	pid = str(os.getpid())
	pidfile = "/tmp/callpass_tools.pid"
	
	
	def __init__(self, port=None):
		'''
		Starts the callpass program as an HTTP server, then forks into the background.
		* Providing a port is optional.
		'''
		
		# Introduction
		print
		print 'Starting APRS callpass web interface',
		
		# Clean up the port.
		# Make sure it's valid.
		if not port and not port == 0:
			port = self.default_port
			print 'on port', port
		else:
			# We got passed a port.
			# Make sure it's an integer.
			try:
				port = int(port)
			except ValueError:
				port = self.default_port
				print; print ' ` Given port was not an integer, defaulting to %d!' % (port)
			# It's an integer.
			# Make sure it's not out of range.
			else:
				if port > 65535:
					port = self.default_port
					print
					raise UserWarning('Port out of range!')
					print ' ` Given port was out of range, defaulting to %d!' % (port)
				else:
					print 'on port', port
		
		
		
		# Make sure the bare minimum exists.
		# These are what come by default, anyway.
		required_files = ['index.html', 'code.html', 'error.html', 'style.css']
		bad_files = []
		
		for file in required_files:
			if not os.path.exists( os.path.join(os.curdir, file) ):
				bad_files.append(file)
		if len(bad_files):
			print ' % Required file(s) are missing!'
			for file in bad_files:
				print "\t%s" % file
			return None
		
		
		
		# All of the html, css, and js files will be read into RAM.
		# This could be a nasty discussion, but I figure if you're
		# going to read the file, the kernel is just going to load
		# it into the RAM IO buffers, so lets keep it in memory to
		# avoid using I/O or possibly waiting for disk priority.
		# Besides, these files barely manage half a MB alone.
		
		for file in required_files:
			try:
				f = open(file)
				self.files[file] = f.read()
				f.close()
			except:
				bad_files.append(file)
		if len(bad_files):
			print ' % Error opening required file(s)!'
			for file in bad_files:
				print "\t%s" % file
			return None
		
		print ' ` Please note, if you customize or change the'
		print '   files, you will have to restart this daemon!'
		
		# Fork into the background to become a daemon!
		print
		daemon.daemonize(self.pidfile)
		
		# Probe the port to see if we can bind it.
		# NOTE:
		#	This is a race condition.
		#	Just because it's available right now,
		#	doesn't mean it will be when we bind to
		#	it. The only other option is to find
		#	that out when we bind to it. So we're
		#	not changing the failing behavior, just
		#	trying to avoid it politely.
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			s.bind(('0.0.0.0', port))
			s.close()
		except socket.error:
			print ' ~ Port unavailable! Cannot continue!'
			exit()
		
		
		# start up the server, let it do what it's supposed to :)
		server = HTTPServer(('0.0.0.0', port), self.APRSRequestHandler)
		server.serve_forever()
		
		os.remove(self.pidfile)
		
		

	class APRSRequestHandler(BaseHTTPRequestHandler):
		
		def do_GET(self):
			parsed_path = urlparse.urlparse(self.path)
			message = '\n'.join([
					'CLIENT VALUES:',
					'client_address=%s (%s)' % (self.client_address,
												self.address_string()),
					'command=%s' % self.command,
					'path=%s' % self.path,
					'real path=%s' % parsed_path.path,
					'query=%s' % parsed_path.query,
					'request_version=%s' % self.request_version,
					'',
					'SERVER VALUES:',
					'server_version=%s' % self.server_version,
					'sys_version=%s' % self.sys_version,
					'protocol_version=%s' % self.protocol_version,
					'',
					])
			self.send_response(200)
			self.end_headers()
			self.wfile.write(message)
			return
		
		def do_POST(self):
			parsed_path = urlparse.urlparse(self.path)
			message = '\n'.join([
					'CLIENT VALUES:',
					'client_address=%s (%s)' % (self.client_address,
												self.address_string()),
					'command=%s' % self.command,
					'path=%s' % self.path,
					'real path=%s' % parsed_path.path,
					'query=%s' % parsed_path.query,
					'request_version=%s' % self.request_version,
					'',
					'SERVER VALUES:',
					'server_version=%s' % self.server_version,
					'sys_version=%s' % self.sys_version,
					'protocol_version=%s' % self.protocol_version,
					'',
					]) 
			self.send_response(200)
			self.end_headers()
			self.wfile.write(message)
			return




if __name__ == '__main__':

	import sys

	usage = """\nUsage:
	
	$ python """ + __file__ + """ [-r] <CALLSIGN>
		<callsign> must be an FCC recognized
		callsign! (no dashes or designators)
	
	$ python """ + __file__ + """ [-r] -d [port]
		This will start the callpass web interface!
		* Port is optional. Defaults to """ +str(web_daemon.default_port)+ """.
	
	* An unfortunate inclusion; The -r flag will
	  restrict users of the application and deny
	  any non-amateurs their APRS-IS code.\n"""
	
	
	# Strip the restrict flag
	# Set it's corresponding trigger
	if len(sys.argv) > 1 and '-r' in sys.argv:
		amateurs_only = True
		sys.argv.pop(sys.argv.index('-r'))
	
	
	# If there's nothing there, or it's something to be
	# paranoid about, definitely disregard it and go to start.
	if len(sys.argv) < 2 or not isinstance(sys.argv[1], str):
		print usage
		sys.exit()
	
	
	# If user calls for a daemon, prepare it.
	if sys.argv[1] == '-d':
		# that's probably a port on the end
		# start it in the correct context.
		if len(sys.argv) > 2:	daemon = web_daemon(sys.argv[2])
		else:					daemon = web_daemon()
	
	# No daemon called, for, but they left a present
	# If it's alnum, assume callsign.
	elif sys.argv[1].isalnum():
		
		affirmative, message = get_code(sys.argv[1])
		if not affirmative:
			print 'Error:', message
		else:
			print 'Your APRS-IS code is', message
			
	
	else:
		print usage
