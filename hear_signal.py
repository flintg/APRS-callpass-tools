#! /usr/bin/env python

import os
print os.getpid()

import signal

def bobby(signal, frame):
	print 'SIGHUP!'

signal.signal(signal.SIGHUP, bobby)

while(1):
	try:
		pass
	except KeyboardInterrup:
		exit()
