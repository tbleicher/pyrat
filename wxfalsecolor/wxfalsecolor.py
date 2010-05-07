#!/usr/bin/env python

LICENSE="""Copyright 2010 Thomas Bleicher. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

   1. Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in
      the documentation and/or other materials provided with the
      distribution.

THIS SOFTWARE IS PROVIDED BY THOMAS BLEICHER ''AS IS'' AND ANY
EXPRESSOR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED.
IN NO EVENT SHALL THOMAS BLEICHER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation
are those of the authors and should not be interpreted as representing
official policies, either expressed or implied, of Thomas Bleicher."""


import sys,os
import cStringIO
import traceback

import wx
import wx.lib.foldpanelbar as fpb
import wx.lib.buttons as buttons
from wx.lib.wordwrap import wordwrap

from falsecolor2 import FalsecolorImage

DEBUG = 0

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
        self._arrayTrue = False
        self.legendoffset = (0,0)
        self.legendpos = "leftbottom"
        FalsecolorImage.__init__(self, *args)


    def doFalsecolor(self, *args, **kwargs):
        """set legendoffset after falsecolor conversion"""
        FalsecolorImage.doFalsecolor(self, *args, **kwargs)
        if not self.error:
            self.legendoffset = (0,0)
            if self.legend.position.startswith("W"):
                self.legendoffset = (self.legend.width,0)
            elif self.legend.position.startswith("N"):
                self.legendoffset = (0,self.legend.height)


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
        if self._arrayTrue:
            return True

        if self._array == []:
            ## data not read yet
            return self.readArrayData(wxparent)
        
        
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
                return
        dlg.Destroy()
        if len(self._array) != yres:
            return False
        else:
            self._arrayTrue = True
            return True


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




class FalsecolorControlPanel(wx.Panel):

    def __init__(self, parent, parentapp, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self.parentapp = parentapp
        
        self.positions = ['WS','W','WN','NW','N','NE','EN','E','ES','SE','S','SW']
        self._buildFCButtons()
        self._cmdLine = ""


    def _buildFCButtons(self):
        """create control elements in grid layout"""
        ## type choice button
        self.fc_type = wx.Choice(self, wx.ID_ANY, choices=["color fill", "c-lines", "c-bands"])
        self.fc_type.SetStringSelection("color fill")
        self.Bind(wx.EVT_CHOICE, self.updateFCButton, self.fc_type)
        
        self.legpos = wx.Choice(self, wx.ID_ANY, choices=self.positions, size=(50,-1))
        self.legpos.SetStringSelection("WS")
        self.Bind(wx.EVT_CHOICE, self.updatePosition, self.legpos)
        self.inside = wx.CheckBox(self, wx.ID_ANY, 'inside')
        self.Bind(wx.EVT_CHECKBOX, self.updateFCButton, self.inside)
        
        self.label = wx.TextCtrl(self, wx.ID_ANY, "NITS",  size=(50,-1))
        self.scale = wx.TextCtrl(self, wx.ID_ANY, "1000",  size=(50,-1))
        self.steps = wx.TextCtrl(self, wx.ID_ANY, "8",     size=(50,-1))
        self.logv  = wx.TextCtrl(self, wx.ID_ANY, "2",     size=(50,-1))
        self.maskv = wx.TextCtrl(self, wx.ID_ANY, "0.001", size=(50,-1))

        self.fc_log  = wx.CheckBox(self, wx.ID_ANY, 'log')
        self.fc_mask = wx.CheckBox(self, wx.ID_ANY, 'mask')
        self.fc_col  = wx.CheckBox(self, wx.ID_ANY, 'old colours')
        self.fc_extr = wx.CheckBox(self, wx.ID_ANY, 'show extremes')
        self.fc_zero = wx.CheckBox(self, wx.ID_ANY, '0 based leg')
        
        self.legW = wx.TextCtrl(self, wx.ID_ANY, "100", size=(50,-1))
        self.legH = wx.TextCtrl(self, wx.ID_ANY, "200", size=(50,-1))
        
        ## 'falsecolor' button
        self.doFCButton = buttons.GenButton(self, wx.ID_ANY, label='falsecolor')
        self.doFCButton.Bind(wx.EVT_LEFT_DOWN, self.doFalsecolor)
        self.doFCButton.Disable()

        layout = [(self.fc_type,                             None),
                  (self.inside,                              self.legpos),
                  (wx.Panel(self,wx.ID_ANY,size=(-1,10)),    None),
                  (wx.StaticText(self, wx.ID_ANY, "label:"), self.label),
                  (wx.StaticText(self, wx.ID_ANY, "scale:"), self.scale),
                  (wx.StaticText(self, wx.ID_ANY, "steps:"), self.steps),
                  (wx.Panel(self,wx.ID_ANY,size=(-1,10)),    None),
                  (self.fc_log,                              self.logv),
                  (self.fc_mask,                             self.maskv),
                  (self.fc_col,                              None),
                  (self.fc_extr,                             None),
                  (self.fc_zero,                             None),
                  (wx.Panel(self,wx.ID_ANY,size=(-1,10)),    None),
                  (wx.StaticText(self, wx.ID_ANY, "leg-w:"), self.legW),
                  (wx.StaticText(self, wx.ID_ANY, "leg-h:"), self.legH),
                  (wx.Panel(self,wx.ID_ANY,size=(-1,10)),    None),
                  (self.doFCButton,                          None),
                  (wx.Panel(self,wx.ID_ANY,size=(-1,5)),     None)]
        
        ## create grid sizer
        grid = wx.GridBagSizer(2,2)
        for r,row in enumerate(layout):
            c1,c2 = row
            if c2:
                grid.Add( c1, (r,0),        flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)
                grid.Add( c2, (r,1),        flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)
            else:
                grid.Add( c1, (r,0), (1,2), flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)
       
        ## bind events
        self.Bind(wx.EVT_TEXT, self.updateFCButton, self.label)
        self.Bind(wx.EVT_TEXT, self.updateFCButton, self.scale)
        self.Bind(wx.EVT_TEXT, self.updateFCButton, self.steps)
        self.Bind(wx.EVT_TEXT, self.updateFCButton, self.logv)
        self.Bind(wx.EVT_TEXT, self.updateFCButton, self.maskv)
        self.Bind(wx.EVT_TEXT, self.updateFCButton, self.legW)
        self.Bind(wx.EVT_TEXT, self.updateFCButton, self.legH)
        self.Bind(wx.EVT_CHECKBOX, self.updateFCButton, self.fc_log)
        self.Bind(wx.EVT_CHECKBOX, self.updateFCButton, self.fc_mask)
        self.Bind(wx.EVT_CHECKBOX, self.updateFCButton, self.fc_col)
        self.Bind(wx.EVT_CHECKBOX, self.updateFCButton, self.fc_extr)
        self.Bind(wx.EVT_CHECKBOX, self.updateFCButton, self.fc_zero)
        
        self.SetSizer(grid)
        self.SetInitialSize()


    def doFalsecolor(self, event):
        """start conversion to falsecolor and update button"""
        if self.parentapp.rgbe2fc(event) == True:
            self._cmdLine = " ".join(self.getFCArgs())
            self.doFCButton.SetLabel("update fc")
            self.doFCButton.Disable()
            self.doFCButton.SetBackgroundColour(wx.WHITE)
        else:
            self.doFCButton.SetLabel("update fc")
            self.doFCButton.Enable()
            self.doFCButton.SetBackgroundColour(wx.RED)
        self.doFCButton.Refresh()


    def enableFC(self, text=""):
        """enable and update doFCButton"""
        self.doFCButton.Enable()
        if text != "":
            self.doFCButton.SetLabel(text)
        self.doFCButton.Refresh()


    def getFCArgs(self):
        """collect command line args as list"""
        args = []
        #args.extend(["-t", "./tempdir"])
        
        if self.fc_type.GetCurrentSelection() > 0:
            args.append(["", "-cl", "-cb"][self.fc_type.GetCurrentSelection()])
        
        position = self.positions[self.legpos.GetCurrentSelection()]
        if self.inside.GetValue():
            position = "-" + position
        args.extend(["-lp", position])
        args.extend(["-lw", self.legW.GetValue()])
        args.extend(["-lh", self.legH.GetValue()])

        args.extend(["-l", self.label.GetValue()])
        args.extend(["-s", self.scale.GetValue()])
        args.extend(["-n", self.steps.GetValue()])
        
        if self.fc_log.GetValue():
            args.extend(["-log", self.logv.GetValue()])
        if self.fc_mask.GetValue():
            args.extend(["-mask", self.maskv.GetValue()])
        if self.fc_col.GetValue():
            args.append("-spec")
        if self.fc_extr.GetValue():
            args.append("-e")
        if self.fc_zero.GetValue():
            args.append("-z")
        return args        


    def setFCLabel(self, text):
        self.label.SetValue(text)

    
    def updateFCButton(self, event):
        """set label of falsecolor button to 'update'"""
        if self._cmdLine != "":
            newCmd = " ".join(self.getFCArgs())
            if self._cmdLine != newCmd:
                self.doFCButton.SetLabel("update fc")
                self.doFCButton.Enable()
                self.doFCButton.SetBackgroundColour(wx.RED)
            else:
                self.doFCButton.Disable()
                self.doFCButton.SetBackgroundColour(wx.WHITE)
            self.doFCButton.Refresh()


    def updatePosition(self, event):
        """update height and width when position changes"""
        pos = self.positions[self.legpos.GetCurrentSelection()]
        pos = pos.replace("-", "")
        if pos.startswith("W") or pos.startswith("E"):
            self.legW.SetValue("100")
            self.legH.SetValue("200")
        else:
            self.legW.SetValue("400")
            self.legH.SetValue("50")




class FoldableControlsPanel(wx.Panel):
    """combines individual feature panels"""
    
    def __init__(self, parent, id=wx.ID_ANY, title="", pos=wx.DefaultPosition,
                 style=wx.DEFAULT_FRAME_STYLE):

        wx.Panel.__init__(self, parent, id)
        self.parent = parent
        self.SetSize((130,350))
        self.CreateFoldBar()
        self.Bind(wx.EVT_SIZE, self.setBarSize)
        

    def CreateFoldBar(self, vertical=True):
        bar = fpb.FoldPanelBar(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
                           fpb.FPB_DEFAULT_STYLE|fpb.FPB_VERTICAL)

        item = bar.AddFoldPanel("ximage", collapsed=False)
        pc_controls = self._buildXimageButtons(item)
        bar.AddFoldPanelWindow(item, pc_controls)
        
        item = bar.AddFoldPanel("falsecolor", collapsed=False)
        self.fcpanel = FalsecolorControlPanel(item, self.parent)
        bar.AddFoldPanelWindow(item, self.fcpanel)
        
        item = bar.AddFoldPanel("misc", collapsed=True)
        pc_controls = self._buildMiscButtons(item)
        bar.AddFoldPanelWindow(item, pc_controls)
        
        if hasattr(self, "pnl"):
            self.pnl.Destroy()
        self.pnl = bar

        size = self.GetClientSize()
        self.pnl.SetDimensions(0, 0, size.GetWidth(), size.GetHeight())

    def _buildMiscButtons(self, parent):
        panel = wx.Panel(parent,wx.ID_ANY,size=(-1,35))
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        about = wx.Button(panel, wx.ID_ANY, "about")
        about.Bind(wx.EVT_BUTTON, self.OnAbout)
        sizer.Add(about, proportion=0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=5)
        
        ## add spacer and set size
        spacer = wx.Panel(panel, wx.ID_ANY, size=(-1,5))
        sizer.Add(spacer, proportion=0, flag=wx.EXPAND|wx.ALL, border=0)
        panel.SetSizer(sizer)
        panel.SetInitialSize()
        return panel


    def _buildPcondButtons(self, panel):
        pcpanel = wx.Panel(panel,wx.ID_ANY,size=(-1,35))
        pcsizer = wx.BoxSizer(wx.VERTICAL)
        
        button1 = wx.Button(pcpanel, wx.ID_ANY, "pcond TODO")
        button1.Bind(wx.EVT_BUTTON, self.OnCollapseMe)
        pcsizer.Add(button1, proportion=0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=5)
        button2 = wx.Button(pcpanel, wx.ID_ANY, "pcond TODO")
        button2.Bind(wx.EVT_BUTTON, self.OnCollapseMe)
        pcsizer.Add(button2, proportion=0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=5)
        
        ## add spacer and set size
        spacer = wx.Panel(pcpanel, wx.ID_ANY, size=(-1,5))
        pcsizer.Add(spacer, proportion=0, flag=wx.EXPAND|wx.ALL, border=0)
        pcpanel.SetSizer(pcsizer)
        pcpanel.SetInitialSize()
        return pcpanel
    
    
    def _buildXimageButtons(self, panel):
        xipanel = wx.Panel(panel,wx.ID_ANY,size=(-1,35))
        #xipanel.SetBackgroundColour(wx.RED)
        xisizer = wx.BoxSizer(wx.VERTICAL)
        
        self.showValues = wx.CheckBox(xipanel, wx.ID_ANY, "show values")
        self.showValues.Bind(wx.EVT_CHECKBOX, self.OnShowValues)
        self.showValues.Disable()
        xisizer.Add(self.showValues, proportion=0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=5)
        
        clearButton = wx.Button(xipanel, wx.ID_ANY, "clear labels")
        clearButton.Bind(wx.EVT_BUTTON, self.OnClearLabels)
        xisizer.Add(clearButton, proportion=0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=5)
        
        saveBitmap = wx.Button(xipanel, wx.ID_ANY, "save bitmap")
        saveBitmap.Bind(wx.EVT_BUTTON, self.OnSaveBitmap)
        xisizer.Add(saveBitmap, proportion=0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=5)
        
        ## spacer
        spacer = wx.Panel(xipanel, wx.ID_ANY, size=(-1,5))
        xisizer.Add(spacer, proportion=0, flag=wx.EXPAND|wx.ALL, border=0)

        xipanel.SetSizer(xisizer)
        xipanel.SetInitialSize()
        return xipanel


    def disableShowValues(self):
        self.showValues.SetValue(False)
        self.showValues.Disable()

    def enableFC(self, text=""):
        self.fcpanel.enableFC(text)

    def enableShowValues(self,status=False):
        self.showValues.Enable()
        self.showValues.SetValue(status)

    def getFCArgs(self):
        return self.fcpanel.getFCArgs()

    def OnAbout(self, event):
        self.parent.showAboutDialog()

    def OnClearLabels(self, event):
        self.parent.picturepanel.clearLabels()
    
    def OnCollapseMe(self, event):
        item = self.pnl.GetFoldPanel(0)
        self.pnl.Collapse(item)

    def OnExpandMe(self, event):
        self.pnl.Expand(self.pnl.GetFoldPanel(0))
        self.pnl.Collapse(self.pnl.GetFoldPanel(1))

    def OnSaveBitmap(self, event):
        self.parent.picturepanel.saveBitmap()
    
    def OnShowValues(self, event):
        self.parent.setShowValues(self.showValues.GetValue())

    def setBarSize(self, event):
        size = event.GetSize()
        self.pnl.SetDimensions(0, 0, size.GetWidth(), size.GetHeight())
        
    def setFCLabel(self, text):
        self.fcpanel.setFCLabel(text)



class FileDropTarget(wx.FileDropTarget):
    """implement file drop feature for ImagePanel"""
    def __init__(self, app):
        wx.FileDropTarget.__init__(self)
        self.app = app

    def OnDropFiles(self, x, y, filenames):
        """validate image before passing it on to self.app.loadImage()"""
        path = filenames[0]
	## create RGBEImage to check file type and data
        rgbeImg = RGBEImage(self, ["-i", path])
        rgbeImg.readImageData(path)
        if rgbeImg.error:
            msg = "Error loading image.\nFile: %s\nError: %s" % (path,rgbeImg.error)
            self.app.showError(msg)
        else:
            ## now load for real
            self.app.loadImage(path)
        


class ImagePanel(wx.Panel):
    """
    A panel to display the bitmap image data.
    """
    def __init__(self, parent, *args, **kwargs):
        wx.Panel.__init__(self, parent,
                          style=wx.SUNKEN_BORDER|wx.NO_FULL_REPAINT_ON_RESIZE,
                          *args, **kwargs)
        
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.DoNothing)

        self.SetDropTarget(FileDropTarget(parent))
        
        self.parent = parent
        self.bmp = None
        self.img = None
        self._scale = 0
        self._scaledImg = None
        self._labels = []
        self.size = self.GetSize()
        self._dragging = False
        self._draggingFrame = (0,0)

        self.OnSize(None)


    def addLabel(self, x, y, dx=0, dy=0):
        """get value for (x,y) and add to self._labels"""
        self._dragging = False
        
        w,h = self._scaledImg.GetSize()
        if x <= w and y <= h:
            if self._scale > 1:
                x = int(x*self._scale)
                y = int(y*self._scale)
            if dx == 0:
                r,g,b,v = self.parent.getRGBVAt((x,y))
            else:
                r,g,b,v = self.parent.getRGBVAverage((x,y),(x+dx,y+dy))
            #print "TEST: fake values for rgbv"
            #r,g,b,v = (0.1,0.2,0.3,(0.0265+0.134+0.0195)*179)
 
        if r > 0:
            if v > 0:
                label = "%s lux" % self.parent.formatNumber(v)
            else:
                lum = (r*0.265+g*0.67+b*0.065)*179
                label = "%s cd/m2" % self.parent.formatNumber(lum)
            if dx == 0:
                dx = 2
                dy = 2
            self._labels.append((x,y, label, dx,dy))
            self.UpdateDrawing()


    def clearLabels(self):
        """reset lables list"""
        self._labels = []
        self.UpdateDrawing()


    def DoNothing(self, evt):
        """swallow EVT_ERASE_BACKGROUND"""
        pass


    def Draw(self, dc):
        """do the actual drawing"""
        try:
            gc = wx.GraphicsContext.Create(dc)
        except NotImplementedError:
            dc.DrawText("wx.GraphicsContext not supported", 25, 25)
            return

        #self._drawBackground(gc)
        ## draw image
        if self._scaledImg:
            self._drawBMP(gc)
        ## draw overlay
        if self._labels != []:
            self._drawLabels(gc)
        
        if self._dragging:
            self._drawDraggingFrame(gc)


    def _drawBackground(self, gc):
        """debug method: draw pink background to show image shape"""
        path_bg = gc.CreatePath()
        w,h = self.GetClientSizeTuple()
        path_bg.AddRectangle(0,0,w,h)
        gc.SetBrush(wx.Brush("pink"))
        gc.DrawPath(path_bg)


    def _drawBMP(self, gc):
        """draw (background) bitmap to graphics context"""
        bmp = wx.BitmapFromImage(self._scaledImg)
        size = bmp.GetSize()
        gc.DrawBitmap(bmp, 0,0, size.width, size.height)


    def _drawDraggingFrame(self,gc):
        """draw translucent frame over dragging area"""
        x,y = self._dragging
        dx,dy = self._draggingFrame
        if dx < 0:
            x += dx
            dx *= -1
        if dy < 0:
            y += dy
            dy *= -1
        gc.PushState()
        gc.SetPen(wx.Pen(wx.BLUE, 1))
        gc.SetBrush(wx.Brush(wx.Colour(0,0,255,51), wx.SOLID))
        gc.Translate(x,y)
        path = gc.CreatePath()
        path.AddRectangle(0,0,dx,dy)
        gc.DrawPath(path)
        gc.PopState()


    def _drawLabels(self, gc):
        """draw labels with r,g,b or lux values""" 
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetWeight(wx.BOLD)
        gc.SetFont(font)
        for x,y,l,dx,dy in self._labels:
            if self._scale > 1:
                x /= self._scale
                y /= self._scale
            w,h = gc.GetTextExtent(l)
            path_spot = gc.CreatePath()
            path_spot.AddRectangle(-1,-1,dx,dy)
            path_label = gc.CreatePath()
            path_label.AddRectangle(0,-1,w+3,h+1)
            gc.PushState()
            gc.Translate(x,y)
            gc.SetPen(wx.Pen(wx.BLACK, 1))
            gc.SetBrush(wx.Brush(wx.WHITE))
            gc.DrawPath(path_label)
            gc.DrawText(l,2,0)
            gc.SetPen(wx.Pen(wx.RED, 1))
            gc.SetBrush(wx.Brush(wx.RED, wx.TRANSPARENT))
            gc.DrawPath(path_spot)
            gc.PopState()


    def _drawTestPath(self, gc):
        BASE  = 80.0    # sizes used in shapes drawn below
        BASE2 = BASE/2
        BASE4 = BASE/4
        path = gc.CreatePath()
        path.AddCircle(0, 0, BASE2)
        path.MoveToPoint(0, -BASE2)
        path.AddLineToPoint(0, BASE2)
        path.MoveToPoint(-BASE2, 0)
        path.AddLineToPoint(BASE2, 0)
        path.CloseSubpath()
        path.AddRectangle(-BASE4, -BASE4/2, BASE2, BASE4)

        # Now use that path to demonstrate various capbilites of the grpahics context
        gc.PushState()             # save current translation/scale/other state 
        gc.Translate(60, 75)       # reposition the context origin

        gc.SetPen(wx.Pen("navy", 1))
        gc.SetBrush(wx.Brush("pink"))
        gc.DrawPath(path)
        gc.PopState()


    def _getBitmapPath(self):
        """show dialog to save bitmap file"""
        path = self.parent.path
        if path == '':
            return ''
        
        dirname, filename = os.path.split(path)
        filebase = os.path.splitext(filename)[0]
        filedialog = wx.FileDialog(self,
                          message = 'save image',
                          defaultDir = dirname,
                          defaultFile = filebase + '.bmp',
                          wildcard = WX_IMAGE_WILDCARD,
                          style = wx.SAVE)
        if filedialog.ShowModal() == wx.ID_OK:
            return filedialog.GetPath()
        else:
            return '' 


    def OnLeftDown(self, evt):
        """set dragging flag when left mouse button is pressed"""
        if self._scaledImg == None:
            return
        self._dragging = evt.GetPosition()
        self._draggingFrame = (0,0)


    def OnLeftUp(self, evt):
        """show spot or average reading"""
        if self._scaledImg == None:
            return
        x2,y2 = evt.GetPosition() 
        if self._dragging == False:
            self.addLabel(x2,y2)
        else:
            x1,y1 = self._dragging
            if x1 > x2:
                x1,x2 = x2,x1
            if y1 > y2:
                y1,y2 = y2,y1
            dx = x2 - x1
            dy = y2 - y1
            if dx > 2 and dy > 2:
                self.addLabel(x1,y1,dx,dy)
            else:
                self.addLabel(x2,y2)
        self._dragging = False
        self._draggingFrame = (0,0)
        self.UpdateDrawing()


    def OnMouseMotion(self, evt):
        """return cursor (x,y) in pixel coords of self.img - (x,y) is 0 based!"""
        if self._scaledImg == None:
            return
        
        x,y = evt.GetPosition()
        if self._dragging != False:
            ## draw dragging frame
            dx = x - self._dragging[0]
            dy = y - self._dragging[1]
            self._draggingFrame = (dx,dy)
            self.UpdateDrawing()

        w,h = self._scaledImg.GetSize()
        if x <= w and y <= h:
            if self._scale > 1:
                x *= self._scale
                y *= self._scale
            self.parent.showPixelValueAt( (int(x),int(y)) )
        
    
    def OnPaint(self, evt):
        """redraw image panel area"""
        dc = wx.BufferedPaintDC(self, self._Buffer)
        return
        if USE_BUFFERED_DC:
            dc = wx.BufferedPaintDC(self, self._Buffer)
        else:
            dc = wx.PaintDC(self)
            dc.DrawBitmap(self._Buffer,0,0)


    def OnSize(self, evt):
        """create new buffer and update window"""
        size = self.GetClientSizeTuple()
        self._Buffer = wx.EmptyBitmap(*size)
        self.resizeImage(size)
        self.UpdateDrawing()


    def resizeImage(self, size):
        """scale image to fit frame proportionally"""
        self.size = size
        if not self.img:
            return
        w,h = self.img.GetSize()
        size = self.GetSize()
        if w != 0 and size[0] != 0:
            scale_x = w / float(size[0])
            scale_y = h / float(size[1])
            self._scale = max(scale_x,scale_y)
            if self._scale != 0:
                if self._scale > 1:
                    self._scaledImg = self.img.Scale( int(w/self._scale), int(h/self._scale) )
                else:
                    self._scaledImg = self.img
            self.SetSize(self._scaledImg.GetSize())
            self.Refresh()
   

    def saveBitmap(self, path=''):
        """save buffer image to file"""
        if path == '':
            path = self._getBitmapPath()

        if path == '':
            return

        ext = os.path.splitext(path)[1]
        ext = ext.lower()
        format = WX_IMAGE_FORMATS.get(ext, wx.BITMAP_TYPE_BMP)
        
        fw,fh = self.GetSize()
        try:
            img = self._Buffer.ConvertToImage()
            w,h = img.GetSize()
            if w > fw:
                img = img.Size((fw,h), (0,0))
            elif h > fh:
                img = img.Size((w,fh), (0,0))
            img.SaveFile(path, format)
        except Exception, err:
            msg = "Error saving image:\n%s\n%s" % (str(err), traceback.format_exc())
            self.parent.showError(msg)
    

    def setImage(self, img):
        """set wx.Image"""
        self.img = img
        self.OnSize(None)
        ## call parent.Layout() to force resize of panel
        self.parent.Layout()


    def UpdateDrawing(self):
        """updates drawing when needed (not by system)"""
        dc = wx.BufferedDC(wx.ClientDC(self), self._Buffer)
        self.Draw(dc)
        return
        if USE_BUFFERED_DC:
            dc = wx.BufferedDC(wx.ClientDC(self), self._Buffer)
            self.Draw(dc)
        else:
            dc = wx.MemoryDC()
            dc.SelectObject(self._Buffer)
            self.Draw(dc)
            wx.ClientDC(self).DrawBitmap(self._Buffer, 0,0)



class wxFalsecolorFrame(wx.Frame):

    def __init__(self, args=[]):
        wx.Frame.__init__(self,None,title = "wxImage - Radiance Picture Viewer")
        
        ## menu
        self._addMenu()
        
        ## image display
        self.picturepanel = ImagePanel(self)

        ## buttons
        self._doButtonLayout()

        ## image - buttons layout
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.panelSizer,   proportion=0, flag=wx.EXPAND)
        self.sizer.Add(self.picturepanel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(self.sizer)
        self.statusbar = self.CreateStatusBar()

        self.rgbeImg = None
        self._array = []
        self.img = None
        self.path = ""
        self.filename = ""

        self._ra2tiff = self._searchBinary("ra2tiff")

        self.Size = (800,600)
        
        path,args = self._checkCmdArgs(args)
        if path != "":
            self.loadImage(path,args)
        self.Show()


    def _addFileButtons(self):
        """create top buttons"""
        self.loadButton = wx.Button(self, wx.ID_ANY, label='open HDR')
        self.loadButton.Bind(wx.EVT_LEFT_DOWN, self.onLoadImage)
        self.panelSizer.Add(self.loadButton, proportion=0, flag=wx.EXPAND|wx.ALL, border=5 )
        
        self.saveButton = wx.Button(self, wx.ID_ANY, label='save image')
        self.saveButton.Bind(wx.EVT_LEFT_DOWN, self.onSaveImage)
        self.saveButton.Disable()
        self.panelSizer.Add(self.saveButton, proportion=0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5 )
        
        spacepanel = wx.Panel(self,wx.ID_ANY,size=(-1,5))
        if os.name == 'nt':
            spacepanel.SetBackgroundColour((128,128,128))
        self.panelSizer.Add(spacepanel, proportion=0, flag=wx.EXPAND)


    def _addMenu(self):
        """add menu to frame (disabled)"""
        return
        self.menubar = wx.MenuBar()
        self.SetMenuBar(self.menubar)
        self.fileMenu = wx.Menu()
        self.menubar.Append(self.file, '&File')
        self.fileOpen = self.file.Append(wx.ID_ANY, '&Open file')
        self.Bind(wx.EVT_MENU, self.onLoadImage, self.fileOpen)


    def _checkCmdArgs(self, args):
        """convert command line args to use with falsecolor2"""
        ## -i <path> is added by loadFile, so remove path and option now
        if "-i" in args or '-ip' in args:
            try:
                idx = args.index("-i")
            except ValueError:
                idx = args.index("-ip")
            try:
                path = args[idx+1]
                if os.path.isfile(path):
                    del args[idx:idx+2]
                    return (path, args)
            except IndexError:
                del args[idx]
                return ("", args)
        ## path is last argument (drag-n-drop and incorrect use)
        if len(args) > 0 and os.path.isfile(args[-1]):
            if len(args) == 1 or args[-2] != '-p':
                path = args.pop()
                args = []
                return (path,args)
        ## if we can't find an input file, don't load stuff
        return ("", args)


    def _doButtonLayout(self):
        """create buttons"""
        self.panelSizer = wx.BoxSizer(wx.VERTICAL)
        ## 'load' and 'save' buttons 
        self._addFileButtons()
        
        ## foldable controls panel
        self.controls = FoldableControlsPanel(self, wx.ID_ANY)
        self.panelSizer.Add(self.controls, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        
        ## 'quit' button
        quitbutton = wx.Button(self, wx.ID_EXIT, label='quit')
        quitbutton.Bind(wx.EVT_LEFT_DOWN,self.onQuit)
        self.panelSizer.Add( quitbutton, proportion=0, flag=wx.EXPAND|wx.ALL|wx.ALIGN_BOTTOM, border=10 )


    def formatNumber(self, n):
        """use FalsecolorImage formating for consistency"""
        if self.rgbeImg:
            return self.rgbeImg.formatNumber(n)
        else:
            return str(n)


    def getFrameSize(self):
        """return available size for image frame"""
        w,h = self.GetClientSize()
        return (w-130,h)


    def getRGBVAt(self, pos):
        """return pixel value at position"""
        if self.rgbeImg:
            return self.rgbeImg.getRGBVAt(pos)
        else:
            return (-1,-1,-1,-1)


    def getRGBVAverage(self, start, end):
        """return average pixel value for rectangle"""
        if self.rgbeImg:
            return self.rgbeImg.getRGBVAverage(start,end)
        else:
            return (-1,-1,-1,-1)


    def loadImage(self, path, args=[]):
        """create instance of falsecolor image from <path>"""
        self.reset()
        self.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))
        fcargs = ["-s", "auto", "-i", path] + args
        if DEBUG:
            fcargs = ["-d"] + fcargs
	self.rgbeImg = RGBEImage(self, fcargs)
        self.rgbeImg.readImageData(path)
        if self.rgbeImg.error:
            msg = "Error loading image:\n%s" % self.rgbeImg.error
            self.showError(msg)
        else:
            if self._showValues:
                self.setShowValues(True)
            self.updatePicturePanel()
            if self.img:
                self.path = path
                self.filename = os.path.split(path)[1]
            if self.rgbeImg.isIrridiance():
                self.controls.setFCLabel("Lux")
            self.saveButton.Enable()
            self.controls.enableFC("convert fc")
        self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))


    def onLoadImage(self,event):
        """load new Radiance RGBE image"""
        filedialog = wx.FileDialog(self,
                          message = 'Choose an image to open',
                          defaultDir = '',
                          defaultFile = '',
                          wildcard = 'Radiance Image Files (*.hdr,*.pic)|*.hdr;*.pic|all files |*.*',
                          style = wx.OPEN)
        if filedialog.ShowModal() == wx.ID_OK:
            path = filedialog.GetPath()
            self.loadImage(path)


    def onQuit(self, event):
        """hasta la vista"""
        self.Close()


    def onSaveImage(self, event):
        """save bmp image to file"""
        dirname, filename = os.path.split(self.path)
        filebase = os.path.splitext(filename)[0]
        #formats = "|".join(["HDR file|*.hdr", WX_IMAGE_WILDCARD, "PIC (old)|*.pic"])
        formats = "|".join(["HDR file|*.hdr", WX_IMAGE_WILDCARD, "PPM file|*.ppm"])
        filedialog = wx.FileDialog(self,
                          message = 'save image',
                          defaultDir = dirname,
                          defaultFile = filebase + '.hdr',
                          wildcard = formats,
                          style = wx.SAVE)
        if filedialog.ShowModal() == wx.ID_OK:
            path = filedialog.GetPath()
            result = self.rgbeImg.saveToFile(path)
            if result != True:
                msg = "Error saving image:\n" + self.rgbeImg.error
                self.showError(msg)
            else:
                self.statusbar.SetStatusText("saved file '%s'" % path)


    def reset(self):
        """reset array to inital (empty) values"""
        self._array = []
        self._arrayTrue = False
        self._showValues = False
        self.controls.enableShowValues()
        self.picturepanel.clearLabels()


    def rgbe2fc(self,event):
        """convert Radiance RGBE image to wx.Bitmap"""
        self.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))
        args = self.controls.getFCArgs()
        self.rgbeImg.resetDefaults()
        self.rgbeImg.setOptions(args)
        self.rgbeImg.doFalsecolor()
        if self.rgbeImg.error:
            self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
            msg = "Error creating falsecolor:\n%s" % self.rgbeImg.error 
            self.showError(msg)
            return False
        else:
            self.updatePicturePanel()
            self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
            return True


    def _searchBinary(self,bname):
        """try to find <bname> in search path"""
        paths = os.environ['PATH']
        extensions = ['']
        try:
            if os.name == 'nt':
                extensions = os.environ['PATHEXT'].split(os.pathsep)
            for path in paths.split(os.pathsep):
                for ext in extensions:
                    binpath = os.path.join(path,bname) + ext
                    if os.path.exists(binpath):
                        return binpath
        except Exception, err:
            traceback.print_exc(file=sys.stderr) 
            return False
        ## if nothing was found return False
        return False


    def setShowValues(self, show):
        """set flag to display pixel values"""
        if show == True:
            if self.rgbeImg:
                ## start reading image data
                result = self.rgbeImg.hasArrayData(self)
                if result == None:
                    ## reading canceled by user
                    self._showValues = False
                    self.controls.enableShowValues()
                elif result == True:
                    ## data is now available
                    self._showValues = True
                    self.controls.enableShowValues(True)
                elif result == False:
                    ## error reading data
                    self._showValues = True
                    self.controls.disableShowValues()
            else:
                self._showValues = False
        else:
            self._showValues = False
 

    def showAboutDialog(self):
        """show dialog with license etc"""
        info = wx.AboutDialogInfo()
        info.Name = "wxfalsecolor"
        info.Version = "v0.2 (rREV)"     # placeholder for build script 
        info.Copyright = "(c) 2010 Thomas Bleicher"
        info.Description = "cross-platform GUI frontend for falsecolor"
        info.WebSite = ("http://sites.google.com/site/tbleicher/radiance/wxfalsecolor", "wxfalsecolor home page")
        info.Developers = ["Thomas Bleicher", "Axel Jacobs"]
        info.License = wordwrap(LICENSE, 500, wx.ClientDC(self))
        wx.AboutBox(info)


    def showError(self, msg):
        """show dialog with error message"""
        self.statusbar.SetStatusText(msg)
        dlg = wx.MessageDialog(self, message=msg, caption="Error", style=wx.OK|wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()


    def showPixelValueAt(self, pos):
        """set pixel position of mouse cursor"""
        value = ""
        if self.rgbeImg and self._showValues:
            r,g,b,v = self.rgbeImg.getRGBVAt(pos)
            if r > 0:
                value = "rgb=(%.3f,%.3f,%.3f)" % (r,g,b)
                if v > 0 and self.rgbeImg.isIrridiance():
                    value = "%s  value=%s lux" % (value,self.formatNumber(v)) 
            self.statusbar.SetStatusText("'%s':   x,y=(%d,%d)   %s" % (self.filename, pos[0],pos[1], value))


    def updatePicturePanel(self):
        """recreate BMP image"""
        try:
            ppm = self.rgbeImg.toPPM()
            io = cStringIO.StringIO(ppm)
            self.img = wx.ImageFromStream(io)
            self.picturepanel.setImage(self.img)
        except:
            if self.rgbeImg.error:
                msg = "Error creating falsecolor image:\n%s" % self.rgbeImg.error
                self.showError(msg)
            return
        self.picturepanel.Refresh()
   



if __name__ == "__main__":   
    try:
        app = wx.App(redirect = False)
        frame = wxFalsecolorFrame(sys.argv[1:])
        app.MainLoop()
    except Exception, e:
        traceback.print_exc()
        print "\npress return to close window ..."
        raw_input()

