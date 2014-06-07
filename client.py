#!/usr/bin/python

import vim
#import os
import string
import requests
#import sys # DEBUG
from BeautifulSoup import BeautifulSoup
#import websocket
#from websocket import create_connection

import time
import json

import subprocess as sp
import zmq

#from multiprocessing import Process, Queue
import Queue # FIFO
import difflib

### General Vim operations
def vimClearScreen():
	del(vim.current.buffer[0:len(vim.current.buffer)])

def vimCursorPos():
	window = vim.current.window
	(row,column) = window.cursor 
	return (row,column)

def vimCursorSet(row,col):
	window = vim.current.window
 	window.cursor = (row,col)

### All web page related ShareLaTex stuff
class SharelatexSession:
	def __init__(self):
		self.authenticated = False
		self.httpHandler = requests.Session()
		
	def login(self,email,password):
		if not self.authenticated:
			# ??? It is neccessary to get a certificate from the login page
			certPage = self.httpHandler.get("https://www.sharelatex.com/login")
			certPos = certPage.text.find("_csrf")
			certString = certPage.text[certPos+28:certPos+52]
			# ??? Filling out the login form
			formData = {'email': email, 'password': password, '_csrf':certString,'redir':''}
			redirect  = self.httpHandler.post("https://www.sharelatex.com/login", data=formData)
			if redirect.text == '{"redir":"/project"}':
				self.authenticated = True
				return True
			else:
				return False
		else:
			return False

	# ??? Returns a list of ShareLaTex projects
	def projectList(self): 
		if self.authenticated:
			projectPage = self.httpHandler.get("https://www.sharelatex.com/project")
			# ??? Scraping the page for information
			projectSoup = BeautifulSoup(projectPage.text)
			projectEntries = projectSoup.findAll("div",attrs={'class':'project_entry'})
			
			newList = []

			for entry in projectEntries:
				# ??? Filtering name, id etc. for each individual project
				entryName = entry.find("a",attrs={'class':'projectName'}).getText()
				entryId = entry.get('id')
				entryInfo = entry.findAll("span")
				entryDate = entryInfo[2].getText()
				visibility = entryInfo[4].getText()
				entryOwner = entryInfo[6].getText()
				newList.append({
					'name':entryName,
					'id':entryId,
					'date':entryDate,
					'visibility':visibility,
					'owner':entryOwner})
			
			return newList
	
	# ??? Generate a timstamp with a length of 13 numbers
	def genTimeStamp(self):
		t = time.time()
		t = str(t)
		t = t[:10]+t[11:]
		while len(t) < 13:
		        t += "0"
		return t

	# ??? Returns a object connected to the given project
	def openProject(self,projectId):
		if self.authenticated:	
			# ??? Generating timestamp
			timestamp = self.genTimeStamp()

			# ??? To establish a websocket connection
			# ??? the client must query for a sec url
			self.httpHandler.get("https://www.sharelatex.com/project")
			channelInfo = self.httpHandler.get("https://www.sharelatex.com/socket.io/1/?t="+timestamp)
			wsChannel = channelInfo.text[0:channelInfo.text.find(":")]
			wsUrl = u"wss://www.sharelatex.com/socket.io/1/websocket/"+wsChannel
			return SharelatexProject(wsUrl,projectId)

### Handles everything Vim spesific
class VimSharelatexPlugin:
	def __init__(self):
		self.sharelatex = SharelatexSession()
		self.currentPage = None
		self.project = None
		self.lastUpdate = time.time()
		self.lastBuffer = None

	def showLogin(self):
		# !!! Implement login screen
		pass

	def enterLogin(self):
		email = vim.eval("g:sharelatex_email")
		password = vim.eval("g:sharelatex_password")
		# !!! Grab login values from login window
		self.sharelatex.login(email,password)

	def showProjects(self):
		projectList = self.sharelatex.projectList()
		
		vimClearScreen()
		vim.current.buffer.append(" ShareLaTeX")
		vim.current.buffer.append("________________")
		vim.current.buffer.append(" ")

		# ??? Displaying the project list
		for project in projectList:
			vim.current.buffer.append(" ")
			vim.current.buffer.append("	"
					+project['name']+" - "
					+project['date']+" - "
					#+project['visibility']+" - "
					+project['owner'])
			vim.current.buffer.append("	________")

		self.page = "project"
		self.projects = projectList

		# ??? Changing Vims buttons mappings
		vim.command("nmap <silent> <up> :call Sharelatex_project_up() <enter>")
		vim.command("nmap <silent> <down> :call Sharelatex_project_down() <enter>")
		vim.command("nmap <silent> <enter> :call Sharelatex_project_enter() <enter>")
		vim.command("autocmd VimLeavePre * :call Sharelatex_close()")
		vimCursorSet(6,1)

	def navigateProjects(self,direction):
		if self.page == "project":
			(row,col) = vimCursorPos()	
	
			if direction == "up" and row !=6:
				row -= 3
			elif direction == "down" and row < (len(vim.current.buffer)-3):
				row += 3
			
			vimCursorSet(row,col)
			if direction == "enter":
				self.openProject(self.projects[(row-6)/3]['id'])
				self.page == "In project"

	def charNumber(row,column):
		char_count = 0
		for line in vim.current.buffer[:row]:
			char_count += len(line)+1
		char_count += column
		return char_count
	
	# ??? Seperate bufferlines with \n
	def convToString(self,b):
		if b == None or len(b) == 0:
			return u''
		changeTo = u''
		for lines in b[0:len(b)-1]:
			changeTo += u''+lines +"\n"

		changeTo += u''+b[len(b)-1]
		changeTo.replace("	","\t")

		return changeTo

	def applyString(self,s):
		b = []
		s = s.replace('\t',"	")
		b = s.split('\n')
		vim.current.buffer[0:] = b[0:]

	def charPos(charNumber):
		counter = 0
		row = 0
		for line in vim.current.buffer:
			counter += len(line)
			row += 1
			if charNumber <= counter:
				column = charNumber - (counter - len(line))
				return (row,column)
			# ??? Extra column for every newline
			counter += 1

	def openProject(self,projectId):
		self.project = self.sharelatex.openProject(projectId)
		serverBuffer = self.project.open_root_doc()

		vimClearScreen()

		# ??? Pushing document to vim
		vim.command("syntax on")
		vim.command("set filetype=tex")
		
		self.applyString(serverBuffer)
		
		# ??? Returning normal function to these buttons	
		vim.command("nmap <silent> <up> <up>")
		vim.command("nmap <silent> <down> <down>")
		vim.command("nmap <silent> <enter> <enter>")
		vim.command("set updatetime=500")
		vim.command("autocmd CursorMoved,CursorMovedI * :call Sharelatex_update_pos()")
		vim.command("autocmd CursorHold,CursorHoldI * :call Sharelatex_update_pos()")

		#self.test = 1

	def updateProject(self):
		if None != self.project:
			currentTime = time.time()

			c = self.convToString(vim.current.buffer)
			c = self.project.update(c)
			self.applyString(c)
			#print str(self.test)
			op = self.getOpCodes()
			if len(op) > 0:
				message = self.project.sendOperations(op)
				if message != None:
					self.project.serverBuffer = self.convToString(vim.current.buffer)
			if self.lastUpdate + 0.300 < currentTime:
				(row,column) = vimCursorPos()
				self.project.updateCursor(row-1,column)
				self.lastUpdate = currentTime

	def getOpCodes(self):
		c = vim.current.buffer
		c = self.convToString(c)
		op = self.project.decodeOperations(c)
		return op

# ??? This class provides the interface between
# ??? Vim and the WebSocket FIFO in com.py. The 
# ??? Inter Process Communication works by having
# ??? every transmission return a value. 
class IPC:
	def __init__(self,port):
		self.context = zmq.Context.instance()
		self.sock = self.context.socket(zmq.REQ)
		self.sock.connect('tcp://localhost:8080')
		self.q = Queue.Queue()
		
	def transmitt(self,message="GET"):	
		self.sock.send_string(message)
		try:
			response = self.sock.recv_string()
			if response == "DIED":
				exit()
			#print "SOCKET RECV. "+message
			return response
		except:
			print "SOCKET ERROR"
			exit()

	def send(self,message):
		response = self.transmitt(message)	
		if response != "FIFO EMPTY":
			self.q.put(response)

	def recv(self):
		if self.q.empty():
			response = self.transmitt()
			return response
		else:
			return self.q.get()

	def kill(self):
		self.sock.send_string("KILL")

	def waitfor(self,codeword,try_times=20):
		try_count = 0
		while try_count < try_times:
			response = self.recv()
			if response.find(codeword)>=0:
				return response
			try_count += 1
			time.sleep(0.250)
	
		return -1

	def EmptyInto(self,queue):
		response = "000"
		while response != "FIFO EMPTY":
			response = self.recv()
			if response != "FIFO EMPTY":
				queue.put(response)

class Document:
	def __init__(self,uniqueID):
		self.uniqueID = uniqueID
		self.lastCommit = None
		self.version = None
		self.content = None

class SharelatexProject:
	def __init__(self,url,projectID):
		
		# ??? Defining usefull variables
		self.projectID = projectID
		self.currentDoc = None
		self.rootDoc = None
		self.last_update = 0
		self.counter = 0
		self.command_counter = 0
		self.serverBuffer = None

		# ??? Creating the seperate WebSocket process
		# !!! Must add dynamic path
		cmd = ['/usr/bin/python', '/home/thomas/git/Vim-ShareLaTex-Plugin/fifo.py']
		self.p = sp.Popen(cmd,shell=False)
		if self.p.poll() == None :
			print "ALIVE"
			time.sleep(0.5)	

		# ??? Establishing a communication channel
		self.ipc_session = IPC("8080")

		# ??? Sending url so the process can connect
		self.ipc_session.send(url)

		# ??? On a successful connect, the ShareLaTex server sends 1::
		r = self.ipc_session.waitfor("1::",10)
		if r != "1::":
			print "CLIENT: No valid response from ShareLaTex server"
			self.p.kill()	
			return

		message = json.dumps({"name":"joinProject","args":[{"project_id":projectID}]})
		self.send("cmd",message)
		r = self.ipc_session.waitfor("6:::1+")
		temp = json.loads(r[r.find("+")+1:len(r)])	
		data = temp[1]
		self.rootDoc = data.get(u'rootDoc_id') 

	def send(self,message_type,message_content=None):
		if message_type == "update":
			self.ipc_session.send("5:::"+message_content)
		elif message_type == "cmd":
			self.command_counter += 1
			self.ipc_session.send("5:" + str(self.command_counter) + "+::" + message_content)
		elif message_type == "alive":
			self.ipc_session.send("2::")

	# ??? Opens a document in the project
	def openDoc(self,docID):
		if self.currentDoc != None:
			temp = json.dumps({"name":"leaveDoc","args":[self.currentDoc.uniqueID]})
			self.send("cmd",temp)
		
		self.currentDoc = Document(docID)
			
		temp = json.dumps({"name":"joinDoc","args":[docID]})
		self.send("cmd",temp)
		r = self.ipc_session.waitfor("::")
		
		temp = json.loads(r[r.find("+")+1:len(r)])	
		data = temp[1]
	
		self.serverBuffer = self.toString(data)
		self.currentDoc.version = temp[2]
		
		return self.serverBuffer

	# ??? Opens the root document in the project
	def open_root_doc(self):
		if self.rootDoc != None:
			return self.openDoc(self.rootDoc)

	# ??? Converts a list of strings into a single
	# ??? string where the list entries are seperated
	# ??? by the newline sequence.
	def toString(self,b):
		if b == None or len(b) == 0:
			return u''
		
		s = u''
		for line in b[0:len(b)-1]:
			s += u''+line +"\n"

		s += u''+b[len(b)-1]
		s.replace("	","\t")

		return s
	
	def get_char_number(self,row,column):
		char_count = 0
		for line in vim.current.buffer[:row]:
			char_count += len(line)+1
		char_count += column
		return char_count

	def get_char_pos(self,char_number):
		counter = 0
		row = 0
		for line in vim.current.buffer:
			counter += len(line)
			row += 1
			if char_number <= counter:
				column = char_number - (counter - len(line))
				return (row,column)
			# ??? Extra column for every newline
			counter += 1

	def updateCursor(self,row,column):
		message = json.dumps({
			"name":"clientTracking.updatePosition",
			"args":[{
				"row":row,
				"column":column,
				"doc_id":self.currentDoc.uniqueID
				}]
			})
		self.send("update",message)
	
	def updateClients(self):
		return None

	def sendOperations(self,op):
		if len(op) > 0:
			version = self.currentDoc.version
			if version > self.currentDoc.lastCommit:
				message = json.dumps({
					"name":"applyOtUpdate",
					"args":[
						self.currentDoc.uniqueID,
						{
						"doc":self.currentDoc.uniqueID,
						"op":op,
						"v":version
						}
						]
					})
				self.send("update",message)
				self.currentDoc.lastCommit = version
				return message
			return None

	def decodeOperations(self,b):
		#changeStart = None
		#changeStop = None
		#for i in range(0,len(a)):
		#	if a[i] != b[i]:
		#		changeStart = i
		#		break

		#if changeStart != None:
		#	for i in range(
		a = self.serverBuffer
		s = difflib.SequenceMatcher(None,a,b)
		deletes = 0
		inserts = 0
		p = None
		op = []
		for tag, i1, i2, j1, j2 in s.get_opcodes():
			if i1 == 'Null':
				i1 = 0
			if i2 == 'Null':
				i2 = 0
			if j1 == 'Null':
				j1 = 0
			if j2 == 'Null':
				j2 = 0
			
			if len(a) == 0:
				a = [""]
			if len(b) == 0:
				b = [""]

			if tag != "equal":
				p = i1
				if tag == "insert":
					op.append({'p':p,'i':b[j1:j2]})
				elif tag == "replace":
					op.append({'p':p,'d':a[i1:i2]})
					op.append({'p':p,'i':b[j1:j2]})
				elif tag == "delete":
					op.append({'p':p,'d':a[i1:i2]})
				
		return op

	# ??? Decodes the external updates recieved from
	# ??? the server and applies the changes to the
	# ??? given string.
	def applyOperationsString(self,args,buf):
		args = args[0]

		if u'v' in args:
			v = args[u'v']
			if v >= self.currentDoc.version:
				self.currentDoc.version = v+1

		if not u'op' in args:
			return buf
		op = args[u'op']

		for op in op:
			# ??? Del char and lines
			if u'd' in op:
				p = op[u'p']
				s = op[u'd']
		
				buf = buf[:p] + buf[p+len(s):]
			# ??? Add chars and newlines
			if u'i' in op:
				p = op[u'p']
				s = op[u'i']
			
				buf = buf[:p] + s + buf[p:]
		return buf

	# ??? Packets containing external updates
	# ??? are filtered and handled here
	def update(self,editorBuffer):
		q = Queue.Queue()
		self.ipc_session.EmptyInto(q)
		while not q.empty():
			r = str(q.get())
			if r.find("5:::") == 0:
				data = json.loads(r[r.find("5:::")+4:len(r)])
				action = data[u'name']
				if action == "clientTracking.clientUpdated":
					self.updateClients()
				elif action == "otUpdateApplied":
					args = data[u'args']
					if u'v' in data:
						version = data[u'v']
						if version >= self.currentDoc.version:
							self.currentDoc.version = version+1
					self.serverBuffer = self.applyOperationsString(args,self.serverBuffer)
					editorBuffer = self.applyOperationsString(args,editorBuffer)

		return editorBuffer

	def get_documents():
		# ??? Getting all the documents
		temp = json.dumps({"name":"getRootDocumentsList"})	
		#r = ws_session.send("5:3+::"+temp)
		#r = ws_session.recv()
		#temp = json.loads(r[r.find("+")+1:len(r)])	
		#data = temp[1]


cmd = vim.eval("g:cmd")
if cmd=="start":
	plugin = VimSharelatexPlugin()
	plugin.enterLogin()
	plugin.showProjects()
elif cmd=="up":
	plugin.navigateProjects("up")
elif cmd=="down":
	plugin.navigateProjects("down")
elif cmd=="enter":
	plugin.navigateProjects("enter")
elif cmd=="updatePos":
	plugin.updateProject()
elif cmd=="close":
	plugin.project.ipc_session.kill()
	print "ENDTIME"
	p.kill()
