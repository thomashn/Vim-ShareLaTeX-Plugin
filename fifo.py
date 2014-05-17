#!/usr/bin/python

# ??? Purpose of this code is to provide vim with
# ??? some kind of FIFO buffer between it and the
# ??? ShareLaTex server communicating using
# ??? WebSocket.

import websocket
import time
#import socket
import threading
import zmq
import sys
import Queue # FIFO

q = Queue.Queue()

lock = threading.Lock()
SHUTDOWN = False

# ??? Functions used by the websocket thing
def on_message(ws, message):
	global q
	#print "WS RECV: "+message
	q.put(message)

def on_error(ws, error):
	global q
	q.put("WS_ERROR")

def on_close(ws):
	global q
	q.put("### closed ###")

class WSPOLL(threading.Thread):
	def run(self):
		global q
		global ws
		global SHUTDOWN
		while 1 :
			try:
				message = ws.recv().decode('utf-8')
				if SHUTDOWN:
					exit()
				if message == "2::":
					ws.send(message)
				q.put(message)
			except:
				#print "WSPOLL: ERROR"
				SHUTDOWN = True
				exit()

class IPC(threading.Thread):
	def run(self):
		global q
		global sock
		global SHUTDOWN
		while 1:
			message = sock.recv_string()
			if SHUTDOWN:
				sock.send("DIED")
				exit()
			#print "SOCK RECV: "+message
			if message == "KILL":
				SHUTDOWN = True
				exit()
			if message != "GET":
				#print "WS SEND:"+message
				ws.send(message)
			if not q.empty():
				response = q.get()
			else:
				response = "FIFO EMPTY"
			#print "SOCK RESP: "+response+"\n"
			sock.send_string(response)


# ??? Globale concurrency counter
counter = 0

# ??? Setting up IPC to vim
context = zmq.Context.instance()
sock = context.socket(zmq.REP)
sock.bind('tcp://*:8080')

wait_for_address = True

if __name__ == "__main__":

	# ??? Wait for an adress that the process can
	# ??? connect to. This will be given by the vim
	# ??? process.
	while wait_for_address:
		ipc_message = sock.recv_string()
		if ipc_message.find('wss://') >= 0:
			#print "SUCCESS"
			wait_for_address = False
			ws_url = ipc_message
			response = "trying to connect"
		else:
			#print "ERROR"
			response = "waiting for command"
		sock.send_string(response)

	# ??? Connecting to a websocket session
	#websocket.enableTrace(True)
	ws = websocket.create_connection(ws_url)
	ws_recv = WSPOLL()
	ws_recv.start()
	
	#ws = websocket.WebSocketApp(ws_url, on_message = on_message, on_error = on_error,on_close = on_close)
	#ws.on_open = on_open
	ipc = IPC()
	#ws.run_forever()
	ipc.start()
	#threading.Thread(target=ws.run_forever(),args=())

		#message = sock.recv_string()
		#if message != "GET":
		#	ws.send(message)
		#if not q.empty():
		#	response = q.get()
		#else:
		#	response = "FIFO EMPTY"
		#print "RESP: "+response+"\n"
		#sock.send_string(response)
