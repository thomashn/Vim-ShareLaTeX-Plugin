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

	# ??? Returns a list of ShareLaTex projects
	def projectList(self): 
		if self.authenticated:
			projectPage = self.httpHandler.get("https://www.sharelatex.com/project")
			# ??? Scraping the page for information
			projectSoup = BeautifulSoup(projectPage.text)
			projectEntries = projectSoup.findAll("div",attrs={'class':'project_entry'})
			
			newList = []

			for entry in projectEntries:
				# ??? Getting the project name
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
			channelInfo = self.httpHandler.get("https://www.sharelatex.com/socket.io/1/?t="+timestamp)
			wsChannel = channelInfo.text[0:channelInfo.text.find(":")]
			wsUrl = "wss://www.sharelatex.com/socket.io/1/websocket/"+wsChannel
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
		if b == None:
			return ""
		changeTo = ""
		for lines in b[0:len(b)-1]:
			if lines[len(lines)-1] == " ":
				lines = lines[len(lines)-2]
			changeTo += lines +"\n"
		changeTo += b[len(b)-1][:]
		return changeTo

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
		self.project.open_root_doc()
		self.lastBuffer = vim.current.buffer[:]
		self.test = ""

	def updateProject(self):
		if None != self.project:
			print self.test
			currentTime = time.time()
			op = self.getOpCodes()
			if len(op) > 0:
				message = self.project.sendOperations(op)
				if message != None:
					self.project.serverBuffer = vim.current.buffer[:]
				#self.project.serverBuffer = vim.current.buffer

			if self.lastUpdate + 0.250 < currentTime:
				self.project.update()
				(row,column) = vimCursorPos()
				self.project.updateCursor(row-1,column)
				self.lastUpdate = currentTime
			#self.lastBuffer = vim.current.buffer[:]

	def getOpCodes(self):
		b = vim.current.buffer
		a = self.project.serverBuffer
		b = self.convToString(b)
		a = self.convToString(a)
		op = self.project.decodeOperations(a,b)
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
			#print "SOCKET RECV. "+message
			return response
		except:
			print "SOCKET ERROR"

	def send(self,message):
		response = self.transmitt(message)	
		if response != "FIFO EMPTY":
			self.q.put(response)

	def recv(self):
		if self.q.empty():
			response = self.transmitt()
			return response
		else:
			return str(self.q.get())

	def kill(self):
		self.sock.send_string("KILL")

	def waitfor(self,codeword,try_times=20):
		try_count = 0
		while try_count < try_times:
			response = self.recv()
			if str(response).find(codeword)>=0:
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
		#if self.p.poll() == None :
		#	print "ALIVE"
		#	time.sleep(0.5)	

		# ??? Establishing a communication channel
		self.ipc_session = IPC("8080")

		# ??? Sending url so the process can connect
		self.ipc_session.send(url)

		# ??? On a successful connect, the ShareLaTex server sends 1::
		r = self.ipc_session.waitfor("1::",6)
		if r != "1::":
			print "CLIENT: No valid response from ShareLaTex server"
			#self.p.kill()	
			return

		message = json.dumps({"name":"joinProject","args":[{"project_id":projectID}]})
		self.send("cmd",message)
		r = str(self.ipc_session.waitfor("6:::1+"))
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
	
	def openDoc(self,docID):
		if self.currentDoc != None:
			temp = json.dumps({"name":"leaveDoc","args":[self.currentDoc.uniqueID]})
			self.send("cmd",temp)
		
		self.currentDoc = Document(docID)
			
		temp = json.dumps({"name":"joinDoc","args":[docID]})
		self.send("cmd",temp)
		r = str(self.ipc_session.waitfor("::"))
		
		temp = json.loads(r[r.find("+")+1:len(r)])	
		data = temp[1]

		self.serverBuffer = data[:]
		self.currentDoc.version = temp[2]

		vimClearScreen()

		# ??? Pushing document to vim
		vim.command("syntax on")
		vim.command("set filetype=tex")
		for a in self.serverBuffer:
			# !!! MUST HANDLE UTF8
			if len(vim.current.buffer[0])>1:
				vim.current.buffer.append(str(a))
			else: 
				vim.current.buffer[0] = str(a)


		# ??? Returning normal function to these buttons	
		vim.command("nmap <silent> <up> <up>")
		vim.command("nmap <silent> <down> <down>")
		vim.command("nmap <silent> <enter> <enter>")
		vim.command("set updatetime=500")
		vim.command("autocmd CursorMoved,CursorMovedI * :call Sharelatex_update_pos()")
		vim.command("autocmd CursorHold,CursorHoldI * :call Sharelatex_update_pos()")

	def open_root_doc(self):
		if self.rootDoc != None:
			self.openDoc(self.rootDoc)

	
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

	def decodeOperations(self,a,b):
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

			if tag != "equal":
				p = i1
				if p == 'Null':
					p = 0
				if tag == "insert":
					op.append({'p':p,'i':b[j1:j2]})
				elif tag == "replace":
					op.append({'p':p,'d':a[i1:i2]})
					op.append({'p':p,'i':b[j1:j2]})
				elif tag == "delete":
					op.append({'p':p,'d':a[i1:i2]})
		
				
		return op

	def applyOperations(self,args,buf):
		args = args[0]

		if u'v' in args:
			v = args[u'v']
			if v >= self.currentDoc.version:
				self.currentDoc.version = v+1
				#self.serverBuffer = vim.current.buffer[:]

		if not u'op' in args:
			return buf
		op = args[u'op']

		for op in op:
			# ??? Del char and lines
			if u'd' in op:
				p = op[u'p']
				s = op[u'd']
				(row,col) = self.get_char_pos(p)
				row -= 1
		
				beforeDelete = buf[row][:col]
				delText = s.split('\n')
				length = len(delText)
				if length > 1:	
					deleteTo = len(delText[length-1])
					afterDelete = buf[row+length-1][deleteTo:]
					for index in range(1,length):
						buf[row:] = buf[row+1:]
				else:
					afterDelete = ""
		
				if s.find("\n") >= 0:
					#buf[row:] = buf[row+1:]
					buf[row] = beforeDelete + afterDelete
				else:
					buf[row] = buf[row][:col] + buf[row][col+len(s):]

			# ??? Add chars and newlines
			if u'i' in op:
				p = op[u'p']
				s = op[u'i']
				(row,col) = self.get_char_pos(p)
				row -= 1
				
				beforeInsert = buf[row][:col]
				afterInsert = buf[row][col:]

				# ??? Tabbing
				if s.find("\t") >= 0:
					s = s.replace("\t","	")
		
				if s.find("\n") >= 0:
					newText = s.split('\n')
					insertBuffer = []
					insertBuffer.append(beforeInsert + newText[0])
					
					for index in range(1,len(newText)-1):
						insertBuffer.append(newText[index])
					
					insertBuffer.append(newText[len(newText)-1]+afterInsert)
					buf[row:] = insertBuffer[:] + buf[row+1:]
				else:
					buf[row] = beforeInsert + s + afterInsert

		return buf

	# ??? Packets containing external updates
	# ??? are filtered and handled here
	def update(self):
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
							#self.serverBuffer = vim.current.buffer[:]
					self.serverBuffer = self.applyOperations(args,self.serverBuffer)
					vim.current.buffer[:] = self.applyOperations(args,vim.current.buffer[:])

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
	#p.kill()
