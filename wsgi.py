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

	
# Bring in the server
# Be immediately prepared for WSGI
import bottle
from callpass_server import *
application = callpass


from sys import argv
server_triggers = ['-s', '--server']
if len( set(server_triggers) & set(argv) ):
		
		argv = [arg for arg in argv if arg not in server_triggers] 	# Erase signs of server triggers

		ip   = argv[1] if len(argv) > 1 else '0.0.0.0' # Default
		port = argv[2] if len(argv) > 2 else 8040      # Default
		  
		bottle.run(callpass, host=ip, port=port)




# The interactive prompt
elif len(argv) > 1 and str(argv[1]).isalnum():
	
	import callpass_license
	call = license( argv[1] )
	
	if not call.status == 'OK':
		print 'The database is currently in state:', call.status
	elif not call.valid: print call.reason
	else: print 'Your APRS-IS passcode is', call.hash



# End of the line, give them the howto
else: print """
	Usage:

	$ python """+__file__+""" AB3DEF
		Callsign must be an FCC recognized
		callsign! (no dashes or designators)
		
	$ python """+__file__+""" -s [ip] [port]
	$ python """+__file__+""" --server [ip] [port]
		This will start the callpass web interface!
		* Port and IP are optional.
		Defaults to 0.0.0.0:8040\n"""