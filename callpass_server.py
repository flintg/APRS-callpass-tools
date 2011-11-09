import bottle
from callpass_license import license

# Begin WSGI app
callpass = bottle.app()


@callpass.route('/')
def index():
	f = open('./index.html', 'r')
	page = f.read()
	f.close()
	return page

@callpass.route('/code',  method='POST')
@callpass.route('/code/', method='POST')
def code_in():
	callsign = bottle.request.forms.get('callsign')
	bottle.redirect('/code/'+callsign)


@callpass.route('/code/:callsign#[a-zA-Z0-9]+#')
def code_callsign(callsign):
	call = license(callsign)
	
	if not call.status == 'OK':
		return call.status
	if not call.valid:
		return call.reason
	else:
		return call.hash


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