##
## controlpanels.py - part of wxfalsecolor
##
## $Id$
## $URL$

import wx
import wx.lib.foldpanelbar as fpb
import wx.lib.buttons as buttons

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


class MyFoldPanelBar(fpb.FoldPanelBar):
    """base for FoldPanelBar in controlls panel"""
    
    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, *args,**kwargs):
        fpb.FoldPanelBar.__init__(self, parent, id, pos, size, *args, **kwargs)

    def OnPressCaption(self, event):
        """collapse all other panels on EVT_CAPTIONBAR event"""
        fpb.FoldPanelBar.OnPressCaption(self, event)
        for i in range(self.GetCount()):
            p = self.GetFoldPanel(i)
            if p != event._tag:
                self.Collapse(p)


class FoldableControlsPanel(wx.Panel):
    """combines individual feature panels"""
    
    def __init__(self, parent, style=wx.DEFAULT_FRAME_STYLE):

        wx.Panel.__init__(self, parent, id=wx.ID_ANY)
        self.parent = parent
        self.SetSize((130,350))
        self.CreateFoldBar()
        self.Bind(wx.EVT_SIZE, self.setBarSize)
    

    def CreateFoldBar(self, vertical=True):
                           
        bar = MyFoldPanelBar(self, style=fpb.FPB_DEFAULT_STYLE|fpb.FPB_VERTICAL)

        item = bar.AddFoldPanel("ximage", collapsed=False)
        pc_controls = self._buildXimageButtons(item)
        bar.AddFoldPanelWindow(item, pc_controls, flags=fpb.FPB_ALIGN_WIDTH)
        
        item = bar.AddFoldPanel("falsecolor", collapsed=True)
        self.fcpanel = FalsecolorControlPanel(item, self.parent)
        bar.AddFoldPanelWindow(item, self.fcpanel, flags=fpb.FPB_ALIGN_WIDTH)
        
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
        """creates layout of ximage buttons"""
        xipanel = wx.Panel(panel,wx.ID_ANY,size=(-1,35))
        xisizer = wx.BoxSizer(wx.VERTICAL)
        
        self.showValues = wx.CheckBox(xipanel, wx.ID_ANY, "show values")
        self.showValues.Bind(wx.EVT_CHECKBOX, self.OnShowValues)
        self.showValues.Disable()
        xisizer.Add(self.showValues, proportion=0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=5)
        
        clearButton = wx.Button(xipanel, wx.ID_ANY, "clear labels")
        clearButton.Bind(wx.EVT_BUTTON, self.OnClearLabels)
        xisizer.Add(clearButton, proportion=0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=5)
        
        ## spacer
        spacer = wx.Panel(xipanel, wx.ID_ANY, size=(-1,5))
        xisizer.Add(spacer, proportion=0, flag=wx.EXPAND|wx.ALL, border=0)

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


