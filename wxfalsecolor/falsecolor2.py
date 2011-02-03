#!/usr/bin/env python

import os
import sys
import tempfile
import time
import shlex
import shutil
import math
import traceback
import logging
from subprocess import Popen, PIPE

VERSION="0.3"

TEMPLATE_PC0 = """
PI : 3.14159265358979323846 ;
scale : %u ;
mult : %f ;
ndivs : %u ;
delta : %f ;

or(a,b) : if(a,a,b);
EPS : 1e-7;
neq(a,b) : if(a-b-EPS,1,b-a-EPS);
btwn(a,x,b) : if(a-x,-1,b-x);
clip(x) : if(x-1,1,if(x,x,0));
frac(x) : x - floor(x);
boundary(a,b) : neq(floor(ndivs*a+delta),floor(ndivs*b+delta));

stepv(x) : floor(x*ndivs)/ndivs;

old_red(x) = 1.6*x - .6;
old_grn(x) = if(x-.375, 1.6-1.6*x, 8/3*x);
old_blu(x) = 1 - 8/3*x;

interp_arr2(i,x,f):(i+1-x)*f(i)+(x-i)*f(i+1);
interp_arr(x,f):if(x-1,if(f(0)-x,interp_arr2(floor(x),x,f),f(f(0))),f(1));
def_redp(i):select(i,0.18848,0.05468174,
0.00103547,8.311144e-08,7.449763e-06,0.0004390987,0.001367254,
0.003076,0.01376382,0.06170773,0.1739422,0.2881156,0.3299725,
0.3552663,0.372552,0.3921184,0.4363976,0.6102754,0.7757267,
0.9087369,1,1,0.9863);
def_red(x):interp_arr(x/0.0454545+1,def_redp);
def_grnp(i):select(i,0.0009766,2.35501e-05,
0.0008966244,0.0264977,0.1256843,0.2865799,0.4247083,0.4739468,
0.4402732,0.3671876,0.2629843,0.1725325,0.1206819,0.07316644,
0.03761026,0.01612362,0.004773749,6.830967e-06,0.00803605,
0.1008085,0.3106831,0.6447838,0.9707);
def_grn(x):interp_arr(x/0.0454545+1,def_grnp);
def_blup(i):select(i,0.2666,0.3638662,0.4770437,
0.5131397,0.5363797,0.5193677,0.4085123,0.1702815,0.05314236,
0.05194055,0.08564082,0.09881395,0.08324373,0.06072902,
0.0391076,0.02315354,0.01284458,0.005184709,0.001691774,
2.432735e-05,1.212949e-05,0.006659406,0.02539);
def_blu(x):interp_arr(x/0.0454545+1,def_blup);

isconta = if(btwn(0,v,1),or(boundary(vleft,vright),boundary(vabove,vbelow)),-1);
iscontb = if(btwn(0,v,1),btwn(.4,frac(ndivs*v),.6),-1);

ra = 0;
ga = 0;
ba = 0;

in = 1;

ro = if(in,clip(%s),ra);
go = if(in,clip(%s),ga);
bo = if(in,clip(%s),ba);

vin(x) = x;

""" 

TEMPLATE_PC1 = """
norm : mult/scale/le(1);

v = map(li(1)*norm);

vleft = map(li(1,-1,0)*norm);
vright = map(li(1,1,0)*norm);
vabove = map(li(1,0,1)*norm);
vbelow = map(li(1,0,-1)*norm);

map(x) = x;

ra = ri(nfiles);
ga = gi(nfiles);
ba = bi(nfiles);

"""


class NullHandler(logging.Handler):
    """handler to swallow all logging messages"""
    def emit(self, record):
        pass



class FalsecolorBase:
    """base class for falsecolor"""
    
    def __init__(self, log=None):
        self.DEBUG = False
        self.tmpdir = ""
        if log != None:
            self._log = log
        else:
            self._initLog()

    def _initLog(self):
        self._log = logging.getLogger("falsecolor2")
        self._log.setLevel(logging.DEBUG)
        h = NullHandler()
        self._log.addHandler(h)
    

    def _clearTmpDir(self):
	"""remove old temporary files and re-create directory"""
        if os.path.isdir(self.tmpdir):
            self._log.debug("clearing self.tmpdir='%s'" % self.tmpdir)
            try:
		now = time.time()
		delta = 86400   ## 24 hours
		if self.DEBUG:
		    delta = 60  ## 1 minute
		## walk directory tree and delete files
	        for root,dirs,files in os.walk(self.tmpdir, topdown=False):
		    for name in files:
		        p = os.path.join(root, name)
			if os.stat(p).st_mtime < (now - delta):
			    self._log.debug("      deleting file '%s'" % p)
	                    os.remove(p)
		    for name in dirs:
		        p = os.path.join(root, name)
			if os.stat(p).st_mtime < (now - delta):
			    self._log.debug("      deleting dir '%s'" % p)
	                    os.rmdir(p)
	        ## finally recreate self.tmpdir
		if not os.path.isdir(self.tmpdir):
		    os.mkdir(self.tmpdir)
            except OSError, err:
                self._log.warning(str(err))
	else:
	    os.mkdir(self.tmpdir)


    def _createTempFile(self, data=None):
        """write input data to temporary file"""
        if data == None:
            if self._input == '':
                self._log.error("_createTempFile(): data available")
                return False
            data = self._input

        self._createTmpDir()
        fd,path = tempfile.mkstemp(suffix=".hdr",dir=self.tmpdir)
        self._log.debug("temppath='%s'" % path)
        f = open(path, "wb")
        f.write(data)
        f.close()
        return path


    def _createTempFileFromCmd(self, cmd, stdin=""):
        """create tmp file as stdout for <cmd> and return file path"""
	self._createTmpDir()
        fd,path = tempfile.mkstemp(suffix=".hdr",dir=self.tmpdir)
        self._log.debug("temppath='%s'" % path)
        f = open(path, "wb")
	try:
	    data = self._popenPipeCmd(cmd, stdin, f)
	    if os.name == 'nt':
	        path = path.replace("\\","\\\\")
	    return path
        except OSError, err:
            self._log.error(str(err))
            f.close()


    def _createTmpDir(self):
        """create temporary directory"""
        if self.tmpdir != "":
            self.tmpdir = os.path.abspath(self.tmpdir)
	    self._clearTmpDir()
        elif os.environ.has_key('_MEIPASS2'):
            ## use pyinstaller temp dir
            self.tmpdir = os.path.join(os.environ['_MEIPASS2'], 'wxfalsecolor')
	    self._clearTmpDir()
        else:
            self.tmpdir = tempfile.mkdtemp()
        
        self._log.debug("self.tmpdir='%s'" % self.tmpdir)
    

    def getImageSize(self, path):
        """extract resolution string from image and return (x,y) size"""
        try:
            f = open(path, 'rb')
            data = f.read()
            f.close()
            header, bdata = data.split("\n\n")
            parts = bdata.split("\n")[0].split()
            return (int(parts[3]),int(parts[1]))
        except Exception, err:
            self._log.debug(str(err), True)
            return (0,0)


    def log(self, msg, is_error=False):
        """append <msg> to log and write to stderr if DEBUG"""
        self._log.debug(msg)
        if self.DEBUG or is_error:
            print >>sys.stderr, msg


    def _popenPipeCmd(self, cmd, data_in, data_out=PIPE):
        """pass <data_in> to process <cmd> and return results"""
        ## convert cmd to (non-unicode?) string for subprocess
	cmd = str(cmd)
        self._log.debug("cmd= %s" % str(shlex.split(cmd)))
        if data_in:
            self._log.debug("data_in= %d bytes" % len(data_in))
	p = Popen(shlex.split(cmd), bufsize=-1, stdin=PIPE, stdout=data_out, stderr=PIPE)
        data, err = p.communicate(data_in)
	
        if err:
            self.error = err.strip()
            raise Exception, err.strip()
        if data:
            self._log.debug("data_out= %d bytes" % len(data))
            return data


    def writeLog(self, s=sys.stderr):
        """write log to stderr"""
        s.write("\nfalsecolor log:\n\n>> ")
        s.write("\n>> ".join(self._log))
        s.write("\n\n")





class FalsecolorLegend(FalsecolorBase):
    """legend for falsecolor image"""

    def __init__(self, img, log=None):
        
        FalsecolorBase.__init__(self, log)
        self._image = img
        self.resetDefaults()


    def create(self):
        """create legend image and return command to combine images"""
        if self.width < 20 or self.height < 20:
            return ''
        path = self.createLegend()
        legW,legH = self.getImageSize(path) 
        imgW,imgH = self._image.getImageResolution()
        
        ## offset table: ( pos,     legX,          legY, imgX, imgY)
        offsets = {'-S' : ((imgW-legW)/2,             0,    0,    0),    
                   '-N' : ((imgW-legW)/2,     imgH-legH,    0,    0),    
                   '-SE': (    imgW-legW,             0,    0,    0),
                   '-NE': (    imgW-legW,     imgH-legH,    0,    0),
                   '-SW': (            0,             0,    0,    0),    
                   '-NW': (            0,     imgH-legH,    0,    0),    
                   '-E' : (    imgW-legW, (imgH-legH)/2,    0,    0),    
                   '-W' : (            0, (imgH-legH)/2,    0,    0),    
                   '-ES': (    imgW-legW,             0,    0,    0),    
                   '-WS': (            0,             0,    0,    0),    
                   '-EN': (    imgW-legW,     imgH-legH,    0,    0),
                   '-WN': (            0,     imgH-legH,    0,    0),
                   'S' :  ((imgW-legW)/2,             0,    0, legH),    
                   'N' :  ((imgW-legW)/2,          imgH,    0,    0),    
                   'SE':  (         imgW,             0,    0, legH),
                   'NE':  (         imgW,          imgH,    0,    0),
                   'SW':  (            0,             0,    0, legH),    
                   'NW':  (            0,          imgH,    0,    0),    
                   'E' :  (         imgW, (imgH-legH)/2,    0,    0),    
                   'W' :  (            0, (imgH-legH)/2, legW,    0),    
                   'ES':  (         imgW,             0,    0,    0),    
                   'WS':  (            0,             0, legW,    0),    
                   'EN':  (         imgW,     imgH-legH,    0,    0),
                   'WN':  (            0,     imgH-legH, legW,    0)}
        
        ## build command line for final pcompos command
        legX,legY,imgX,imgY = offsets[self.position]
        cmd = "pcompos -bg %.f %.f %.f" % self.bgcolor 
        cmd += " - %d %d \"%s\" %d %d" % (imgX,imgY,path,legX,legY)
        return cmd


    def createColorScale(self):
        """create color gradient image with pcomb and return path"""
        if self.is_vertical():
            args = "-e v=y/yres;vleft=v;vright=v;vbelow=(y-1)/yres;vabove=(y+1)/yres;"
            colheight = self.height
            colwidth = max(int(self.width*0.3), 25)
            self._legendOffX = colwidth + 3                         ## x-offset for legend
            if self.zerooff == 0:
                self._gradientOffY = int(self._textheight / 2.0)    ## y-offset for gradient
        else:
            args = "-e v=x/xres;vleft=(x-1)/xres;vright=(x+1)/xres;vbelow=v;vabove=v;"
            colwidth = self.width
            colheight = max(int(self.height*0.5), 25)
            self._gradientOffY = self.height - colheight

        cmd = "pcomb %s %s -x %d -y %d" % (self.pc0args, args, colwidth, colheight) 
        path = self._createTempFileFromCmd(cmd)
        self._log.debug("gradient file='%s'" % path)
        return path  

        
    def createLegend(self):
        """create vertical legend image"""
        legimg = self.createText()
        colimg = self.createColorScale()
        
        ## combine gradient and legend
        cmd = "pcompos -bg %.f %.f %.f" % self.bgcolor 
        cmd += " \"%s\" %d %d" % (colimg, self._gradientOffX, self._gradientOffY)
        cmd += " \"%s\" %d %d" % (legimg, self._legendOffX,   self._legendOffY)
        path = self._createTempFileFromCmd(cmd)
        
        ## create label
        fg = "-cf %.f %.f %.f" % self.fgcolor
        bg = "-cb %.f %.f %.f" % self.bgcolor
        cmd = "psign -s -.15 %s %s -h %d %s" % (fg,bg,self._textheight,self.label)
        labimg = self._createTempFileFromCmd(cmd)
        
        ## add label at top (vertical) or left (horizontal)
        labx,laby = self.getImageSize(labimg)
        legx,legy = self.getImageSize(path)
        cmd = "pcompos -bg %.f %.f %.f" % self.bgcolor 
        if self.is_vertical():
            if not self.position.startswith("-"):
                cmd += " -x %d" % self.width
            cmd += " \"%s\" %d %d" % (labimg, int((legx-labx)/2.0), legy)
            cmd += " \"%s\" %d %d" % (  path, 0, 0)
        else:
            if not self.position.startswith("-"):
                cmd += " -y %d" % self.height
            cmd += " \"%s\" %d %d" % (labimg,    0, int((legy-laby)/2.0))
            cmd += " \"%s\" %d %d" % (  path, labx, 0)
        path = self._createTempFileFromCmd(cmd)
        self._log.debug("legend file='%s'" % path)
        return path  
        

    def createText(self):
        """create legend image with psign and return path"""
        ## legend values
        textlist = []
        for i in range(self.steps):
            if self.decades > 0:
                x = (self.steps-self.zerooff-i) / self.steps
                value = self.scale * 10**((x-1)*self.decades)
            else:
                value = self.scale * (self.steps - self.zerooff - i) / self.steps
            textlist.append(self.formatNumber(value))
        if self.zerooff == 0:
            textlist.append(self.formatNumber(0))
        self._log.debug( "legend text: '%s'" % str(textlist) )
        if self.is_vertical():
            return self._createTextV(textlist)
        else:
            return self._createTextH(textlist)
        

    def _createTextV(self, textlist):
        """create vertical legend text with psign"""
        self._textheight = math.floor(self.height / self.steps)
        fg = "-cf %.f %.f %.f" % self.fgcolor
        bg = "-cb %.f %.f %.f" % (0,0,1)
        bg = "-cb %.f %.f %.f" % self.bgcolor
        cmd = "psign -s -.15 %s %s -h %d" % (fg,bg,self._textheight)
        text = "\n".join(textlist)
        path = self._createTempFileFromCmd(cmd, text+"\n")
        if self.zerooff == 0:
            self.height = self._textheight * (len(textlist) - 1)
        else:
            self.height = self._textheight * len(textlist)
        self._log.debug("legend file='%s'" % path)
        self._log.debug("new legend height='%d'" % self.height)
        return path


    def _createTextH(self, textlist):
        """create horizontal legend text with psign and pfilt"""
        textlist.reverse()
        numbers, max_x = self._createTextHNumbers(textlist, self._textheight)

        ## adjust textheight if number of 
        if self.zerooff > 0:
            incr = self.width/len(textlist)
        else:
            incr = self.width/(len(textlist)-1)
        if incr < max_x:
            textheight = int(self._textheight * (incr / float(max_x)))
            self._log.debug("adjusting text height for legend: %d" % textheight)
            numbers, max_x = self._createTextHNumbers(textlist, textheight)
            self._legendOffY = int((self._textheight-textheight)/float(2))
        
        ## get offset for first element
        if self.zerooff > 0:
            incr = self.width/len(textlist)
        else:
            incr = self.width/(len(textlist)-1)
            self._gradientOffX = int(incr/2)

        ## create pcompos command to combine images
        parts = ["pcompos -b %.f %.f %.f" % self.bgcolor]
        if numbers[0][0]:
            off_first = int(numbers[0][1]*0.5)
        else:
            off_first = 0
        for i,(path,size_x) in enumerate(numbers):
            if path:
                offset = int((i+0.5)*incr - size_x*0.5)
                parts.append(" \"%s\" %d 0" % (path,offset))
        path = self._createTempFileFromCmd(" ".join(parts))
        return path

    
    def _createTextHNumbers(self, textlist, textheight):
        fg = "-cf %.f %.f %.f" % self.fgcolor
        bg = "-cb %.f %.f %.f" % self.bgcolor
        numbers = []
        max_x = 0
        for n in textlist:
            cmd = "psign -s -.15 %s %s -h %d" % (fg,bg,textheight)
            path = self._createTempFileFromCmd(cmd, n+"\n")
            dim = self.getImageSize(path)
            if dim:
                numbers.append( (path,dim[0]) )
                if dim[0] > max_x:
                    max_x = dim[0]
            else:
                numbers.append((None,0)) 
        return numbers, max_x

    
    def formatNumber(self,n):
        """return number formated based on self.scale"""
        if int(n) == n:
            return "%d" % n
        if float("%.1f" % n) == n:
            return "%.1f" % n
        if float("%.2f" % n) == n:
            return "%.2f" % n

        if self.scale <= 1:
            return "%.3f" % n
        elif self.scale <= 10:
            return "%.2f" % n
        elif self.scale <= 100:
            return "%.1f" % n
        else:
            return "%d" % n


    def is_vertical(self):
        """return true if legend is vertical"""
        if self.position.startswith("W") or self.position.startswith("-W"):
            return True
        if self.position.startswith("E") or self.position.startswith("-E"):
            return True
        else:
            return False

    def resetDefaults(self):
        """restore default values for legend"""
        self.label = "cd/m2"
        self.border = 0
        self.height = 200
        self.width = 100
        self.steps = 8
        self.scale = 1000
        self.decades = 0
        self.position = "WS"
        self.fgcolor = (1,1,1)
        self.bgcolor = (0,0,0)
        self.zerooff = 0.5
        self._textheight = 26
        self._legendOffX = 0
        self._legendOffY = 0
        self._gradientOffX = 0
        self._gradientOffY = 0
        self._defaultsize = (True,True)

    def setLegendHeight(self, h):
        """set legend height"""
        self.height = h
        self._defaultsize = (self._defaultsize[1], False)

    def setLegendWidth(self, w):
        """set legend width"""
        self.width = w
        self._defaultsize = (False, self._defaultsize[0])

    def setPosition(self, pos):
        """check <pos> argument and set position"""
        pos = pos.upper()
        within = ""
        if pos.startswith('-'):
            pos = pos[1:]
            within = "-"
        if pos in 'WS W WN NW N NE EN E ES SE S SW'.split():
            if pos.startswith('N') or pos.startswith('S'):
                if self._defaultsize[0] == True:
                    self.width = 400
                if self._defaultsize[1] == True:
                    self.height = 50
            self.position = within + pos
            return True
        else:
            return False




class FalsecolorImage(FalsecolorBase):
    """convert Radiance image to falsecolor and add legend"""

    def __init__(self, args=[], log=None):
        """set defaults and parse command line args""" 
        FalsecolorBase.__init__(self, log)
        self.legend = FalsecolorLegend(self, self._log)
        self._input = ''
        self.picture = '-'
        self.cpict = ''
        self.resetDefaults()

        self.data = None
        self.vertical = True    # future flag for horizontal legend
        self.tmpdir = ''
        self._irridiance = False
        self._resolution = (0,0)

        if len(args) > 0:
            self.setOptions(args)

    
    def applyMask(self):
        """mask values below self.mask with black"""
        if self.picture == "-":
            fd,maskImg = tempfile.mkstemp(suffix=".hdr",dir=self.tmpdir)
            f = open(maskImg, 'wb')
            f.write(self._input)
            f.close()
        else:
            maskImg = self.picture
        mv = self.mask / self.mult
        args = "-e ro=if(li(2)-%f,ri(1),0);go=if(li(2)-%f,gi(1),0);bo=if(li(2)-%f,bi(1),0);" % (mv,mv,mv)
        cmd = str("pcomb %s - \"%s\"" % (args, maskImg))
        self._log.debug( "applyMask cmd= %s" % str(shlex.split(cmd)) )
        self.data = self._popenPipeCmd(cmd, self.data)


    def cleanup(self):
        """delete self.tmpdir - throws error on Windows (files still in use)"""
        if self.tmpdir != "":
            if self.DEBUG:
                self._log.debug("keeping tmpdir '%s'" % self.tmpdir)
            try:
                shutil.rmtree(self.tmpdir)
            except WindowsError, err:
                self._log.warning("cleanup() error: %s" % str(err))


    def _createCalFiles(self):
        """create *.cal files"""
        self._createTmpDir()
        
        fd,pc0 = tempfile.mkstemp(suffix=".cal",dir=self.tmpdir)
        f_pc0 = open(pc0, 'w')
        f_pc0.write(TEMPLATE_PC0 % (self.scale, self.mult, self.ndivs, self.zerooff, self.redv, self.grnv, self.bluv))
        if self.docont == 'b':
            ## create contour bands
            f_pc0.write("vin(x) = stepv(x);\n")
        elif self.docont == 'a':
            ## create contour lines
            f_pc0.write("in=iscont%s\n" % self.docont)
        f_pc0.close()

        fd,pc1 = tempfile.mkstemp(suffix=".cal",dir=self.tmpdir)
        f_pc1 = open(pc1, 'w')
        f_pc1.write(TEMPLATE_PC1)
        if self.cpict == '':
            f_pc1.write("ra=0;ga=0;ba=0;\n")
        if self.decades > 0:
            f_pc1.write("map(x)=if(x-10^-%d,log10(x)/%d+1,0);\n" % (self.decades,self.decades))
        f_pc1.close()
        
        self.pc0args = "-f \"%s\"" % pc0
        self.pc1args = "-f \"%s\"" % pc1
        self.legend.pc0args = self.pc0args
        self.legend.pc1args = self.pc1args
    
        if self.cpict == self.picture:
            self.cpict = ''


    def doFalsecolor(self, keeptmp=False):
        """create part images, combine and store image data in self.data"""
        if self.error != "":
            self._log.debug("falsecolor2 error: %s" % self.error, True)
            return 
        try:
            if not self._input:
                self.readImageData()
            if self._input:
                self.falsecolor()
            if self.data and self.mask > 0:
                self.applyMask()
            if self.data:
                cmd = self.legend.create()
                if cmd != '':
                    self.data = self._popenPipeCmd(cmd, self.data)
                    self._log.debug("self.data=%d bytes" % len(self.data))
                if self.doextrem is True:
                    self.showExtremes()
            else:
                self._log.error("no data in falsecolor image")
                self.writeLog()

        except Exception, e:
            self._log.error(str(e))
            self.error = str(e)
            traceback.print_exc(file=sys.stderr)
            if not self.DEBUG:
                self.writeLog()
        
        finally:
            if keeptmp == False and self.DEBUG == False:
                self.cleanup()


    def falsecolor(self, data=""):
        """convert image data to falsecolor image data"""
        if data == "":
            data = self._input
        self._createCalFiles()
        cmd = "pcomb %s %s - %s" % (self.pc0args, self.pc1args, self.cpict)
        self.data = self._popenPipeCmd(cmd, data)

    
    def findAutoScale(self):
        """quick'n'dirty version for auto scale"""
        self._log.debug("findAutoScale()") 
        cmd = "pextrem -o"
        extreme = self._popenPipeCmd(cmd, self._input+"\n")
        minx,miny,minr,ming,minb, maxx,maxy,maxr,maxg,maxb = extreme.split()
        maxv = (float(maxr)*0.265+float(maxg)*0.67+float(maxb)*0.065)*self.mult
        for d in [0.001,0.01,0.1,1,10,100,1000,10000,100000,1000000]:
            for s in range(1,10):
                for ss in range(1,10):
                    scale = d*s + d*ss*0.1
                    if scale > maxv:
                        self.scale = scale
                        self.legend.scale = scale
                        self._log.debug("    scale=%s" % self.formatNumber(self.scale))
                        return

        ## return to defaults if scale was not found 
        self.scale = 1000
        self.legend.scale = 1000


    def formatNumber(self,n):
        return self.legend.formatNumber(n)


    def getImageResolution(self):
        """return image size"""
        return self._resolution

    
    def isIrridiance(self):
        """return True if image has irridiance data"""
        return self._irridiance


    def readImageData(self, picture=''):
        """load image data into self._input"""
        try:
            if picture != '':
                self.picture = picture
            if self.picture == "-":
                self._input = sys.stdin.read()
            else:
                self._input = file(self.picture, "rb").read()
            self.data = self._input
            self._analyzeImage()
            if self.scale == "auto":
                self.findAutoScale()
        except Exception, err:
            self.error = traceback.format_exc()


    def _analyzeImage(self):
        """
        get picture information from header lines
        """
        self._log.debug("analyzeImage()")
        parts = self._input.split("\n\n")
        self._log.debug("    image parts=%d" % len(parts))
        header = parts[0]
        self._log.debug("    image header=%d bytes" % len(header))
        
        ## read image header
        for line in header.split("\n"):
            line = line.rstrip()
            if line.startswith("pcond"):
                ## pvalue can not be used directly
                self._irridiance = False
                break
            elif line.startswith("rpict") and "-i" in line.split():
                self._irridiance = True
            elif line.startswith("rtrace") and "-i" in line.split():
                self._irridiance = True
        self._log.debug("    image _irridiance=%s" % self._irridiance)

        ## get resolution string
        data = parts[1]
        self._log.debug("    image data=%d bytes" % len(data))
        y,YRES,x,XRES = data.split("\n")[0].split()
        self._resolution = (int(XRES),int(YRES))
        self._log.debug("    image resolution=(%s,%s)" % (XRES,YRES))
    

    def resetDefaults(self):
        """set defaults for falsecolor conversion"""
        self.mult = 179.0
        self.label = 'cd/m2'
        self.scale = 1000
        self.decades = 0
        self.mask = 0
        self.redv = 'def_red(vin(v))'
        self.grnv = 'def_grn(vin(v))'
        self.bluv = 'def_blu(vin(v))'
        self.ndivs = 8
        self.docont = ''
        self.doextrem = False
        self.needfile = False
        self.error = ''
        self.zerooff = 0.5      # half step legend offset from zero
        self.legend.resetDefaults()


    def setOptions(self, args):
        """check command line args"""
       
        ## if help is required show help and exit
	if "-h" in args:
	    self.showHelp()
	    sys.exit(0)

        ## check for debugging options first
        if "-d" in args or "-df" in args:
            self.DEBUG = True
            self.legend.DEBUG = True
            if "-d" in args:
                h = logging.StreamHandler()
                h.setLevel(logging.DEBUG)
                f = logging.Formatter("%(name)s : %(levelname)-8s - %(message)s")
                h.setFormatter(f)
                self._log.addHandler(h)
            if "-df" in args:
                idx = args.index("-df") + 1
                logfile = args[args.index("-df")+1]
                if logfile.startswith("-"):
                    print >>sys.stderr, "ERROR: log file name can't start with '-' (name='%s')" % logfile
                    sys.exit(1)
                h = logging.FileHandler(logfile)
                h.setLevel(logging.DEBUG)
                f = logging.Formatter("%(levelname)-8s in %(funcName)s : %(message)s")
                h.setFormatter(f)
                self._log.addHandler(h)
            self._log.debug("begin setOptions() args=%s" % str(args))
        
        ## now loop over argument list
        try:
            while args:
                if args[0] == '-lw':
                    option = args.pop(0)
                    self.legend.setLegendWidth(int(args[0]))
                    self._log.debug("    -lw %s" % args[0])
                elif args[0] == '-lh':
                    option = args.pop(0)
                    self.legend.setLegendHeight(int(args[0]))
                    self._log.debug("    -lh %s" % args[0])
                elif args[0] == '-lp':
                    option = args.pop(0)
                    if self.legend.setPosition(args[0]) != True:
                        self.error = "illegal argument for '-lp': '%s'" % args[0]
                        break
                    self._log.debug("    -lp %s" % args[0])

                elif args[0] == '-log':
                    option = args.pop(0)
                    self.decades = int(args[0])
                    self.legend.decades = int(args[0])
                    self._log.debug("    -log %d" % int(args[0]))
                elif args[0] == '-s':
                    option = args.pop(0)
                    if args[0].startswith("a") or args[0].startswith("A"):
                        self.scale = "auto"
                    else:
                        self.scale = float(args[0])
                        self.legend.scale = float(args[0])
                elif args[0] == '-n':
                    option = args.pop(0)
                    self.ndivs = int(args[0])
                    self.legend.steps = int(args[0])
                    if self.ndivs == 0:
                        self.error = "illegal argument for '-n': '%s'" % args[0]
                        break
                    self._log.debug("    -n %d" % int(args[0]))

                elif args[0] == '-l':
                    option = args.pop(0)
                    self.legend.label = args[0]
                    self._log.debug("    -l %s" % args[0])

                elif args[0] == '-spec':
		    self.redv='old_red(vin(v))'
		    self.grnv='old_grn(vin(v))'
		    self.bluv='old_blu(vin(v))'
                
                elif args[0] == '-mask':
                    option = args.pop(0)
                    self.mask = float(args[0])
                    self._log.debug("    -l %.3f" % float(args[0]))

                elif args[0] == '-r':
                    option = args.pop(0)
                    self.redv = args[0]
                elif args[0] == '-g':
                    option = args.pop(0)
                    self.grnv = args[0]
                elif args[0] == '-b':
                    option = args.pop(0)
                    self.bluv = args[0]
                
                ## input and background image
                elif args[0] == '-i':
                    option = args.pop(0)
                    if os.path.isfile(args[0]):
                        self.picture = args[0]
                    else:
                        self.error = "no such file: \"%s\"" % args[0]
                        break
                    self._log.debug("    -i \"%s\"" % args[0])

                elif args[0] == '-p':
                    option = args.pop(0)
                    if os.path.isfile(args[0]):
                        self.cpict = args[0]
                    else:
                        self.error = "no such file: \"%s\"" % args[0]
                        break
                    self._log.debug("    -p \"%s\"" % args[0])
                
                elif args[0] == '-ip' or args[0] == '-pi':
                    option = args.pop(0)
                    if os.path.isfile(args[0]):
                        self.picture = args[0]
                        self.cpict = args[0]
                    else:
                        self.error = "no such file: \"%s\"" % args[0]
                        break
                    self._log.debug("    -ip \"%s\"" % args[0])

                ## contour line and band option
                elif args[0] == '-cl':
                    self.docont = 'a'
                    self._log.debug("    -cl [contour lines]")
                elif args[0] == '-cb':
                    self.docont = 'b'
                    self._log.debug("    -cb [contour bands]")

                elif args[0] == '-m':
                    option = args.pop(0)
                    self.mult = float(args[0])
                    self._log.debug("    -m %.2f" % float(args[0]))
                
                elif args[0] == '-t':
                    option = args.pop(0)
                    self.tmpdir = args[0]
                    self.legend.tmpdir = args[0]
                
                elif args[0] == '-d':
                    self.DEBUG = True
                elif args[0] == '-df':
                    option = args.pop(0)
                
                elif args[0] == '-e':
                    self.doextrem = True
                    self.needfile = True
                    self._log.debug("    -e [show extremes]")
                
                elif args[0] == '-z':
                    self.zerooff = 0.0
                    self.legend.zerooff = 0.0
                    self._log.debug("    -z [legend starts with 0]")

                else:
                    self.error = "bad option \"%s\"" % args[0]
                    break
                args.pop(0)

        except ValueError, e:
            self.error = "bad value for option '%s': '%s'" % (option,args[0])
            self._log.error(self.error)

        except IndexError, e:
            self.error = "missing argument for option '%s'" % option
            self._log.error(self.error)

        self._log.debug("end of setOptions()")


    def showExtremes(self):
        """create labels for min and max and combine with fc image"""
        cmd = "pextrem -o"
        extreme = self._popenPipeCmd(cmd, self._input+"\n")

        # output from pextrem -o:
        # 193 207 3.070068e-02 3.118896e-02 1.995850e-02
        # 211 202 1.292969e+00 1.308594e+00 1.300781e+00
        minx,miny,minr,ming,minb, maxx,maxy,maxr,maxg,maxb = extreme.split()

        minpos = "%d %d" % (int(minx)+self.legend.width, int(miny))
        maxpos = "%d %d" % (int(maxx)+self.legend.width, int(maxy))
        minval = (float(minr)*.265 + float(ming)*.67 + float(minb)*.065) * self.mult
        maxval = (float(maxr)*.265 + float(maxg)*.67 + float(maxb)*.065) * self.mult

        cmd = "psign -s -.15 -a 2 -h 16 %.3f" % minval 
        minvpic = self._createTempFileFromCmd(cmd)
        cmd = "psign -s -.15 -a 2 -h 16 %.3f" % maxval 
        maxvpic = self._createTempFileFromCmd(cmd)

        cmd = "pcompos - 0 0 \"%s\" %s \"%s\" %s" % (minvpic, minpos, maxvpic, maxpos)
        self.data = self._popenPipeCmd(cmd, self.data)


    def showHelp(self):
        """show usage message"""
        options = [("-h", "", "show this help message"),

        ("-i",  "IMG", "use IMG as input; the default is to read data from STDIN"), 
        ("-p",  "IMG", "use IMG as background image"), 
        ("-ip", "IMG", "use IMG as input and background image"), 

        ("-s", "SCALE", "set maximum legend value to SCALE"),
        ("-n", "STEPS", "create legend with STEPS subdivisions"),
        ("-l", "LABEL", "use LABEL as legend title; default is \"Lux\" or \"cd/m2\""),
        ("-log", "DEC", "create logarithmic scale with DEC decades below maximum"),

        ("-lh", "HEIGHT", "set legend height in pixels"),
        ("-lw", "WIDTH", "set legend width in pixels"),
        ("-lp", "[-]WS|W|WN|NW|N|NE|EN|E|ES|SE|S|SW", "set legend position to the given direction (default EN);\nif preceded by \"-\" the legend will be within the image frame"),  

        ("-cl", "", "create contour lines"),
        ("-cb", "", "create contour bands"),

        ("-e", "", "show values of brightest and darkest pixel"),
        ("-z", "", "create legend with values starting at zero"),
        ("-spec", "", "use old style color scheme"),
        ("-mask", "MINV", "mask values below MINV with background colour (black)"),
        
        ("-d", "", "print detailed progress messages to STDERR"),	
        ("-df","LOGFILE", "write detailed progress messages to LOGFILE"), 
        
        ("-t", "TEMPDIR", "use TEMPDIR as temporary directory"),
        ("-m", "MULTI", "set luminouse efficacy to MULTI; default is 179 Wh/m2"),
        ("-r", "EXPR", "set mapping of red colour channel"),
        ("-g", "EXPR", "set mapping of green colour channel"),
        ("-b", "EXPR", "set mapping of blue colour channel")]

        indent = "    " 
        sys.stdout.write("\nABOUT:\n")
        sys.stdout.write("\n%s%s (v%s,REV)\n" % (indent,sys.argv[0],VERSION))
        sys.stdout.write("\nUSAGE:\n\n")
        for o in options:
            sys.stdout.write("%s%s %s\n" % (indent, o[0],o[1])) 
            sys.stdout.write("%s%s%s\n\n" % (indent,indent, o[2].replace("\n", "\n"+indent+indent)))


    def toBMP(self, data=''):
        """convert image data to BMP image format"""
        if data == '':
            data = self.data
        cmd = "ra_bmp" 
        return self._popenPipeCmd(cmd, self.data)


    def toPPM(self, data=''):
        """convert image data to PPM image format"""
        if data == '':
            data = self.data
        cmd = "ra_ppm" 
        return self._popenPipeCmd(cmd, self.data)




if __name__ == "__main__":
    # create falsecolor image and write to stdout - like falsecolor.csh
    fc_img = FalsecolorImage(sys.argv[1:])
    fc_img.doFalsecolor()
    if os.name == 'nt':
        import msvcrt
        msvcrt.setmode(1,os.O_BINARY)
    sys.stdout.write(fc_img.data)

    if fc_img.error:
        print >>sys.stderr, "falsecolor.py error:", fc_img.error
        sys.exit(1)
    else:
        sys.exit(0)


