import web
from tools import license

with open('VERSION', 'r') as f:
	__version__ = f.read()

def code_in():
	callsign = bottle.request.forms.get('callsign')
	bottle.redirect('/code/'+callsign)

def code_no():
	bottle.redirect('/')


#@callpass.route('/code/:callsign#[a-zA-Z0-9]+#')
def code_callsign(callsign):
	call = license(callsign)
	
	if not call.status == 'OK':	return file('./error.html').replace('%s', 'DB: '+call.status)
	if not call.valid:			return file('./error.html').replace('%s', call.reason)
	return file('./code.html').replace('%s', call.hash)


#@callpass.route('/json/:callsign#[a-zA-Z0-9]+#')
def json_callsign(callsign):
	call = license(callsign)
	give = {}
	
	give['callsign']	= call.callsign
	give['status']		= call.status
	if call.status == 'OK':
		give['valid'] = call.valid
		if not call.valid: give['reason'] = call.reason
	return give

class hello:
	def GET(self, name):
		return "Hello", ('' if not name else name)
##
# The workings
#

urls = (
        '/hello/?(.*)',     'hello',
#       '/',                'index.front',
#       '/request/key',     'keys.requested',
#       '/tests/echo',      'tests.echo',
)

app = web.application(urls, globals())
def start(host, port):
	import sys; sys.argv = [sys.argv[0]]
	if host is not None: sys.argv.append(':'.join([host,port]))
	else: sys.argv.append(port)
	app.run()


if __file__ == 'wsgi.py':
	web.config.debug = False
	application = app.wsgifunc()

elif __name__ == '__main__':
	from optparse import OptionParser
	
	parser = OptionParser(usage="usage: %prog [port]|[host:port]",
	                      version="APRS callpass tools "+__version__)
	parser.parse_args()
	app.run()
