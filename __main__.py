#!/usr/bin/env python

with open('VERSION', 'r') as f:
	__version__ = f.read()

from optparse import OptionParser

if __name__  == '__main__':
	
	parser = OptionParser(usage="usage: %prog [options]|[callsign]",
	                  version="APRS callpass tools "+__version__)
	
	parser.add_option("-s", "--server",
	                  action="store_true",
	                  dest="run_server",
	                  default=False,
	                  help="This flag will start the http server. (not needed if you set the host)")
	
	parser.add_option("-i", "--host",
	                  action="store",
	                  dest="host",
	                  default=False,
	                  help="This flag will start the http server at the specified address.")
	
	parser.add_option("-p", "--port",
	                  action="store", # optional because action defaults to "store"
	                  dest="port",
	                  default="8000",
	                  help="Specify the port to run on (default 8000)",)
	
	(options, args) = parser.parse_args()
	
	if options.run_server is not False or options.host is not False:
		import server
		server.start(options.host, options.port)
	
	else:
		if len(args) != 1:
			parser.error("wrong number of arguments")
	
		import tools
		call = tools.license( args[0] )
		
		if not call.status == 'OK':
			print 'The database is currently in state:', call.status
		elif not call.valid: print call.reason
		else: print 'Your APRS-IS passcode is', call.hash
