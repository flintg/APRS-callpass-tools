import bottle
from callpass_license import license

# Begin WSGI app
callpass = bottle.app()

def file(filename, replacements=None):
	f = open(filename, 'r');	page = f.read();	f.close()
	if not replacements == None:
		return page % replacements
	return page



@callpass.route('/')
def index():
	return file('./index.html')


@callpass.route('/code',  method='POST')
@callpass.route('/code/', method='POST')
def code_in():
	callsign = bottle.request.forms.get('callsign')
	bottle.redirect('/code/'+callsign)


@callpass.route('/code/:callsign#[a-zA-Z0-9]+#')
def code_callsign(callsign):
	call = license(callsign)
	
	if not call.status == 'OK':
		return file('./error.html', ('Database status: '+call.status))
	if not call.valid:
		return file('./error.html', (call.reason))
	else:
		return file('./code.html', (call.hash))


@callpass.route('/json/:callsign#[a-zA-Z0-9]+#')
def json_callsign(callsign):
	call = license(callsign)
	give = {}
	
	give['callsign']	= call.callsign
	give['status']		= call.status
	if call.status == 'OK':
		give['valid'] = call.valid
		if not call.valid: give['reason'] = call.reason
	return give


# Backups for important static files.
@callpass.route('/static/style.css')
def style():
	bottle.response.content_type = 'text/css; charset=UTF-8'
	return file('./static/style.css')

@callpass.route('/favicon.ico')
def favicon():
	bottle.response.content_type = 'image/x-icon'
	return file('./static/favicon.ico')
