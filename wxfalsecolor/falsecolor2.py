#!/usr/bin/env python

import os
import sys
import tempfile
import time
import shlex, shutil
import math
import traceback
from subprocess import Popen, PIPE

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


class FalsecolorImage:
    """convert Radiance image to falsecolor and add legend"""

    def __init__(self, args=[]):
        """set defaults and parse command line args""" 
        self.DEBUG = False
        self._input = ""
        self.picture = '-'
        self.cpict = ''
        self.resetDefaults()

        self.data = None
        self.vertical = True    # future flag for horizontal legend
        self.tmpdir = ""
        self._irridiance = False
        self._textheight = 26
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
        if self.DEBUG:
            print >>sys.stderr, "DEBUG applyMask cmd=", shlex.split(cmd)
        self.data = self._popenPipeCmd(cmd, self.data)
        

    def cleanup(self):
        """delete self.tmpdir - throws error on Windows (files still in use)"""
        if self.DEBUG and self.tmpdir != "":
            print >>sys.stderr, "DEBUG keeping tmpdir '%s'" % self.tmpdir
        if self.tmpdir != "":
            try:
                shutil.rmtree(self.tmpdir)
            except WindowsError,e:
                if self.DEBUG:
                    print >>sys.stderr, "DEBUG falsecolor cleanup() error:", str(e)


    def combineImages(self,scol,slab):
        """combine color scale, legend and fcimage to new falsecolor image"""
        cmd = "pcompos \"%s\" 0 %d -t .2 \"%s\" %d %d - %d 0" % (scol,self._scoloff,slab,self._slaboff,self.loff,self.legwidth)
        self.data = self._popenPipeCmd(cmd, self.data)
        if self.DEBUG:
            print >>sys.stderr, "DEBUG self.data=%d bytes" % len(self.data)


    def _createCalFiles(self):
        """create *.cal files"""
        self._createTmpDir()
        
        fd,pc0 = tempfile.mkstemp(suffix=".cal",dir=self.tmpdir)
        f_pc0 = open(pc0, 'w')
        f_pc0.write(TEMPLATE_PC0 % (self.scale, self.mult, self.ndivs, self.zerooff, self.redv, self.grnv, self.bluv))
        if self.docont != '':
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
    
        if self.cpict == self.picture:
            self.cpict = ''


    def createColorScale(self):
        """create color gradient image with pcomb and return path"""
        if self.vertical:
            #TODO: check diff to original
            args = "-e v=y/yres;vleft=v;vright=v;vbelow=(y-1)/yres;vabove=(y+1)/yres;"
            #args = "-e v=y/yres;vleft=v;vright=v;vbelow=(y-0.5)/yres;vabove=(y+1.5)/yres;"
        else:
            ## for future horizontal legends
            args = "-e v=x/xres;vleft=(x-1)/xres;vright=(x+1)/xres;vbelow=v;vabove=v;"
        
        if self.zerooff == 0:# and self.docont == '':
            ## zero based and filled -> place gradient and legend side by side
            colwidth = max(int(self.legwidth*0.3), 25)
            self.loff = 0                                   ## y-offset for legend
            self._slaboff = colwidth + 3                    ## x-offset for legend
            self._scoloff = int(self._textheight / 2.0)     ## y-offset for gradient
        else:
            colwidth = self.legwidth
            self._slaboff = 0   ## x-offset for legend
            self._scoloff = 0   ## y-offset for gradient
        cmd = "pcomb %s %s -x %d -y %d" % (self.pc0args, args, colwidth, self.legheight) 
        path = self._createTempFileFromCmd(cmd)
        if self.DEBUG:
            print >>sys.stderr, "DEBUG gradient file='%s'" % path
        return path  

        
    def createLegend(self):
        """create legend image with psign and return path"""
        self._textheight = math.floor(self.legheight / self.ndivs)
        textlist = [self.label]
        
        ## legend values
        for i in range(self.ndivs):
            if self.decades > 0:
                x = (self.ndivs-self.zerooff-i) / self.ndivs
                value = self.scale * 10**((x-1)*self.decades)
            else:
                value = self.scale * (self.ndivs - self.zerooff - i) / self.ndivs
            textlist.append(self._formatNumber(value))
        if self.zerooff == 0:
            textlist.append(self._formatNumber(0))

        text = "\n".join(textlist)
        if self.DEBUG:
            print >>sys.stderr, "DEBUG legend text:", " ".join(text.split())

        cmd = "psign -s -.15 -cf 1 1 1 -cb 0 0 0 -h %d" % self._textheight
        path = self._createTempFileFromCmd(cmd, text+"\n")
        if self.zerooff == 0:
            self.legheight = self._textheight * (len(textlist) - 2)
        else:
            self.legheight = self._textheight * (len(textlist) - 1)
        if self.DEBUG:
            print >>sys.stderr, "DEBUG legend file='%s'" % path
            print >>sys.stderr, "DEBUG new legend height='%d'" % self.legheight
        return path


    def _createTempFileFromCmd(self, cmd, stdin=""):
        """create tmp file as stdout for <cmd> and return file path"""
	self._createTmpDir()
        fd,path = tempfile.mkstemp(suffix=".hdr",dir=self.tmpdir)
        if self.DEBUG:
            print >>sys.stderr, "DEBUG temppath='%s'" % path
        f = open(path, "wb")
	try:
	    data = self._popenPipeCmd(cmd, stdin, f)
	    if os.name == 'nt':
	        path = path.replace("\\","\\\\")
	    return path
        except OSError:
            f.close()


    def _clearTmpDir(self):
	"""remove old temporary files and re-create directory"""
        if os.path.isdir(self.tmpdir):
	    if self.DEBUG:
                print >>sys.stderr, "DEBUG clearing self.tmpdir='%s'" % self.tmpdir
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
			    if self.DEBUG:
				print >>sys.stderr, "      deleting file '%s'" % p
	                    os.remove(p)
		    for name in dirs:
		        p = os.path.join(root, name)
			if os.stat(p).st_mtime < (now - delta):
			    if self.DEBUG:
				print >>sys.stderr, "      deleting dir '%s'" % p
	                    os.rmdir(p)
	        ## finally recreate self.tmpdir
		if not os.path.isdir(self.tmpdir):
		    os.mkdir(self.tmpdir)
            except OSError, err:
	        if self.DEBUG:
                    print >>sys.stderr, "DEBUG error:", err
	else:
	    os.mkdir(self.tmpdir)


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
        
	if self.DEBUG:
            print >>sys.stderr, "DEBUG self.tmpdir='%s'" % self.tmpdir
        

    def doFalsecolor(self, keeptmp=False):
        """create part images, combine and store image data in self.data"""
        if self.error != "":
            print >>sys.stderr, "falsecolor2 error:", self.error
            return 
        try:
            if not self._input:
                self.readImageData()
            if self._input:
                self.falsecolor()
            if self.data and self.mask > 0:
                self.applyMask()
            if self.data:
                if self.legwidth > 20 and self.legheight > 40:
                    slab = self.createLegend()
                    scol = self.createColorScale()
                    self.combineImages(scol,slab)
                if self.doextrem is True:
                    self.showExtremes()
            else:
                print >>sys.stderr, "ERROR: no data in falsecolor image"

        except Exception, e:
            print >>sys.stderr, "Falsecolor Error:", e
            self.error = str(e)
            traceback.print_exc(file=sys.stderr)
        
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


    def _formatNumber(self,n):
        """return number formated based on self.scale"""
        if self.scale <= 1:
            return "%.3f" % n
        elif self.scale <= 10:
            return "%.2f" % n
        elif self.scale <= 100:
            return "%.1f" % n
        else:
            return "%d" % n
    
    
    def getPValueLines(self):
        """run pvalue on self._input to get "x,y,r,g,b" for each pixel"""
        cmd = "pvalue -o -h -H"
        if os.name == "nt":
            path = self._createTempFileFromCmd(cmd, self._input)
            f = open(path, 'r')
            text = f.read()
            f.close()
        else:
	    text = self._popenPipeCmd(cmd, self._input)

	if self.error:
            return False
        else:
            return text


    def getImageResolution(self):
        """return image size"""
        return self._resolution

    
    def isIrridiance(self):
        """return True if image has irridiance data"""
        return self._irridiance


    def _popenPipeCmd(self, cmd, data_in, data_out=PIPE):
        """pass <data_in> to process <cmd> and return results"""
        ## convert cmd to (non-unicode?) string for subprocess
	cmd = str(cmd)
        if self.DEBUG:
            print >>sys.stderr, "DEBUG cmd=", shlex.split(cmd)
            if data_in:
                print >>sys.stderr, "DEBUG data_in= %d bytes" % len(data_in)
	p = Popen(shlex.split(cmd), bufsize=-1, stdin=PIPE, stdout=data_out, stderr=PIPE)
        data, err = p.communicate(data_in)
	
        if err:
            self.error = err.strip()
            raise Exception, err.strip()
        if data:
            if self.DEBUG:
                print >>sys.stderr, "DEBUG data_out= %d bytes" % len(data)
            return data


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
        except Exception, err:
            self.error = err


    def _analyzeImage(self):
        """
        get picture information from header lines
        
        TODO: see how pvalue command can be used to read Lux values  
        """
        parts = self._input.split("\n\n")
        header = parts[0]
        
        ## read image header
        for line in header.split("\n"):
            line = line.strip()
            if line.startswith("pcond"):
                ## pvalue can not be used directly
                self._irridiance = False
                break
            elif line.startswith("rpict") and "-i" in line.split():
                self._irridiance = True
            elif line.startswith("rtrace") and "-i" in line.split():
                self._irridiance = True

        ## get resolution string
        data = parts[1]
        y,YRES,x,XRES = data.split("\n")[0].split()
        self._resolution = (int(XRES),int(YRES))
    

    def resetDefaults(self):
        """set defaults for falsecolor conversion"""
        self.mult = 179.0
        self.label = 'Nits'
        self.scale = 1000
        self.decades = 0
        self.mask = 0
        self.redv = 'def_red(v)'
        self.grnv = 'def_grn(v)'
        self.bluv = 'def_blu(v)'
        self.ndivs = 8
        self.legwidth = 100
        self.legheight = 200
        self.docont = ''
        self.loff = 0
        self._slaboff = 0
        self._scoloff = 0 
        self.doextrem = False
        self.needfile = False
        self.error = ''
        self.zerooff = 0.5      # half step legend offset from zero


    def saveToTif(self, path, data=''):
        """convert data to TIF file"""
        if data == '':
            data = self.data
        cmd = str("ra_tiff -z - \"%s\"" % path) 
        return self._popenPipeCmd(cmd, self.data)


    def saveToFile(self, path):
        """convert image and save to file <path>"""
        pathext = os.path.splitext(path)[1]
        pathext = pathext.upper()
        try:
            data = None
            if pathext == ".TIF":
                self.saveToTif(path)
            elif pathext == ".PPM":
                data = self.toPPM()
            elif pathext == ".BMP":
                data = self.toBMP()
            else:
                data = self.data
            if data:
                f = open(path, 'wb')
                f.write(data)
                f.close()
            return True
        except Exception, err:
            self.error = str(err)
            return False

        
    def setOptions(self,args):
        """check command line args"""
        if "-d" in args:
            print >>sys.stderr, "DEBUG parseArgs:", args

        try:
            while args:
                
                if args[0] == '-lw':
                    option = args.pop(0)
                    self.legwidth = int(args[0])
                elif args[0] == '-lh':
                    option = args.pop(0)
                    self.legheight = int(args[0])
                elif args[0] == '-log':
                    option = args.pop(0)
                    self.decades = int(args[0])
                elif args[0] == '-s':
                    option = args.pop(0)
                    self.scale = float(args[0])
                elif args[0] == '-n':
                    option = args.pop(0)
                    self.ndivs = int(args[0])
                    if self.ndivs == 0:
                        self.error = "illegal argument for '-n': '%s'" % args[0]
                        break
                elif args[0] == '-l':
                    option = args.pop(0)
                    self.label = args[0]

                elif args[0] == '-spec':
		    self.redv='old_red(v)'
		    self.grnv='old_grn(v)'
		    self.bluv='old_blu(v)'
                
                elif args[0] == '-mask':
                    option = args.pop(0)
                    self.mask = float(args[0])

                elif args[0] == '-r':
                    option = args.pop(0)
                    self.redv = args[0]
                elif args[0] == '-g':
                    option = args.pop(0)
                    self.grnv = args[0]
                elif args[0] == '-b':
                    option = args.pop(0)
                    self.bluv = args[0]

                elif args[0] == '-i':
                    option = args.pop(0)
                    if os.path.isfile(args[0]):
                        self.picture = args[0]
                    else:
                        self.error = "no such file: \"%s\"" % args[0]
                        break
                elif args[0] == '-p':
                    option = args.pop(0)
                    if os.path.isfile(args[0]):
                        self.cpict = args[0]
                    else:
                        self.error = "no such file: \"%s\"" % args[0]
                        break
                elif args[0] == '-ip' or args[0] == '-pi':
                    option = args.pop(0)
                    if os.path.isfile(args[0]):
                        self.picture = args[0]
                        self.cpict = args[0]
                    else:
                        self.error = "no such file: \"%s\"" % args[0]
                        break

                elif args[0] == '-cl':
                    self.docont = 'a'
                    self.loff = 12
                elif args[0] == '-cb':
                    #if self.zerooff == 0:
                    if False:
                        print >>sys.stderr, "WARNING: '-cb' option incompatible with '-z'; using '-cl'"
                        self.docont = 'a'
                        self.loff = 12
                    else:
                        self.docont = 'b'
                        self.loff = 13

                elif args[0] == '-m':
                    option = args.pop(0)
                    self.mult = float(args[0])
                
                elif args[0] == '-t':
                    option = args.pop(0)
                    self.tmpdir = args[0]
                
                elif args[0] == '-d':
                    self.DEBUG = True
                
                elif args[0] == '-e':
                    self.doextrem = True
                    self.needfile = True
                
                elif args[0] == '-z':
                    self.zerooff = 0.0
                    #if self.docont == 'b':
                    if False:
                        print >>sys.stderr, "WARNING: '-cb' option incompatible with '-z'; using '-cl'"
                        self.docont = 'a'
                        self.loff = 12

                else:
                    self.error = "bad option \"%s\"" % args[0]
                    break
                args.pop(0)

        except ValueError, e:
            self.error = "bad value for option '%s': '%s'" % (option,args[0])
            print >>sys.stderr, "ERROR:", self.error

        except IndexError, e:
            self.error = "missing argument for option '%s'" % option
            print >>sys.stderr, "ERROR:", self.error


    def showExtremes(self):
        """create labels for min and max and combine with fc image"""
        cmd = "pextrem -o"
        extreme = self._popenPipeCmd(cmd, self._input+"\n")

        # output from pextrem -o:
        # 193 207 3.070068e-02 3.118896e-02 1.995850e-02
        # 211 202 1.292969e+00 1.308594e+00 1.300781e+00
        minx,miny,minr,ming,minb, maxx,maxy,maxr,maxg,maxb = extreme.split()

        minpos = "%d %d" % (int(minx)+self.legwidth, int(miny))
        maxpos = "%d %d" % (int(maxx)+self.legwidth, int(maxy))
        minval = (float(minr)*.265 + float(ming)*.67 + float(minb)*.065) * self.mult
        maxval = (float(maxr)*.265 + float(maxg)*.67 + float(maxb)*.065) * self.mult

        cmd = "psign -s -.15 -a 2 -h 16 %.3f" % minval 
        minvpic = self._createTempFileFromCmd(cmd)
        cmd = "psign -s -.15 -a 2 -h 16 %.3f" % maxval 
        maxvpic = self._createTempFileFromCmd(cmd)

        cmd = "pcompos - 0 0 \"%s\" %s \"%s\" %s" % (minvpic, minpos, maxvpic, maxpos)
        self.data = self._popenPipeCmd(cmd, self.data)


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


