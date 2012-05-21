APRS Callpass generator
=======================

What, why?
----------

This is a tiny thing I decided to build because I got tired of people waiting for other people to give them their APRS code. Some wait times reach weeks long.

This is a much faster solution which aims to remove emails and wait times. Less hassle for humans, less pissoff-ery for the person needing their code.

This does the basic job, and more. It works as a library, a command line tool, and a tiny web server.
You like the sound of that? Good, it's free!


Requirements
------------

Python 2
webpy (optional)


How it works
------------

When given a callsign, it checks for the validity of the callsign (so, US only at the moment) and bothers to generate the code if the call is valid.


TODO
----	

- Find a license data source which is more comprehensive than the FCC. ( Do NOT suggest QRZ )
- The default code.html and error.html files need a bit better text styling.
- Doesn't currently identify cancelled licenses because I don't know if that has a consistent entry in the database


CREDITS
-------

- xastir
	xastir (released under a compatible GPL license) is a cool peice of software.
	Thanks for the callpass hash method. I wouldn't have known where else to find it.

- callook
	callook (callook.info) is a (very) fast, well behaved amateur license database.
	Uses data from the FCC. Many thanks for the great performance!


LICENSE
-------
	
GPLv3
