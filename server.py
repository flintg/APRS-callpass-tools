import os
import web
from tools import license

with open('VERSION', 'r') as f:
	__version__ = f.read()

template = web.template.render('templates')


class index:
	
	def GET(self):
		return template.index()

class code:
	
	def POST(self, _):
		
		post = web.input()
		
		# check the callsign for bullshit
		if 'callsign' not in post.keys() \
		or post['callsign'] == 'dicks': 
			raise web.seeother('/#invalid-callsign')
		
		raise web.seeother( "/code/%s" % (post['callsign'],) )
	
	def GET(self, callsign):
		
		call = license(callsign)
		
		if call.status is not "OK" or not call.valid:
			return template.error(call.callsign, call.reason)
		else:
			return template.code(call.callsign, call.code)

class json:
	
	def GET(self, callsign):
		call = license(callsign)
		return call.json


## ### ##

urls = (
        '/',               'index',
	'/code/?(.*)',     'code',
	'/json/?(.*)',     'json',
)

app = web.application(urls, globals())

def start(host, port):
	import sys; sys.argv = [sys.argv[0]]
	if host is not None: sys.argv.append(':'.join([host,port]))
	else: sys.argv.append(port)
	app.run()


## ### ##

if os.path.split(__file__)[-1] == 'wsgi.py':
	web.config.debug = False
	application = app.wsgifunc()

elif __name__ == '__main__':
	from optparse import OptionParser
	
	parser = OptionParser(usage="usage: %prog [port]|[host:port]",
	                      version="APRS callpass tools "+__version__)
	parser.parse_args()
	app.run()
