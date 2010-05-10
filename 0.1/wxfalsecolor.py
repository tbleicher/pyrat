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
import wx
import wx.lib.foldpanelbar as fpb
from wx.lib.wordwrap import wordwrap

from falsecolor2 import FalsecolorImage


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
            #TODO: consider legend position
            if self.legendpos.startswith("left"):
                self.legendoffset = (self.legwidth,0)
            elif self.legendpos.startswith("top"):
                self.legendoffset = (0,self.legheight)


    def getRGBAt(self, pos):
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
        
    
    def getValueAt(self, pos):
        """Return Lux value at <pos> or -1 if no values are available"""
        if not self.isIrridiance():
            return -1
        else:
            r,g,b,v = self.getRGBAt(pos)
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
            self.showError(wxparent,msg)
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
                v = (0.265*r+0.67*g+0.065*b)*self.mult
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


    def showError(self, wxparent, msg):
        dlg = wx.MessageDialog(parent, message=msg, caption="Error", style=wx.OK|wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()
    

class FalsecolorControlPanel(wx.Panel):

    def __init__(self, parent, parentapp, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self.parentapp = parentapp
        self._buildFCButtons()

        self._cmdLine = ""


    def _buildFCButtons(self):
        """create control elements in grid layout"""
        #fcpanel.SetBackgroundColour(wx.BLUE)
        #fcsizer = wx.BoxSizer(wx.VERTICAL)
        
        ## type choice button
        self.fc_type = wx.Choice(self, wx.ID_ANY, choices=["color fill", "c-lines", "c-bands"])
        self.Bind(wx.EVT_CHOICE, self.updateFCButton, self.fc_type)
        
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
        self.doFCButton = wx.Button(self, wx.ID_ANY, label='falsecolor')
        self.doFCButton.Bind(wx.EVT_LEFT_DOWN, self.doFalsecolor)
        self.doFCButton.Disable()

        layout = [(self.fc_type,                                None),
                  (wx.Panel(self,wx.ID_ANY,size=(-1,10)),    None),
                  (wx.StaticText(self, wx.ID_ANY, "label:"), self.label),
                  (wx.StaticText(self, wx.ID_ANY, "scale:"), self.scale),
                  (wx.StaticText(self, wx.ID_ANY, "steps:"), self.steps),
                  (wx.Panel(self,wx.ID_ANY,size=(-1,10)),    None),
                  (self.fc_log,                                 self.logv),
                  (self.fc_mask,                                self.maskv),
                  (self.fc_col,                                 None),
                  (self.fc_extr,                                None),
                  (self.fc_zero,                                None),
                  (wx.Panel(self,wx.ID_ANY,size=(-1,10)),    None),
                  (wx.StaticText(self, wx.ID_ANY, "leg-w:"), self.legW),
                  (wx.StaticText(self, wx.ID_ANY, "leg-h:"), self.legH),
                  (wx.Panel(self,wx.ID_ANY,size=(-1,10)),    None),
                  (self.doFCButton,                             None),
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
        
        #fcsizer.Add(grid, proportion=1, flag=wx.EXPAND|wx.ALL, border=0)
        #self.SetSizer(fcsizer)
        self.SetSizer(grid)
        self.SetInitialSize()


    def doFalsecolor(self, event):
        if self.parentapp.rgbe2fc(event) == True:
            self._cmdLine = " ".join(self.getFCArgs())
            self.doFCButton.SetLabel("update")
            self.doFCButton.Disable()
        else:
            self.doFCButton.SetLabel("update")
            self.doFCButton.Enable()


    def updateFCButton(self, event):
        """set label of falsecolor button to 'update'"""
        if self._cmdLine != "":
            newCmd = " ".join(self.getFCArgs())
            if self._cmdLine != newCmd:
                self.doFCButton.SetLabel("update")
                self.doFCButton.Enable()
            else:
                self.doFCButton.Disable()
    

    def getFCArgs(self):
        """collect command line args as list"""
        args = []
        #args.extend(["-t", "./tempdir"])
        
        if self.fc_type.GetCurrentSelection() > 0:
            args.append(["", "-cl", "-cb"][self.fc_type.GetCurrentSelection()])

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
        if self.legW.GetValue() != "100":
            args.extend(["-lw", self.legW.GetValue()])
        if self.legH.GetValue() != "200":
            args.extend(["-lh", self.legH.GetValue()])

        return args        


    def setFCLabel(self, text):
        self.label.SetValue(text)


    def enableFC(self, text=""):
        self.doFCButton.Enable()
        if text != "":
            self.doFCButton.SetLabel(text)




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
        ## spacer
        spacer = wx.Panel(xipanel, wx.ID_ANY, size=(-1,5))
        xisizer.Add(spacer, proportion=0, flag=wx.EXPAND|wx.ALL, border=0)

        xipanel.SetSizer(xisizer)
        xipanel.SetInitialSize()
        return xipanel


    def OnAbout(self, event):
        self.parent.showAboutDialog()

    def OnCollapseMe(self, event):
        item = self.pnl.GetFoldPanel(0)
        self.pnl.Collapse(item)

    def OnExpandMe(self, event):
        self.pnl.Expand(self.pnl.GetFoldPanel(0))
        self.pnl.Collapse(self.pnl.GetFoldPanel(1))

    def OnShowValues(self, event):
        self.parent.setShowValues(self.showValues.GetValue())

    def setBarSize(self, event):
        size = event.GetSize()
        self.pnl.SetDimensions(0, 0, size.GetWidth(), size.GetHeight())
    
    
    def disableShowValues(self):
        self.showValues.SetValue(False)
        self.showValues.Disable()

    def enableShowValues(self,status=False):
        self.showValues.Enable()
        self.showValues.SetValue(status)

    def OnShowValues(self, event):
        self.parent.setShowValues(self.showValues.GetValue())

    
    def enableFC(self, text=""):
        self.fcpanel.enableFC(text)

    def getFCArgs(self):
        return self.fcpanel.getFCArgs()

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
	rgbeImg = RGBEImage(self, ["-i", path])
        rgbeImg.readImageData(path)
        if rgbeImg.error:
            msg = "Error loading image.\nFile: %s\nError: %s" % (path,rgbeImg.error)
            self.app.showError(msg)
        else:
            self.app.loadImage(path)
        


class ImagePanel(wx.Panel):

    def __init__(self, parent, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self.Bind(wx.EVT_SIZE, self.resizeImage)
        
        self.SetDropTarget(FileDropTarget(parent))
        
        self.parent = parent
        self.bmp = None
        self.img = None
        self._scale = 0
        self.size = self.GetSize()

    
    def reportPosition(self, evt):
        """return cursor (x,y) in pixel coords of self.img - (x,y) is 0 based!"""
        x,y = evt.GetPosition()
        x *= self._scale
        y *= self._scale
        self.parent.showPixelValueAt( (int(x),int(y)) )
        
    
    def resizeImage(self, evt):
        """scale image to fit frame proportionally"""
        self.size = evt.GetSize()
        self.scaleImage()
    
    
    def setBitmap(self):
        """convert scale image to new bitmap graphic"""
        if self.bmp:
            self.bmp.Destroy()
        self.bmp = wx.StaticBitmap(self,wx.ID_ANY,wx.BitmapFromImage(self._scaledImg))
        self.bmp.Bind(wx.EVT_MOTION, self.reportPosition)


    def setImage(self, img):
        """set wx.Image"""
        self.img = img
        self.scaleImage()
        self.Update()


    def scaleImage(self):
        """scale image to fit frame"""
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
                self.setBitmap()
            self.Refresh()
    


class ImageFrame(wx.Frame):

    def __init__(self, args=[]):
        wx.Frame.__init__(self,None,title = "wxImage - Radiance Picture Viewer")
        
        ## menu
        self._addMenu()
        ## image display
        self.picturepanel = ImagePanel(self,style = wx.SUNKEN_BORDER)

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
        print "TEST: cmd line args:"
        for i,arg in enumerate(args):
            print "     ", i, arg
        ## -i <path> is added by loadFile, so remove path and option now
        if "-i" in args:
            idx = args.index("-i")
            try:
                path = args[idx+1]
                if os.path.isfile(path):
                    del args[idx:idx+2]
                    return (path, args)
            except IndexError:
                del args[idx]
                return ("", args)
        
        ## path is only argument (drag-n-drop)
        if len(args) == 1 and os.path.isfile(args[-1]):
	    path = args.pop()
	    args = []
            return (path,args)

        else:
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

    def reset(self):
        self._array = []
        self._arrayTrue = False
        self._showValues = False
        self.controls.enableShowValues()

    def loadImage(self, path, args=[]):
        """create instance of falsecolor image from <path>"""
        print "TEST load Image:", path
        self.reset()
        self.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))
	#self.rgbeImg = RGBEImage(self, sys.argv[1:] + ["-t", "./tempdir"])
	self.rgbeImg = RGBEImage(self, ["-i", path] + args)
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
            self.controls.enableFC("convert")
        self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))


    def onLoadImage(self,event):
        """load new Radiance RGBE image"""
        filedialog = wx.FileDialog(self,
                          message = 'Choose an image to open',
                          defaultDir = '',
                          defaultFile = '',
                          wildcard = 'HDR files|*.hdr|PIC files|*.pic|all files |*.*',
                          style = wx.OPEN)
        if filedialog.ShowModal() == wx.ID_OK:
            path = filedialog.GetPath()
            self.loadImage(path)


    def onQuit(self, event):
        """hasta la vista"""
        self.Close()


    def onSaveImage(self,event):
        """save bmp image to file"""
        dirname, filename = os.path.split(self.path)
        filebase = os.path.splitext(filename)[0]
        filedialog = wx.FileDialog(self,
                          message = 'save image',
                          defaultDir = dirname,
                          defaultFile = filebase + '_fc.hdr',
                          wildcard = 'HDR file|*.hdr|BMP file|*.bmp|PPM file|*.ppm|TIF file|*.tif|PIC (old)|*.pic',
                          style = wx.SAVE)
        if filedialog.ShowModal() == wx.ID_OK:
            path = filedialog.GetPath()
            result = self.rgbeImg.saveToFile(path)
            if result != True:
                msg = "Error saving image:\n" + self.rgbeImg.error
                self.showError(msg)


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
        info.Version = "0.1 (rREV)"     # placeholder for build script 
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
            r,g,b,v = self.rgbeImg.getRGBAt(pos)
            if r > 0:
                value = "rgb=(%.3f,%.3f,%.3f)" % (r,g,b)
                if v > 0 and self.rgbeImg.isIrridiance():
                    if v < 1:
                        value = "%s  value=%.3f lux" % (value,v) 
                    elif v < 10:
                        value = "%s  value=%.2f lux" % (value,v) 
                    elif v < 100:
                        value = "%s  value=%.1f lux" % (value,v) 
                    else:
                        value = "%s  value=%d lux" % (value,v) 

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
        frame = ImageFrame(sys.argv[1:])
        app.MainLoop()
    except Exception, e:
        import traceback
        traceback.print_exc()
        print "\npress return to close window ..."
        raw_input()
