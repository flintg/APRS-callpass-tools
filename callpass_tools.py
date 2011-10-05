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
import signal

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
	
	# Fetch data from the FCC. Subject to change.
	api_url = 'http://data.fcc.gov/api/license-view/basicSearch/getLicenses?format=json&searchValue='
	page = urllib.urlopen( api_url+urllib.quote(callsign) ); data = page.read(); page.close()
	data = json.loads(data)
	license = False
	
	# Something isn't okay. Just relay that.
	if not str(data['status']).upper() == 'OK':
		return { 'status': False, 'reason': '[FCC] '+ data['Errors']['Err'][0]['msg'] }
	
	# Search through them for the license we're looking for.
	for lic_entry in data['Licenses']['License']:
		# A match! Get out of the loop, record the license.
		if str(lic_entry['callsign']).upper() == str(callsign).upper():
			license = lic_entry
			break
	
	# If we didn't find it, that's all.
	if not license:
		return { 'status': False, 'reason': 'Callsign could not be found!' }
	
	# :( If amateurs_only restriction is set, check out the license.
	if amateurs_only and not str(license['serviceDesc']).lower() == 'amateur':
		return { 'status': False, 'reason': 'This service has been restricted to amateur operators.' }
	
	# Turn dates into YYYYMMDD - comparable integers
	expdate  = license['expiredDate'].split('/')
	expdate  = int(expdate[2]+expdate[0]+expdate[1])
	currdate = int(time.strftime('%Y%m%d', time.gmtime(time.time())))
	
	if currdate > expdate:
		return { 'status': False, 'reason': 'Your license is expired!' }
	
	return { 'status': True }


def get_code(callsign):
	
	# Validation returns likewise failure reasons
	result = validate_callsign(callsign)
	if not result['status']: return result
	
	# Call the external program, wait for it to complete, return findings.
	proc = Popen(['callpass', callsign], stdout=PIPE); proc.wait()
	result = proc.stdout.read()
	result = result.rsplit(' ', 1)
	code = int(result[1])
	
	return { 'status': True, 'callpass': code }



class web_daemon:
	
	default_ip = '0.0.0.0'
	default_port = 8050
	
	ip = '0.0.0.0'
	port = 0
	
	pid = str(os.getpid())
	pidfile = "/tmp/callpass_tools.pid"
	
	
	def __init__(self, ip=default_ip, port=default_port):
		
		# Check the IP
		if self.validate_ip(ip):	self.ip = ip
		else: self.ip = self.default_ip; print '*** WARNING: Given IP was illegal. Defaulting to', self.ip
		
		# Check the ports
		if self.validate_port(port): self.port = port
		else: self.port = self.default_port; print '*** WARNING: Given port was illegal, defaulting to', self.port
		
		# Tell them where the server should spawn
		print 'Starting APRS callpass web interface on', ( str(self.ip) +':'+ str(self.port) )
		
		# Test bind
		if not self.probe_bind(self.ip, self.port):
			print '*** ERROR: Could not bind to IP and port! Cannot continue!'
			return None
		
		# Start the server, daemonize, then activate its server loop
		# The KeyboardInterrup exception just looks better when debugging
		print 'Forking server into background'
		server = self.APRSCallpassServer((self.ip, self.port), self.APRSRequestHandler)
		# daemon.daemonize(self.pidfile) # debug
		try:	server.serve_forever()
		except KeyboardInterrupt:	print "\nServer shutdown!"
		
		# Remove pidfile once the server comes down
		try:			os.remove(self.pidfile)
		except OSError:	pass
		return None
	
	
	def __del__(self):
		# Redundancy
		
		# Remove pidfile once the server comes down
		try:			os.remove(self.pidfile)
		except OSError:	pass
		return None
	
	
	def validate_ip(self, ip):
		
		# Make sure it's a string.
		try:				ip = str(ip)
		except ValueError:	return False
		
		# Does it have four octets
		ip = ip.split('.')
		if not len( ip ) == 4: return False
		
		# Are the octets within range
		for octet in ip:
			try:
				if int(octet) > 255 or int(octet) < 0:
					return False
			except ValueError:	return False
		
		# Nothing to complain about
		return True
	
	
	def validate_port(self, port):
		
		# Make sure it's an integer.
		try:				port = int(port)
		except ValueError:	return False
		
		# Make sure it's not out of range.
		if port > 65535:	return False
		return True
	
	
	def probe_bind(self, ip, port):
		
		# Probe the port to see if we can bind it.
		# 
		# NOTE:
		#	Reliance on this creates a race condition.
		#	Just because it's available right now,
		#	doesn't mean it will be when we bind.
		
		try:
				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				s.bind((ip, port))
				s.close()
				return True
		
		except socket.error:
				# Couldn't bind, the port is inhabited
				# daemon check exits for us if it's ours.
				daemon.checkPID(self.pidfile)
		
		return False
	
	
	
	class APRSCallpassServer(ThreadingMixIn, HTTPServer):
		# Yep. Literally the only reason for this to exist
		# is that it's a threaded HTTPServer. More stable.
		pass

	class APRSRequestHandler(BaseHTTPRequestHandler):
		
		import urllib
		
		# A list of media to allow the server to serve, and their content-type
		media_types = { 'html': 'text/html', 'css': 'text/css', 'js': 'text/javascript' }
		
		# Required files (duh). These come with the server by default.
		required_files = ( 'index.html', 'code.html', 'error.html', 'style.css' )
		
		
		def files(self, file_to_get=None):
		# If this returns false, a (bad) response has been sent.
			
			# Acceptable files to serve.
			file_formats = ['html', 'css', 'js']
			
			# The file list
			files = []
			
			
			# Required files are always required
			for file in self.required_files:
				if not os.path.exists( os.path.join(os.curdir, file) ):
					
					# A request is open, send HTTP 500 and return False.
					self.send_response(500)
					self.end_headers()
					return False
			
			# Build a file list.
			for fn in os.listdir('.'):
				if len(fn.rsplit('.', 1)) > 1 and fn.rsplit('.', 1)[1].lower() in file_formats:
					files.append(fn)
			
			if file_to_get not in files:
				
				self.send_response(404)
				self.send_header('Location', '/')
				self.end_headers()
				return False
			
			# Else, return the contents of the file.
			try:
				f = open(file_to_get)
				fdata = f.read()
				f.close()
			
			except:
				self.send_response(503)
				self.end_headers()
				return False
			
			return fdata
		
		
		def do_GET(self):
			
			parsed_path = urlparse.urlparse(self.path)
			path = parsed_path.path[1:]
			if not len(path):	path = 'index.html'
			
			
			# The quick JSON version of this server.
			if len(path) > 8 and str(path[:8]).lower() == 'getcode/':
				
				print path, '-', path[8:]
				self.send_response(200)
				self.send_header('Content-type', 'text/json')
				self.end_headers()
				
				r = get_code(path[8:])
				
				self.wfile.write( json.dumps( s ) )
				return
			
			#  Don't serve the usecase files directly
			#  Send them to the front of the server.
			if path in ['code.html', 'error.html']:
				
				self.send_response(410)
				self.send_header('Location', '/')
				self.end_headers()
			
			# They're here for something that exists publicly.
			else:
				
				file = self.files(path)
				if file is not False:
					
					self.send_response(200)
					self.send_header( 'Content-type', self.media_types[path.rsplit('.', 1)[1]] )
					self.end_headers()
					self.wfile.write( file )
			
			return
		
		
		def do_POST(self):
			
			parsed_path = urlparse.urlparse(self.path)
			path = parsed_path.path[1:]
			
			# Let the cgi module give us the pretty POST data
			ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
			if ctype == 'multipart/form-data':
				postvars = cgi.parse_multipart(self.rfile, pdict)
			elif ctype == 'application/x-www-form-urlencoded':
				length = int(self.headers.getheader('content-length'))
				postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
			else:	postvars = {}
			
			
			# Separating features by URL.
			if path in ['', 'getcode']:
				
				if 'callsign' in postvars.keys():
					
					self.send_response(200)
					self.send_header('Content-type', 'text/html')
					self.end_headers()
					
					result = get_code(postvars['callsign'][0])
					
					post_file = self.files( 'code.html' if result['status'] else 'error.html' )
					if not post_file == False:
						self.wfile.write( post_file.replace('%unpopulated%', result['callpass'] if result['status'] else result['reason'] ) )
				
				# Their POST request was incorrect.
				# Send them away to the front of the server.
				else:
					
					self.send_response(400)
					self.send_header('Location', '/')
					self.end_headers()
			
			# Nothing covers that URL path.
			else:
				
				self.send_response(301)
				self.send_header('Location', '/')
				self.end_headers()
			
			return



if __name__ == '__main__':
	
	import sys
	
	usage = "\nUsage:\n\n\t$ python "+__file__+" [-r] <CALLSIGN>\n\t\t<callsign> must be an FCC recognized\n\t\tcallsign! (no dashes or designators)\n\n\t$ python "+__file__+" [-r] -d [port] [ip]\n\t\tThis will start the callpass web interface!\n\t\t* Port and IP are optional.\n\t\t  Defaults to "+str(web_daemon.default_ip)+':'+str(web_daemon.default_port)+"\n\n\t * An unfortunate inclusion; The -r flag will\n\t   restrict users of the application and deny\n\t   any non-amateurs their APRS-IS code.\n"
	
	
	# Check for restriction flag, activate it.
	if len(sys.argv) > 1 and '-r' in sys.argv:
		
		print "*** WARNING: Amateur operators only - restriction enabled."
		
		# This is an optional flag, we don't expect it so remove it
		sys.argv.pop(sys.argv.index('-r'))
		amateurs_only = True
	
	
	# Catch daemon flag, start the daemon.
	if len(sys.argv) > 1 and sys.argv[1] == '-d':
		
		# Provide the default values if none specified
		port = web_daemon.default_port
		ip   = web_daemon.default_ip
		
		# An argument after the flag is assumed to be a port.
		# An argument after the port is assumed to be an IP.
		if len(sys.argv) > 2:	port = sys.argv[2]
		if len(sys.argv) > 3:	ip   = sys.argv[3]
		
		# Start the daemon
		daemon = web_daemon(ip=ip, port=port)
	
	
	# If the argument is alnum, assume callsign.
	elif len(sys.argv) > 1 and sys.argv[1].isalnum():
		
		result = get_code(sys.argv[1])
		if not result['status']:	print 'Error:', result['reason']
		else:						print 'Your APRS-IS callpass is', result['callpass']
	
	
	# They did something wrong.
	# Education time!
	else: 	print usage
