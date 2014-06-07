import vim
import string
import difflib

class Diff:
	def __init__(self):
		self.last = vim.current.buffer[:]

	def operations(self,a,b):
		s = difflib.SequenceMatcher(None,a,b)
		deletes = 0
		inserts = 0
		p = None
		op = []
		for tag, i1, i2, j1, j2 in s.get_opcodes():
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
				#print ("%7s a[%d:%d] (%s) b[%d:%d] (%s)" %(tag, i1, i2, a[i1:i2], j1, j2, b[j1:j2]))

	def convToString(self,b):
		changeTo = ""
		for lines in b[0:len(b)-1]:
			changeTo += lines +"\n"
		changeTo += b[len(b)-1][:]
		return changeTo

	def getOpCodes(self):
		b = vim.current.buffer[:]
		a = self.last
		b = self.convToString(b)
		a = self.convToString(a)
		op = self.operations(a,b)
		self.last = vim.current.buffer[:]
		return op

cmd = vim.eval("g:cmd")
if cmd == "start":
	diffy = Diff()
elif cmd == "update":
	diffy.getOpCodes()
