#!/usr/bin/env python
	
	# APRS-IS callsign passcode generation web interface library
    # Copyright (C) 2011 "zamabe" zamabe@inderagamono.net
	#
	# This program is free software: you can redistribute it and/or modify
	# it under the terms of the GNU General Public License as published by
	# the Free Software Foundation, either version 3 of the License, or
	# (at your option) any later version.
	#
	# This program is distributed in the hope that it will be useful,
	# but WITHOUT ANY WARRANTY; without even the implied warranty of
	# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	# GNU General Public License for more details.
	#
    # You should have received a copy of the GNU General Public License
    # along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os, time
import urllib, urlparse
import socket, cgi

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn
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
# >> You either know what you need installed or you don't.
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



files = {} # global here so subclasses can access it.
class web_daemon:
	
	default_port = 8050
	port = 0
	files = {}
	required_files = ['index.html', 'code.html', 'error.html', 'style.css']
	
	pid = str(os.getpid())
	pidfile = "/tmp/callpass_tools.pid"
	
	
	def __init__(self, port=None):
		'''
		Starts the callpass program as an HTTP server, then forks into the background.
		* Providing a port is optional.
		'''
		
		# Introduction
		print 'Starting APRS callpass web interface',
		
		# Make sure the port is valid.
		if not port and not port == 0:
			self.port = self.default_port
			print 'on default port', self.port
		elif not self.validate_port(port):
			self.port = self.default_port
			print
			raise UserWarning('Port out of range!')
			print ' ` Given port was illegal, defaulting to %d!' % (self.default_port)
		else:
			print 'on port', port
		
		# Probe the port to see if we can bind it.
		if not self.probe_port(self.port):
			print ' ~ Port unavailable! Cannot continue!'
			return None
		
		# Load the files into memory
		if not self.required_files_check()\
		or not self.load_files():	return None
		else:						print 'Files loaded'
		
		print 'Note: if you customize, change, add or delete files, you'
		print '      will have to restart this daemon or send a SIGHUP! (WIP)'
		
		# Start up the server, let it do what it's supposed to :)
		server = self.APRSCallpassServer(('0.0.0.0', self.port), self.APRSRequestHandler)
		
		# Fork into the background to become a daemon!
		print 'Attempting to fork into background'
		daemon.daemonize(self.pidfile)
		
		# Everything is set
		try:
			server.serve_forever()
		except KeyboardInterrupt:
			# Not likely, but prettier when debugging
			print "\nServer shutdown!"
		
		# Remove pidfile once the server comes down
		try:
			os.remove(self.pidfile)
		except OSError:
			# This only fails if you ^C.
			# Since this is a daemon,
			# it usually gets killed.
			pass
		
		# Ze end
		return None
	
	
	
	def validate_port(self, port):
		# We got passed a port.
		# Make sure it's an integer.
		try:
			port = int(port)
		except ValueError:
			return False
		# It's an integer.
		# Make sure it's not out of range.
		else:
			if port > 65535:
				return False
		
		return True
	
	
	def probe_port(self, port):
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
			# Something is running on that port, make
			# sure it's not an instance of this server
			# daemon check exits for us if it's ours.
			daemon.checkPID(self.pidfile)
			return False
		return True
	
	
	
	def required_files_check(self):
		# Make sure the bare minimum exists.
		# These are what come by default, anyway.
		
		bad_files = []
		
		for file in self.required_files:
			if not os.path.exists( os.path.join(os.curdir, file) ):
				bad_files.append(file)
		
		if len(bad_files):
			print ' % Required file(s) are missing!'
			for file in bad_files:
				print "\t%s" % file
			return False
		
		return True
	
	
	def load_files(self):
		# All of the html, css, and js files will be read into RAM.
		# This could be a nasty discussion, but I figure if you're
		# going to read the file, the kernel is just going to load
		# it into the RAM IO buffers, so lets keep it in memory to
		# avoid using I/O or possibly waiting for disk priority.
		# Besides, these files barely manage half a MB alone.
		
		global files
		files = {} # reset for SIGHUP
		bad_files = []
		file_formats = ['html', 'css', 'js']

		for filename in os.listdir('.'):
			if len(filename.rsplit('.', 1)) < 2 or filename.rsplit('.', 1)[1].lower() not in file_formats:
				continue
			try:
				f = open(filename)
				files[filename] = f.read()
				f.close()
			except:
				bad_files.append(filename)
		
		if len(bad_files):
			print ' % Error opening file(s)!'
			for file in bad_files:
				print "\t%s" % file
			return False
		
		return True
	
	
	class APRSCallpassServer(ThreadingMixIn, HTTPServer):
		pass

	class APRSRequestHandler(BaseHTTPRequestHandler):
		
		global files
		import urllib
		media_types = { 'html': 'text/html', 'css': 'text/css', 'js': 'text/javascript' }
		
		def do_GET(self):
			
			parsed_path = urlparse.urlparse(self.path)
			path = parsed_path.path
			
			if path == '/':	path = '/index.html'
			if path[1:] in ['code.html', 'error.html']\
			or path[1:] not in files:
				self.send_response(301)
				self.send_header('Location', '/')
				self.end_headers()
				return
				
			self.send_response(200)
			self.send_header( 'Content-type', self.media_types[path.rsplit('.', 1)[1]] )
			self.end_headers()
			self.wfile.write(files[path[1:]])
			return
		
		
		def do_POST(self):
			
			parsed_path = urlparse.urlparse(self.path)
			path = parsed_path.path
			
			ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
			if ctype == 'multipart/form-data':
				postvars = cgi.parse_multipart(self.rfile, pdict)
			elif ctype == 'application/x-www-form-urlencoded':
				length = int(self.headers.getheader('content-length'))
				postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
			else:
				postvars = {}
			
			if not path == "/getcode" \
			or 'callsign' not in postvars.keys():
				self.send_response(301)
				self.send_header('Location', '/')
				self.end_headers()
				return
			
			self.send_response(200)
			self.send_header('Content-type', 'text/html')
			self.end_headers()
			
			status, message = get_code(postvars['callsign'][0])
			#self.wfile.write( files['error.html'] )
			
			# Good
			if status:
				self.wfile.write( files['code.html'].replace('%unpopulated%', str(message)) )
			
			# Bad
			else:
				self.wfile.write( files['error.html'].replace('%unpopulated%', message) )
			
			return



if __name__ == '__main__':
	
	import sys
	
	# Assume the user knows nothing.
	# Which is probably true *giggle*
	usage = """\nUsage:\n
	$ python """ + __file__ + """ [-r] <CALLSIGN>
		<callsign> must be an FCC recognized
		callsign! (no dashes or designators)\n
	$ python """ + __file__ + """ [-r] -d [port]
		This will start the callpass web interface!
		* Port is optional. Defaults to """ +str(web_daemon.default_port)+ """.\n
	* An unfortunate inclusion; The -r flag will
	  restrict users of the application and deny
	  any non-amateurs their APRS-IS code.\n"""
	
	
	# Check for restriction, activate it.
	if len(sys.argv) > 1 and '-r' in sys.argv:
		amateurs_only = True
		sys.argv.pop(sys.argv.index('-r'))
		try:
			from termcolor import colored
		except ImportError:
			def colored(text, color): return text
		print "\n", colored('*** WARNING:', 'red'), "Amateur operators (only) restriction enabled.", "\n"
	
	
	# User provided no arguments or invalid arguments.
	if len(sys.argv) < 2 or not isinstance(sys.argv[1], str):
		print usage
		sys.exit()
	
	
	# If user calls for a daemon, prepare it.
	if sys.argv[1] == '-d':
		# An argument after the flag is assumed to be a port.
		if len(sys.argv) > 2:	daemon = web_daemon(sys.argv[2])
		else:					daemon = web_daemon()
	
	# If the argument is alnum, assume callsign.
	elif sys.argv[1].isalnum():
		
		affirmative, message = get_code(sys.argv[1])
		if not affirmative:
			print 'Error:', message
		else:
			print 'Your APRS-IS code is', message
	
	# They did something wrong.
	# [Redundant] Education time!
	else:
		print usage
