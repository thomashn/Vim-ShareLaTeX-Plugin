#!/usr/bin/python

import vim
import string
import requests
import sys # DEBUG
#import lxml.html
from BeautifulSoup import BeautifulSoup
import websocket
from websocket import create_connection

import time
import json
#import threading
#import base64
import logging


# These two lines enable debugging at httplib level (requests->urllib3->httplib)
# You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# The only thing missing will be the response.body which is not logged.
import httplib

base_url = "https://www.sharelatex.com/"	

def sharelatex_login():
	global http_session
	http_session = requests.Session()
	# ??? To login, we need a cookie, the first call is used to get this
	response = http_session.get("https://www.sharelatex.com/login")
	pos = response.text.find("_csrf")
	# ??? Finding the given value of _csrf that is sent using post
	value = response.text[pos+28:pos+52]	
	# !!! This is just for a proff of concept
	payload = {'email': 'YOUR_EMAIL', 'password': 'YOUR_PASSWORD', '_csrf':value,'redir':''}
	response  = http_session.post("https://www.sharelatex.com/login", data=payload)

def clear_screen():
	del(vim.current.buffer[0:len(vim.current.buffer)])

def show_projects():
	clear_screen()
	vim.current.buffer.append(" ShareLaTeX")
	vim.current.buffer.append("________________")

	try:
		http_session
	except:
		sharelatex_login()

	
	# ??? Entering the projects page 
	r = http_session.get("https://www.sharelatex.com/project")
	# ??? Scraping the page for information
	soup = BeautifulSoup(r.text)
	projects = soup.findAll("div",attrs={'class':'project_entry'})

	vim.current.buffer.append("")

	# ??? A list holding all the id values of the availiable projects
	global project_list
	project_list = []
	i = 0

	for a in projects:
		project_list.append([])
		# ??? Getting the project name
		vim.current.buffer.append("")
		temp = a.find("a",attrs={'class':'projectName'})
		name = temp.getText()
		temp = a.findAll("span")
		date = temp[2].getText()
		status = temp[4].getText()
		owner = temp[6].getText()
		vim.current.buffer.append("	" + name + " - " + date + " - " + owner)
		# ??? Getting the project id
		project_list[i] = a.get('id')
		# !!! Must store the id values of the individual projects
		vim.current.buffer.append("	________")
		i += 1

	vim.command("nmap <silent> <up> :call Sharelatex_project_up() <enter>")
	vim.command("nmap <silent> <down> :call Sharelatex_project_down() <enter>")
	vim.command("nmap <silent> <enter> :call Sharelatex_project_enter() <enter>")
	w = vim.current.window
	w.cursor = (6,1)

def do_debug():
	httplib.HTTPConnection.debuglevel = 1
	#logging.basicConfig() 
	#logging.getLogger().setLevel(logging.DEBUG)
	#requests_log = logging.getLogger("requests.packages.urllib3")
	#requests_log.setLevel(logging.DEBUG)
	#requests_log.propagate = True

class Project:
	def __init__(self,http_session,project_id):
		# ??? Defining usefull variables
		self.current_doc_id = None
		self.root_doc_id = None
		self.last_update = 0
		self.counter = 0

		# ??? Generating timestamp
		t = str(time.time())
		t = t.replace(".","")
		t = t[1:13]
		# ??? To establish a websocket connection
		# ??? the client must query for a sec url
		r = http_session.get(base_url+"socket.io/1/?t="+t)
		sec_url = r.text[0:r.text.find(":")]
		temp = "wss://www.sharelatex.com/socket.io/1/websocket/"+sec_url
		self.session = create_connection(temp,timeout=20)
		self.command_counter = 0
		r = self.session.recv()
		# ??? On a successful connect, the server sends 1::
		if r == "1::":
			temp = json.dumps({"name":"joinProject","args":[{"project_id":project_id}]})
			self.send("cmd",temp)
			r = self.session.recv()
			temp = json.loads(r[r.find("+")+1:len(r)])	
			data = temp[1]
			self.root_doc_id = data.get(u'rootDoc_id') 


	def send(self,message_type,message_content=None):
		if message_type == "update":
			self.session.send("5:::"+message_content)
		elif message_type == "cmd":
			self.command_counter += 1
			self.session.send("5:" + str(self.command_counter) + "+::" + message_content)
		elif message_type == "alive":
			self.session.send("2::")

	def poll(self):
		try:
			r = self.session.recv_data()
			return r
		except:
			#print "No message"
			return None

	def open_doc(self,doc_id):
		if self.current_doc_id != None:
			temp = json.dumps({"name":"leaveDoc","args":[current_doc_id]})
			self.send("cmd",temp)
			r = self.poll()

		temp = json.dumps({"name":"joinDoc","args":[doc_id]})
		self.send("cmd",temp)

		r = self.session.recv()
		#print doc_id
		temp = json.loads(r[r.find("+")+1:len(r)])	
		data = temp[1]
		clear_screen()

		# ??? Pushing document to vim
		vim.command("syntax on")
		vim.command("set filetype=tex")
		for a in data:
			# !!! MUST HANDLE UTF8
			if len(vim.current.buffer[0])>1:
				vim.current.buffer.append(a)
			else: 
				vim.current.buffer[0] = a
		
		self.current_doc_id = doc_id

		# ??? Returning normal function to these buttons	
		vim.command("nmap <silent> <up> <up>")
		vim.command("nmap <silent> <down> <down>")
		vim.command("nmap <silent> <enter> <enter>")
		vim.command("set updatetime=250")
		vim.command("autocmd CursorMoved,CursorMovedI * :call Sharelatex_update_pos()")
		vim.command("autocmd CursorHold,CursorHoldI * :call Sharelatex_update_pos()")

	def open_root_doc(self):
		if self.root_doc_id != None:
			self.open_doc(self.root_doc_id)

	def update_cursor_pos(self):
		window = vim.current.window
		(row,column) = window.cursor 
		row -= 1
		self.counter += 1
		print self.counter
		if self.last_update + 0.500 < time.time():
			temp = json.dumps({"name":"clientTracking.updatePosition","args":[{"row":row,"column":column,"doc_id":self.current_doc_id}]})
			r = self.send("update",temp)
			#r = self.session.recv()
			#self.update()
			self.last_update = time.time()


	def update(self):
		r = self.poll()
		if r == "2::":
			print "ALIVE"
			self.send("alive")
		elif str(r)[1:4] == "5:::":
			print "SERVER"

	def get_documents():
		# ??? Getting all the documents
		temp = json.dumps({"name":"getRootDocumentsList"})	
		#r = ws_session.send("5:3+::"+temp)
		#r = ws_session.recv()
		#temp = json.loads(r[r.find("+")+1:len(r)])	
		#data = temp[1]
		# !!! Printing results in error
		#print data	

def open_project(id_value):
	global http_session

	global ws_session
	ws_session = Project(http_session,id_value)

	# ??? Getting the root document
	ws_session.open_root_doc()

# ??? This function is used to navigate up and down the project menu
# ??? and to enter the projects loading its project page or whatever.
def navigate_projects(direction):
	global project_list

	w = vim.current.window
	(v,h) = w.cursor
	if direction == "up" and v !=6:
		v -= 3
	elif direction == "down" and v < (len(vim.current.buffer)-3):
		v += 3
	w.cursor = (v,h)

	if direction == "enter":
		open_project(project_list[(v-6)/3])


cmd = vim.eval("g:cmd")
if cmd=="start":
	show_projects()
elif cmd=="up":
	navigate_projects("up")
elif cmd=="down":
	navigate_projects("down")
elif cmd=="enter":
	navigate_projects("enter")
elif cmd=="updatePos":
	ws_session.update_cursor_pos()
