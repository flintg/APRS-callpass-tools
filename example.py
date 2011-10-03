#! /usr/bin/env python

def usage():
		print
		print "Usage:"
		print "\t$ python", __file__, '<CALLSIGN>'
		print "\t\t<callsign> must be an amateur operator"
		print "\t\tcallsign! (no dashes or designators)"
		print
		print "\t$ python", __file__, '-d', '[port]'
		print "\t\tThis will start the callpass web interface!"
		print "\t\t* Port is optional. Defaults to 80."
		print
		return True


if __name__ == '__main__':
	import sys
	
	if len(sys.argv) < 2 or not isinstance(sys.argv[1], str):
		usage()
		sys.exit()
	
	
	if sys.argv[1] == '-d': # start the deamon
		import callpass_tools
		if len(sys.argv) > 2: # it (prob) has a port on the end
			callpass_tools.start_web_daemon(sys.argv[2])
		else:
			callpass_tools.start_web_daemon()
	
	elif sys.argv[1].isalnum():
		import callpass_tools
		stuff = callpass_tools.get_code(sys.argv[1])
		if not stuff[0]:
			print 'An error occurred:', stuff[1]
		else:
			print 'Your APRS-IS code is', stuff[1]
			
	
	else:
		usage()
