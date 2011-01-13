##
## rgbeimage.py - part of wxfalsecolor
##
## $Id$
## $URL$

import os,sys
import array
import cStringIO
import traceback
import wx
from falsecolor2 import FalsecolorImage

WX_IMAGE_WILDCARD = "BMP file|*.bmp|JPEG file|*.jpg|PNG file|*.png|TIFF file|*.tif|PNM file|*.pnm" 
WX_IMAGE_FORMATS = {".bmp":  wx.BITMAP_TYPE_BMP,
                    ".jpg":  wx.BITMAP_TYPE_JPEG,
                    ".jpeg": wx.BITMAP_TYPE_JPEG,
                    ".png":  wx.BITMAP_TYPE_PNG,
                    ".tif":  wx.BITMAP_TYPE_TIF,
                    ".tiff": wx.BITMAP_TYPE_TIF,
                    ".pnm":  wx.BITMAP_TYPE_PNM}




class RGBEImage(FalsecolorImage):
    """extends FalsecolorImage with interactive methods"""

    def __init__(self, wxparent, *args):
        self.wxparent = wxparent
        self._array = []
        self._hasArray = False
        self.legendoffset = (0,0)
        self.legendpos = "SW"
        FalsecolorImage.__init__(self, *args)


    def cancelLoading(self, dlg, wxparent):
        """set flag when loading process has been canceled"""
        dlg.Destroy()
        wxparent.loadingCanceled = True
        self._array = []
        return


    def doFalsecolor(self, *args, **kwargs):
        """set legendoffset after falsecolor conversion"""
        FalsecolorImage.doFalsecolor(self, *args, **kwargs)
        if self.error:
            msg = "falsecolor2 error:\n%s" % self.error
            self.showError(msg)
            return False
        self.legendoffset = (0,0)
        if self.legend.position.startswith("W"):
            self.legendoffset = (self.legend.width,0)
        elif self.legend.position.startswith("N"):
            self.legendoffset = (0,self.legend.height)
        return True


    def doPcond(self, args):
        """condition image with pcond"""
        if self.picture == "-":
            path = self._createTempFile()
        else:
            path = self.picture
        cmd = "pcond %s '%s'" % (" ".join(args), path)
        try:
            data = self._popenPipeCmd(cmd, None)
            if data:
                self.data = data
                self.legendoffset = (0,0)
                return True
        except Exception, err:
            msg = "pcond error:\n%s" % self.error
            self.showError(msg)
            return False


    def getDataHeader(self):
        return self.getHeader(self.data)


    def getHeader(self, data=None):
        """return header of input picture or data"""
        if not data:
            data = self._input
        try:
            header = data.split("\n\n")[0]
            return header
        except:
            return False


    def getRGBVAt(self, pos):
        """Return r,g,b values at <pos> or -1 if no values are available"""
        if self._array == []:
            return (-1,-1,-1,-1)
        x,y = pos

        x -= self.legendoffset[0]
        y -= self.legendoffset[1]
        if x < 0 or y < 0:
            return (-1,-1,-1,-1)
        if x < self._resolution[0] and y < self._resolution[1]:
            return self._array[y][x]
        return (-1,-1,-1,-1)
        
    
    def getRGBVAverage(self, start, end):
        """calculate and return average (r,g,b,v) for rectangle"""
        rgbv = []
        for y in range(start[1],end[1]+1):
            for x in range(start[0],end[0]+1):
                r,g,b,v = self.getRGBVAt((x,y))
                if r > 0:
                    rgbv.append((r,g,b,v))
        if len(rgbv) > 0:
            r_avg = sum([t[0] for t in rgbv]) / len(rgbv)
            g_avg = sum([t[1] for t in rgbv]) / len(rgbv)
            b_avg = sum([t[2] for t in rgbv]) / len(rgbv)
            v_avg = sum([t[3] for t in rgbv]) / len(rgbv)
            return (r_avg,g_avg,b_avg,v_avg)
        else:
            return (-1,-1,-1,-1)


    def getValueAt(self, pos):
        """Return Lux value at <pos> or -1 if no values are available"""
        if not self.isIrridiance():
            return -1
        else:
            r,g,b,v = self.getRGBVAt(pos)
            return v


    def hasArrayData(self, wxparent):
        """read pixel data into array of (r,g,b,v) values"""
        if self._hasArray == True:
            return True
        elif self._array == False:
            return False
        else:
            self._hasArray = self.readArrayDataBIN(wxparent)
            return self._hasArray
        

    def readArrayData(self, wxparent):
        """read pixel data into array of (r,g,b,v) values"""
        xres, yres = self.getImageResolution()
        
        ## start modal dialog to keep user informed
        keepGoing = True
        dlg = wx.ProgressDialog("reading pixel values ...",
                                "reading raw data ...",
                                maximum = yres+1,
                                parent = wxparent,
                                style = wx.PD_APP_MODAL|wx.PD_CAN_ABORT|wx.PD_ELAPSED_TIME|wx.PD_REMAINING_TIME)
        
        lines = self.getPValueLines()
        if lines == False:
            dlg.Destroy()
            msg = "Error reading pixel values:\n%s" % self.error
            self.showError(msg)
            return False
        
        self._array = []
        scanline = []
        lineno = 0
        for line in lines.split("\n"):
            try:
                x,y,r,g,b = line.split()
                r = float(r)
                g = float(g)
                b = float(b)
                if self._irridiance:
                    v = (0.265*r+0.67*g+0.065*b)*self.mult
                else:
                    v = -1
                scanline.append((r,g,b,v))
            except:
                pass
            if len(scanline) == xres:
                self._array.append(scanline)
                scanline = []
                lineno += 1
                if lineno % 30 == 0:
                    try:
                        (keepGoing, foo) = dlg.Update(lineno, "converting image data ...")
                    except:
                        pass
            if keepGoing == False:
                dlg.Destroy()
                self._array = []
                wxparent.loadingCanceled = True
                return
        dlg.Destroy()
        if len(self._array) != yres:
            self._array = False
            return False
        else:
            self._hasArray = True
            return True


    def readArrayDataBIN(self, wxparent):
        """read binary pixel data into array of (r,g,b,v) values"""
        xres,yres = self.getImageResolution()
        keepGoing = True
        dlg = wx.ProgressDialog("reading pixel values ...",
                                "reading raw data ...",
                                maximum = 7,
                                parent = wxparent,
                                style = wx.PD_APP_MODAL|wx.PD_CAN_ABORT|wx.PD_ELAPSED_TIME)

        arr_red   = array.array('d')
        arr_green = array.array('d')
        arr_blue  = array.array('d')
        for i,channel in enumerate([(arr_red,"r"),(arr_green,"g"),(arr_blue,"b")]):
            arr,c = channel 
            (keepGoing, foo) = dlg.Update(i+1, "reading %s channel ..." % {'r':'red','g':'green','b':'blue'}[c])
            if keepGoing == False:
                return self.cancelLoading(dlg, wxparent)
            
            cmd = "pvalue -o -dd -h -H -p%s" % c.upper()
            data = self._popenPipeCmd(cmd, self._input)
            if self.error:
                self._readArrayError(dlg, "Error reading pixel values:\n%s" % self.error)
                return False
            else:
                arr.fromstring(data)
                if len(arr) != xres*yres:
                    self._readArrayError(dlg, "Error: wrong number of values (x,y=%d,%d arr=%d)" % (xres,yres,len(arr)))
                    return False
        
        ## calculate v from r,g,b 
        (keepGoing, foo) = dlg.Update(4, "calculating values ...")
        if keepGoing == False:
            return self.cancelLoading(dlg, wxparent)
        
        arr_val = [(arr_red[i]*0.265+arr_green[i]*0.67+arr_blue[i]*0.065)*179 for i in range(len(arr_red))]
       
        ## convert to array of lines
        if len(arr_red) < 500000:
            ## less feedback for small images
            dlg.Update(5, "merging channels ...")
            pixels = zip(arr_red,arr_green,arr_blue,arr_val)
            dlg.Update(6, "building scanlines ...")
            self._array = [pixels[y*xres:(y+1)*xres] for y in range(yres)]
        
        else:
            ## create new dialog for large images
            dlg.Destroy()
            dlg = wx.ProgressDialog("merging channels ...",
                                    "merging 0 % ...",
                                    maximum = xres,
                                    parent = wxparent,
                                    style = wx.PD_APP_MODAL|wx.PD_CAN_ABORT|wx.PD_ELAPSED_TIME)
            self._array = []
            for i in range(xres):
                ## update progress bar every ten lines
                if i % 10 == 0:
                    keepGoing, skip = dlg.Update(i, "merging line %d ..." % i)
                    if keepGoing == False:
                        return self.cancelLoading(dlg, wxparent)

                ## handle data line by line
                start  =     i * xres
                end    = (i+1) * xres
                reds   = arr_red[start:end] 
                greens = arr_green[start:end] 
                blues  = arr_blue[start:end]
                vals   = arr_val[start:end]
                pixels = zip(reds,greens,blues,vals)
                self._array.append(pixels)

        ## finaly close dialog
        dlg.Destroy()
        wxparent.loadingCanceled = False
        return True


    def _readArrayError(self, dlg, msg):
        """show error message and set self._array to False"""
        dlg.Destroy()
        self.showError(msg)
        self._array = False


    def saveToAny(self, path):
        """convert self.data to image format supported by wx"""
        ext = os.path.splitext(path)[1]
        ext = ext.lower()
        format = WX_IMAGE_FORMATS.get(ext, wx.BITMAP_TYPE_BMP)
        ppm = self.toPPM()
        io = cStringIO.StringIO(ppm)
        img = wx.ImageFromStream(io)
        img.SaveFile(path, format)


    def saveToFile(self, path):
        """convert image and save to file <path>"""
        pathext = os.path.splitext(path)[1]
        pathext = pathext.lower()
        try:
            data = None
            if pathext == ".hdr" or pathext == ".pic":
                data = self.data
            elif pathext == ".ppm":
                data = self.toPPM()
            else:
                self.saveToAny(path)
            
            if data:
                f = open(path, 'wb')
                f.write(data)
                f.close()
            return True

        except Exception, err:
            self.error = traceback.format_exc()
            return False

        
    def saveToTif(self, path, data=''):
        """convert data to TIF file"""
        if data == '':
            data = self.data
        cmd = str("ra_tiff -z - \"%s\"" % path) 
        self._popenPipeCmd(cmd, self.data)


    def showError(self, msg):
        """display dialog with error message"""
        dlg = wx.MessageDialog(self.wxparent, message=msg, caption="Error", style=wx.OK|wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()


    def showWarning(self, msg):
        """display dialog with error message"""
        dlg = wx.MessageDialog(self.wxparent, message=msg, caption="Warning", style=wx.YES_NO|wx.ICON_WARN)
        result == dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_OK:
            return True
        else:
            return False

