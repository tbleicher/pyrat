#!/usr/bin/env python

## wxfalsecolor.py - main file of wxfalsecolor
##
## $Id$
## $URL$

import os
import traceback
import wx


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
from wx.lib.wordwrap import wordwrap

from rgbeimage import RGBEImage, WX_IMAGE_FORMATS, WX_IMAGE_WILDCARD
from controlpanels import FoldableControlsPanel
from imagepanel import ImagePanel


DEBUG = 0



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
        self._foldpanel = FoldableControlsPanel(self, wx.ID_ANY)
        self.fccontrols = self._foldpanel.fccontrols
        self.displaycontrols = self._foldpanel.displaycontrols
        self.panelSizer.Add(self._foldpanel, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        
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
            self.updatePicturePanel()
            if self.img:
                self.path = path
                self.filename = os.path.split(path)[1]
            if self.rgbeImg.isIrridiance():
                self.fccontrols.setFCLabel("Lux")
            self.saveButton.Enable()
            self.fccontrols.enableFC("convert fc")
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
        self.displaycontrols.reset()
        self.picturepanel.clearLabels()


    def rgbe2fc(self,event):
        """convert Radiance RGBE image to wx.Bitmap"""
        self.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))
        args = self.fccontrols.getFCArgs()
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


    def loadValues(self):
        """load luminance/illuminance data from image"""
        return self.rgbeImg.hasArrayData(self)


    def showAboutDialog(self):
        """show dialog with license etc"""
        info = wx.AboutDialogInfo()
        info.Name = "wxfalsecolor"
        info.Version = "v0.2 (rREV)"     # placeholder for build script 
        info.Copyright = "(c) 2010 Thomas Bleicher"
        info.Description = "cross-platform GUI frontend for falsecolor"
        info.WebSite = ("http://sites.google.com/site/tbleicher/radiance/wxfalsecolor", "wxfalsecolor home page")
        info.Developers = ["Thomas Bleicher", "Axel Jacobs"]
        lines = [" ".join(line.split()) for line in LICENSE.split("\n\n")]
        info.License = wordwrap("\n\n".join(lines), 500, wx.ClientDC(self))
        wx.AboutBox(info)


    def showError(self, msg):
        """show dialog with error message"""
        self.statusbar.SetStatusText(msg)
        dlg = wx.MessageDialog(self, message=msg, caption="Error", style=wx.OK|wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    
    def showHeaders(self):
        """display image headers in popup dialog"""
        if not self.rgbeImg:
            return
        header = self.rgbeImg.getHeader()
        if header == False:
            self.showError("Image header not available!")
            return
        header2 = self.rgbeImg.getDataHeader()
        if header2 and header != header2:
            header += "\n\ncurrent:\n\n"
            header += header2
        
        #XXX use StaticText to avoid line wrap and for highlight
        dlg = wx.MessageDialog(self, message=header, caption="Image Header", style=wx.OK|wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()


    def showPixelValueAt(self, pos):
        """set pixel position of mouse cursor"""
        value = ""
        if self.rgbeImg:
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
            self.picturepanel.rgbeImg = self.rgbeImg
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

