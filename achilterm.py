#!/usr/bin/env python

"""
    Achilterm is an AJAX web based terminal, very easy to install and to use.
    Copyright (C) 2013 Florent Gallaire <fgallaire@gmail.com>
    Copyright (C) 2006 Antony Lesuisse (email: al AT udev.org)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import array,cgi,fcntl,glob,mimetypes,optparse,os,pty,random,re,signal,select,sys,threading,time,termios,struct,pwd

import webob
import wsgiref.simple_server
import gzip

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

class Terminal:
	def __init__(self,width=80,height=24):
		self.width=width
		self.height=height
		self.init()
		self.reset()
	def init(self):
		self.esc_seq={
			"\x00": None,
			"\x05": self.esc_da,
			"\x07": None,
			"\x08": self.esc_0x08,
			"\x09": self.esc_0x09,
			"\x0a": self.esc_0x0a,
			"\x0b": self.esc_0x0a,
			"\x0c": self.esc_0x0a,
			"\x0d": self.esc_0x0d,
			"\x0e": None,
			"\x0f": None,
			"\x1b#8": None,
			"\x1b=": None,
			"\x1b>": None,
			"\x1b(0": None,
			"\x1b(A": None,
			"\x1b(B": None,
			"\x1b[c": self.esc_da,
			"\x1b[0c": self.esc_da,
			"\x1b]R": None,
			"\x1b7": self.esc_save,
			"\x1b8": self.esc_restore,
			"\x1bD": None,
			"\x1bE": None,
			"\x1bH": None,
			"\x1bM": self.esc_ri,
			"\x1bN": None,
			"\x1bO": None,
			"\x1bZ": self.esc_da,
			"\x1ba": None,
			"\x1bc": self.reset,
			"\x1bn": None,
			"\x1bo": None,
		}
		for k,v in self.esc_seq.items():
			if v==None:
				self.esc_seq[k]=self.esc_ignore
		# regex
		d={
			r'\[\??([0-9;]*)([@ABCDEFGHJKLMPXacdefghlmnqrstu`])' : self.csi_dispatch,
			r'\]([^\x07]+)\x07' : self.esc_ignore,
		}
		self.esc_re=[]
		for k,v in d.items():
			self.esc_re.append((re.compile('\x1b'+k),v))
		# define csi sequences
		self.csi_seq={
			'@': (self.csi_at,[1]),
			'`': (self.csi_G,[1]),
			'J': (self.csi_J,[0]),
			'K': (self.csi_K,[0]),
		}
		for i in [i[4] for i in dir(self) if i.startswith('csi_') and len(i)==5]:
			if not self.csi_seq.has_key(i):
				self.csi_seq[i]=(getattr(self,'csi_'+i),[1])
	def reset(self,s=""):
		self.scr=array.array('i',[0x000700]*(self.width*self.height))
		self.st=0
		self.sb=self.height-1
		self.cx_bak=self.cx=0
		self.cy_bak=self.cy=0
		self.cl=0
		self.sgr=0x000700
		self.buf=""
		self.outbuf=""
		self.last_html=""
	def peek(self,y1,x1,y2,x2):
		return self.scr[self.width*y1+x1:self.width*y2+x2]
	def poke(self,y,x,s):
		pos=self.width*y+x
		self.scr[pos:pos+len(s)]=s
	def zero(self,y1,x1,y2,x2):
		w=self.width*(y2-y1)+x2-x1+1
		z=array.array('i',[0x000700]*w)
		self.scr[self.width*y1+x1:self.width*y2+x2+1]=z
	def scroll_up(self,y1,y2):
		self.poke(y1,0,self.peek(y1+1,0,y2,self.width))
		self.zero(y2,0,y2,self.width-1)
	def scroll_down(self,y1,y2):
		self.poke(y1+1,0,self.peek(y1,0,y2-1,self.width))
		self.zero(y1,0,y1,self.width-1)
	def scroll_right(self,y,x):
		self.poke(y,x+1,self.peek(y,x,y,self.width))
		self.zero(y,x,y,x)
	def cursor_down(self):
		if self.cy>=self.st and self.cy<=self.sb:
			self.cl=0
			q,r=divmod(self.cy+1,self.sb+1)
			if q:
				self.scroll_up(self.st,self.sb)
				self.cy=self.sb
			else:
				self.cy=r
	def cursor_right(self):
		q,r=divmod(self.cx+1,self.width)
		if q:
			self.cl=1
		else:
			self.cx=r
	def echo(self,c):
		if self.cl:
			self.cursor_down()
			self.cx=0
		self.scr[(self.cy*self.width)+self.cx]=self.sgr|ord(c)
		self.cursor_right()
	def esc_0x08(self,s):
		self.cx=max(0,self.cx-1)
	def esc_0x09(self,s):
		x=self.cx+8
		q,r=divmod(x,8)
		self.cx=(q*8)%self.width
	def esc_0x0a(self,s):
		self.cursor_down()
	def esc_0x0d(self,s):
		self.cl=0
		self.cx=0
	def esc_save(self,s):
		self.cx_bak=self.cx
		self.cy_bak=self.cy
	def esc_restore(self,s):
		self.cx=self.cx_bak
		self.cy=self.cy_bak
		self.cl=0
	def esc_da(self,s):
		self.outbuf="\x1b[?6c"
	def esc_ri(self,s):
		self.cy=max(self.st,self.cy-1)
		if self.cy==self.st:
			self.scroll_down(self.st,self.sb)
	def esc_ignore(self,*s):
		pass
#		print "term:ignore: %s"%repr(s)
	def csi_dispatch(self,seq,mo):
	# CSI sequences
		s=mo.group(1)
		c=mo.group(2)
		f=self.csi_seq.get(c,None)
		if f:
			try:
				l=[min(int(i),1024) for i in s.split(';') if len(i)<4]
			except ValueError:
				l=[]
			if len(l)==0:
				l=f[1]
			f[0](l)
#		else:
#			print 'csi ignore',c,l
	def csi_at(self,l):
		for i in range(l[0]):
			self.scroll_right(self.cy,self.cx)
	def csi_A(self,l):
		self.cy=max(self.st,self.cy-l[0])
	def csi_B(self,l):
		self.cy=min(self.sb,self.cy+l[0])
	def csi_C(self,l):
		self.cx=min(self.width-1,self.cx+l[0])
		self.cl=0
	def csi_D(self,l):
		self.cx=max(0,self.cx-l[0])
		self.cl=0
	def csi_E(self,l):
		self.csi_B(l)
		self.cx=0
		self.cl=0
	def csi_F(self,l):
		self.csi_A(l)
		self.cx=0
		self.cl=0
	def csi_G(self,l):
		self.cx=min(self.width,l[0])-1
	def csi_H(self,l):
		if len(l)<2: l=[1,1]
		self.cx=min(self.width,l[1])-1
		self.cy=min(self.height,l[0])-1
		self.cl=0
	def csi_J(self,l):
		if l[0]==0:
			self.zero(self.cy,self.cx,self.height-1,self.width-1)
		elif l[0]==1:
			self.zero(0,0,self.cy,self.cx)
		elif l[0]==2:
			self.zero(0,0,self.height-1,self.width-1)
	def csi_K(self,l):
		if l[0]==0:
			self.zero(self.cy,self.cx,self.cy,self.width-1)
		elif l[0]==1:
			self.zero(self.cy,0,self.cy,self.cx)
		elif l[0]==2:
			self.zero(self.cy,0,self.cy,self.width-1)
	def csi_L(self,l):
		for i in range(l[0]):
			if self.cy<self.sb:
				self.scroll_down(self.cy,self.sb)
	def csi_M(self,l):
		if self.cy>=self.st and self.cy<=self.sb:
			for i in range(l[0]):
				self.scroll_up(self.cy,self.sb)
	def csi_P(self,l):
		w,cx,cy=self.width,self.cx,self.cy
		end=self.peek(cy,cx,cy,w)
		self.csi_K([0])
		self.poke(cy,cx,end[l[0]:])
	def csi_X(self,l):
		self.zero(self.cy,self.cx,self.cy,self.cx+l[0])
	def csi_a(self,l):
		self.csi_C(l)
	def csi_c(self,l):
		#'\x1b[?0c' 0-8 cursor size
		pass
	def csi_d(self,l):
		self.cy=min(self.height,l[0])-1
	def csi_e(self,l):
		self.csi_B(l)
	def csi_f(self,l):
		self.csi_H(l)
	def csi_h(self,l):
		if l[0]==4:
			pass
#			print "insert on"
	def csi_l(self,l):
		if l[0]==4:
			pass
#			print "insert off"
	def csi_m(self,l):
		for i in l:
			if i==0 or i==39 or i==49 or i==27:
				self.sgr=0x000700
			elif i==1:
				self.sgr=(self.sgr|0x000800)
			elif i==7:
				self.sgr=0x070000
			elif i>=30 and i<=37:
				c=i-30
				self.sgr=(self.sgr&0xff08ff)|(c<<8)
			elif i>=40 and i<=47:
				c=i-40
				self.sgr=(self.sgr&0x00ffff)|(c<<16)
#			else:
#				print "CSI sgr ignore",l,i
#		print 'sgr: %r %x'%(l,self.sgr)
	def csi_r(self,l):
		if len(l)<2: l=[0,self.height]
		self.st=min(self.height-1,l[0]-1)
		self.sb=min(self.height-1,l[1]-1)
		self.sb=max(self.st,self.sb)
	def csi_s(self,l):
		self.esc_save(0)
	def csi_u(self,l):
		self.esc_restore(0)
	def escape(self):
		e=self.buf
		if len(e)>32:
#			print "error %r"%e
			self.buf=""
		elif e in self.esc_seq:
			self.esc_seq[e](e)
			self.buf=""
		else:
			for r,f in self.esc_re:
				mo=r.match(e)
				if mo:
					f(e,mo)
					self.buf=""
					break
#		if self.buf=='': print "ESC %r\n"%e
	def write(self,s):
		s = s.decode('utf-8')
		for i in s:
			if len(self.buf) or (i in self.esc_seq):
				self.buf+=i
				self.escape()
			elif i == '\x1b':
				self.buf+=i
			else:
				self.echo(i)
	def read(self):
		b=self.outbuf
		self.outbuf=""
		return b
	def dumphtml(self,color=1):
		h=self.height
		w=self.width
		r=""
		span=""
		span_bg,span_fg=-1,-1
		for i in range(h*w):
			q,c=divmod(self.scr[i],256)
			if color:
				bg,fg=divmod(q,256)
			else:
				bg,fg=0,7
			if i==self.cy*w+self.cx:
				bg,fg=1,7
			if (bg!=span_bg or fg!=span_fg or i==h*w-1):
				if len(span):
					r+='<span class="f%d b%d">%s</span>'%(span_fg,span_bg,cgi.escape(span.encode('utf8')))
				span=""
				span_bg,span_fg=bg,fg
                        if c == 0:
                                span+=' '
                        elif c > 0x10000:
                                span+='?'
                        else:
                                span+=unichr(c&0xFFFF)
			if i%w==w-1:
				span+='\n'
		r='<?xml version="1.0" encoding="UTF-8"?><pre class="term">%s</pre>'%r
		if self.last_html==r:
			return '<?xml version="1.0"?><idem></idem>'
		else:
			self.last_html=r
#			print self
			return r
	def __repr__(self):
		d=self.scr
		r=""
		for i in range(self.height):
			r+="|%s|\n"%d[self.width*i:self.width*(i+1)]
		return r

class SynchronizedMethod:
	def __init__(self,lock,orig):
		self.lock=lock
		self.orig=orig
	def __call__(self,*l):
		self.lock.acquire()
		r=self.orig(*l)
		self.lock.release()
		return r

class Multiplex:
	def __init__(self,cmd=None):
		#signal.signal(signal.SIGCHLD, signal.SIG_IGN)
		self.cmd=cmd
		self.proc={}
		self.lock=threading.RLock()
		self.thread=threading.Thread(target=self.loop)
		self.alive=1
		# synchronize methods
		for name in ['create','fds','proc_read','proc_write','dump','die','run']:
			orig=getattr(self,name)
			setattr(self,name,SynchronizedMethod(self.lock,orig))
		self.thread.start()
	def create(self,w=80,h=25):
		pid,fd=pty.fork()
		if pid==0:
			try:
				fdl=[int(i) for i in os.listdir('/proc/self/fd')]
			except OSError:
				fdl=range(256)
			for i in [i for i in fdl if i>2]:
				try:
					os.close(i)
				except OSError:
					pass
			if self.cmd:
				cmd=['/bin/sh','-c',self.cmd]
			elif os.getuid()==0:
				cmd=['/bin/login']
			else:
				sys.stdout.write("Login: ")
				login=sys.stdin.readline().strip()
				if re.match('^[0-9A-Za-z-_. ]+$',login):
					cmd=['ssh']
					cmd+=['-oPreferredAuthentications=keyboard-interactive,password']
					cmd+=['-oNoHostAuthenticationForLocalhost=yes']
					cmd+=['-oLogLevel=FATAL']
					cmd+=['-F/dev/null','-l',login,'localhost']
				else:
					os._exit(0)
			env={}
			env["COLUMNS"]=str(w)
			env["LINES"]=str(h)
			env["TERM"]="linux"
			env["PATH"]=os.environ['PATH']
			os.execvpe(cmd[0],cmd,env)
		else:
			fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
			# python bug http://python.org/sf/1112949 on amd64
			fcntl.ioctl(fd, struct.unpack('i',struct.pack('I',termios.TIOCSWINSZ))[0], struct.pack("HHHH",h,w,0,0))
			self.proc[fd]={'pid':pid,'term':Terminal(w,h),'buf':'','time':time.time()}
			return fd
	def die(self):
		self.alive=0
	def run(self):
		return self.alive
	def fds(self):
		return self.proc.keys()
	def proc_kill(self,fd):
		if fd in self.proc:
			self.proc[fd]['time']=0
		t=time.time()
		for i in self.proc.keys():
			t0=self.proc[i]['time']
			if (t-t0)>120:
				try:
					os.close(i)
					os.kill(self.proc[i]['pid'],signal.SIGTERM)
				except (IOError,OSError):
					pass
				del self.proc[i]
	def proc_read(self,fd):
		try:
			t=self.proc[fd]['term']
			t.write(os.read(fd,65536))
			reply=t.read()
			if reply:
				os.write(fd,reply)
			self.proc[fd]['time']=time.time()
		except (KeyError,IOError,OSError):
			self.proc_kill(fd)
	def proc_write(self,fd,s):
		try:
			os.write(fd,s.encode('utf-8'))
		except (IOError,OSError):
			self.proc_kill(fd)
	def dump(self,fd,color=1):
		try:
			return self.proc[fd]['term'].dumphtml(color)
		except KeyError:
			return False
	def loop(self):
		while self.run():
			fds=self.fds()
			i,o,e=select.select(fds, [], [], 1.0)
			for fd in i:
				self.proc_read(fd)
			if len(i):
				time.sleep(0.002)
		for i in self.proc.keys():
			try:
				os.close(i)
				os.kill(self.proc[i]['pid'],signal.SIGTERM)
			except (IOError,OSError):
				pass

class AchilTerm:
	def __init__(self,cmd=None,index_file='achilterm.html'):
		self.files={}
		for i in ['css','html','js']:
			for j in glob.glob('*.%s'%i):
				self.files[j]=file(j).read()
		self.files['index']=file(index_file).read()
		self.mime = mimetypes.types_map.copy()
		self.mime['.html']= 'text/html; charset=UTF-8'
		self.multi = Multiplex(cmd)
		self.session = {}
	def __call__(self, environ, start_response):
		req = webob.Request(environ)
		res = webob.Response()
		if req.environ['PATH_INFO'].endswith('/u'):
			s=req.params.get("s","")
			k=req.params.get("k","")
			c=req.params.get("c","")
			w=int(req.params.get("w", 0))
			h=int(req.params.get("h", 0))
			if s in self.session:
				term=self.session[s]
			else:
				if not (w>2 and w<256 and h>2 and h<100):
					w,h=80,25
				term=self.session[s]=self.multi.create(w,h)
			if k:
				self.multi.proc_write(term,k)
			time.sleep(0.002)
			dump=self.multi.dump(term,c)
			res.content_type = 'text/xml'
			if isinstance(dump,str):
				res.content_encoding = 'gzip'
				zbuf=StringIO.StringIO()
				zfile=gzip.GzipFile(mode='wb', fileobj=zbuf)
				zfile.write(''.join(dump))
				zfile.close()
				zbuf=zbuf.getvalue()
				res.write(zbuf)
			else:
				del self.session[s]
				res.write('<?xml version="1.0"?><idem></idem>')
#			print "sessions %r"%self.session
		else:
			n=os.path.basename(req.environ['PATH_INFO'])
			if n in self.files:
				res.content_type = self.mime.get(os.path.splitext(n)[1].lower(), 'application/octet-stream')
				res.write(self.files[n])
			else:
				res.content_type = 'text/html; charset=UTF-8'
				res.write(self.files['index'])
		return res(environ, start_response)

def main():
	parser = optparse.OptionParser()
	parser.add_option("-p", "--port", dest="port", default="8022", help="Set the TCP port (default: 8022)")
	parser.add_option("-c", "--command", dest="cmd", default=None,help="set the command (default: /bin/login or ssh localhost)")
	parser.add_option("-l", "--log", action="store_true", dest="log",default=0,help="log requests to stderr (default: quiet mode)")
	parser.add_option("-d", "--daemon", action="store_true", dest="daemon", default=0, help="run as daemon in the background")
	parser.add_option("-P", "--pidfile",dest="pidfile",default="/var/run/achilterm.pid",help="set the pidfile (default: /var/run/achilterm.pid)")
	parser.add_option("-i", "--index", dest="index_file", default="achilterm.html",help="default index file (default: achilterm.html)")
	parser.add_option("-u", "--uid", dest="uid", help="Set the daemon's user id")
	(o, a) = parser.parse_args()
	if o.daemon:
		pid=os.fork()
		if pid == 0:
			#os.setsid() ?
			os.setpgrp()
			nullin = file('/dev/null', 'r')
			nullout = file('/dev/null', 'w')
			os.dup2(nullin.fileno(), sys.stdin.fileno())
			os.dup2(nullout.fileno(), sys.stdout.fileno())
			os.dup2(nullout.fileno(), sys.stderr.fileno())
			if os.getuid()==0 and o.uid:
				try:
					os.setuid(int(o.uid))
				except:
					os.setuid(pwd.getpwnam(o.uid).pw_uid)
		else:
			try:
				file(o.pidfile,'w+').write(str(pid)+'\n')
			except:
				pass
			print 'Achilterm at http://localhost:%s/ pid: %d' % (o.port,pid)
			sys.exit(0)
	else:
		print 'Achilterm at http://localhost:%s/' % o.port
	at=AchilTerm(o.cmd,o.index_file)
	try:
		wsgiref.simple_server.make_server('localhost', int(o.port), at).serve_forever()
	except KeyboardInterrupt,e:
		sys.excepthook(*sys.exc_info())
	at.multi.die()

if __name__ == '__main__':
	main()

