
import os
import urllib2
import time
from HTMLParser import HTMLParser

import wx


URL_WXFALSECOLOR = "http://code.google.com/p/pyrat/downloads/detail?name=wxfalsecolor.exe"

URL_TESTFILE = "./tests/data/code.google.html"

class DownloadParser(HTMLParser):
    """parses the project's wxfalsecolor.exe download site"""

    def __init__(self, dfmt=""):
        
        HTMLParser.__init__(self)

        self._tableheader = False
        self._expectDate = False
        self._expectDownload = False
        self._expectDescription = False
        self._dateFormat = dfmt if dfmt != "" else "%a %b %d %H:%M:%S %Y"
        
        ## the things we need to find in page
        self.downloadLink = None
        self.uploadedDate = None
        self.struct_time = None
        self.description = None


    def handle_starttag(self, tag, attrs):
        """set attributes depending on html context"""
        
        ## important fields are preceeded by <th>
        if tag == "th":
            self._tableheader = True

        ## upload date is the 'title' attribute of a <span>
        elif tag == "span" and self._expectDate:
            for k,v in attrs:
                if k == "title":
                    try:
                        ## format: Thu Jan 13 12:29:20 2011
                        s = time.strptime(v, self._dateFormat)
                        self.struct_time = s
                        self.uploadedDate = v
                    except ValueError:
                        pass
                    self._expectDate = False
        
        ## download links
        elif tag == "a" and self._expectDownload:
            for k,v in attrs:
                if k == "href" and v.endswith("wxfalsecolor.exe"):
                    self.downloadLink = v
                    self._expectDownload = False


    def handle_endtag(self, tag):
        """reset context attributes"""
        if tag == "th":
            self._tableheader = False

        elif tag == "span":
            self._expectDate = False


    def handle_data(self, data):
        """process text information"""

        ## skip layout only tags (plenty of those)
        data = data.strip()
        if data == "":
            return
        
        ## set next attribute based on header text
        if self._tableheader:
            if data == "Uploaded:":
                self._expectDate = True
            elif data == "Description:":
                self._expectDescription = True
            elif data == "File:":
                self._expectDownload = True
        
        ## check length of data to find download description
        elif self._expectDescription:
            if len(data) > 100:
                self.description = data
                self._expectDescription = False
   

    def hasData(self):
        """return True if all info fields were found"""
        if self.downloadLink == None:
            return False
        if self.uploadedDate == None:
            return False
        if self.description == None:
            return False
        return True


    def isUpdate(self, testdate):
        """return True if testdate is older than upload date"""
        if not self.hasData():
            return False
        if type(testdate) == type(""):
            testdate = time.strptime(testdate, self._dateFormat)
        if isinstance(testdate, time.struct_time):
            return testdate < self.struct_time
       

    def printData(self):
        print "Uploaded:\n  ", self.uploadedDate
        print "download:\n  ", self.downloadLink
        print "Descript:\n  ", self.description[:70], "..."
    

    def setFormat(self, format):
        """set format to use to parse date string"""
        self._dateFormat = dateformat



class UpdateDetailsDialog(wx.Dialog):
    """this dialog shows details of the available update"""

    def __init__(self, parent, details, id=wx.ID_ANY, title="update details"):
        wx.Dialog.__init__(self, parent, id, title)
        
        ## layout
        sizer = self.layout(details)
        self.SetSizer(sizer)
        sizer.Fit(self) 
    
    
    def layout(self, details):
        """create layout of text fields and buttons"""

        sizer = wx.BoxSizer(wx.VERTICAL)
        
        ## title
        label = wx.StaticText(self, -1, "Download details for wxfalsecolor.exe")
        font_big = wx.Font(16, wx.SWISS, wx.NORMAL, wx.BOLD)
        label.SetFont(font_big)
        sizer.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 15)
        
        ## grid of title - value fields
        self._layoutLabels(sizer, details)
        
        ## description text box
        text = wx.TextCtrl(self, wx.ID_ANY, 
                details.get('description', ""),
                size=(400,200),
                style=wx.TE_MULTILINE)
        sizer.Add(text, 0, wx.ALIGN_CENTRE|wx.LEFT|wx.RIGHT, 15)
        
        ## divider
        line = wx.StaticLine(self, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.LEFT|wx.RIGHT, 10)

        ## bottom row 
        stretch = wx.StaticText(self, wx.ID_ANY, "")
        skip = wx.Button(self, wx.ID_CANCEL, "not now")
        dload = wx.Button(self, wx.ID_OK, "download")
        dload.SetDefault()
        
        btnsizer = wx.BoxSizer(wx.HORIZONTAL)
        btnsizer.Add(stretch, 1, wx.EXPAND|wx.ALL, 5)
        btnsizer.Add(skip,    0, wx.EXPAND|wx.ALL, 5)
        btnsizer.Add(dload,   0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(btnsizer, 1, wx.EXPAND|wx.ALL, 10)

        return sizer


    def _layoutLabels(self, sizer, details):
        """create text labels for keys in details dict"""
        font_bold = wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD)
        for header,text in [
                ("version:",     details.get('version', "n/a")),
                ("upload date:", details.get('date', "n/a")),
                ("size (Mb):",   details.get('filesize', "n/a")),
                ("description:", "")]:

            box = wx.BoxSizer(wx.HORIZONTAL)
            label1 = wx.StaticText(self, wx.ID_ANY, header, size=(85,-1))
            label1.SetFont(font_bold)
            box.Add(label1, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
            label2 = wx.StaticText(self, wx.ID_ANY, text, size=(150,-1))
            box.Add(label2, 1, wx.ALIGN_CENTRE|wx.ALL, 5)
            sizer.Add(box, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT, 10)



class UpdateManager:

    def __init__(self, date, url, format=""):
        
        self._parser = DownloadParser(format)
        self.date = date
        self.url = url
        self.error = None
        self.text = ""


    def getDownloadPage(self):
        """try to retrieve wxfalsecolor.exe download page"""
        try:
            page = urllib2.urlopen(self.url)
            self.text = page.read()
            page.close()
            return True
        except urllib2.HTTPError, err:
            self.error = str(err)
            return False
        except urllib2.URLError, err:
            self.error = err.reason
            return False


    def parseText(self, text=""):
        """process contents of html page"""
        if text == "":
            text = self.text
        self._parser.feed(text)
        self._parser.close()


    def getDownloadDetails(self):
        """return download details as dict""" 
        if not self._parser.hasData():
            return {}
        return {'url' :         self._parser.downloadLink,
                'description' : self._parser.description,
                'date' :        self._parser.uploadedDate,
                'struct_time' : self._parser.struct_time}
    

    def showDialog(self, parent):
        """show dialog according to update availability"""
        available = self.updateAvailable()
        if available == True:
            details = self.getDownloadDetails()
            self._showDetailsDialog(parent, details)
        elif self.error:
            self._showErrorDialog(parent)
        else:
            self._showNoUpdatesDialog(parent)
    

    def _showDetailsDialog(self, parent, details):
        """show dialog with details of the download file"""
        for k,v in details.items():
            print "%11s : %s" % (k, str(v)[:60])
        
        dlg = UpdateDetailsDialog(parent, details)
        dlg.CenterOnScreen()
        val = dlg.ShowModal()
        if val == wx.ID_OK:
            print "TODO: start download ..."
        else:
            print "skipping download"


    def _showErrorDialog(self, parent):
        """show error message dialog"""
        dlg = wx.MessageDialog(parent,
            "error message:\n%s" % self.error,
            "Error during update!", 
            wx.OK|wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()
    

    def _showNoUpdatesDialog(self, parent):
        """show error message dialog"""
        dlg = wx.MessageDialog(parent,
            "Try again in a few weeks.",
            "No new updates available.", 
            wx.OK|wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
            

    def updateAvailable(self, date=None):
        """check if uploaded date is newer than release date"""
        if self.error:
            return False
        if self.text == "":
            self.getDownloadPage()
            self.parseText()
        if not date:
            date = self.date
        return self._parser.isUpdate(date)



class wxUpdaterTestFrame(wx.Frame):

    def __init__(self, parent=None, id=-1, title="updater test frame"):
        wx.Frame.__init__(self, parent, id, title, size=wx.Size(150,150))
        self.Show()

        ## 'no update' button
        noupdate = wx.Button(self, wx.ID_ANY, 'no update', (20,10) )
        noupdate.Bind(wx.EVT_LEFT_DOWN, self.onNoUpdate)
        
        ## 'update' button
        updateb = wx.Button(self, -1, 'update', (20,40) )
        updateb.Bind(wx.EVT_LEFT_DOWN, self.onUpdate)
        
        ## 'update error' button
        update_err = wx.Button(self, -1, 'update error', (20,70) )
        update_err.Bind(wx.EVT_LEFT_DOWN, self.onUpdateError)
        
        ## 'quit' button
        quitbutton = wx.Button(self, wx.ID_EXIT, 'quit', (20,100) )
        quitbutton.Bind(wx.EVT_LEFT_DOWN, self.onQuit)

    def onNoUpdate(self, evt):
        print "\nstarting update (no update) ... URL_TESTFILE"
        fileurl = "file://%s" % os.path.abspath(URL_TESTFILE)
        RELEASE_DATE = "Fri Jan 14 12:29:20 2011" #XXX
        um = UpdateManager(date=RELEASE_DATE, url=fileurl)
        um.showDialog(self)
    
    def onUpdate(self, evt):
        print "\nstarting update ... URL_TESTFILE"
        fileurl = "file://%s" % os.path.abspath(URL_TESTFILE)
        RELEASE_DATE = "Wed Jan 12 12:29:20 2011" #XXX
        um = UpdateManager(date=RELEASE_DATE, url=fileurl)
        um.showDialog(self)
        self.Close()

    def onUpdateError(self, evt):
        print "\nstarting update (error) ... URL_TESTFILE"
        fileurl = "file://%s" % os.path.abspath(URL_TESTFILE)
        RELEASE_DATE = "Thu Jan 13 12:29:20 2011" #XXX
        um = UpdateManager(date=RELEASE_DATE, url=fileurl+"foo")
        um.showDialog(self)
        
    
    def onQuit(self, evt):
        self.Close()



def cmdtest():
        
    text = file(URL_TESTFILE, "r").read()

    parser = DownloadParser()
    parser.feed(text)
    parser.close()

    if parser.hasData():
        parser.printData()
        print "\nisUpdate()"
        print "  isUpdate -1 (expect False):", parser.isUpdate("Wed Jan 12 12:29:20 2011")
        print "  isUpdate  0 (expect False):", parser.isUpdate("Thu Jan 13 12:29:20 2011")
        print "  isUpdate +1 (expect True): ", parser.isUpdate("Fri Jan 14 12:29:20 2011")
        
    print "\n"
    fileurl = "file://%s" % os.path.abspath(URL_TESTFILE)

    print "TEST: same day (older) ",
    um = UpdateManager(date="Thu Jan 13 12:29:20 2011", url=fileurl)
    print "  update available:", um.updateAvailable()

    print "TEST: date -1 (older)  ",
    print "  update available:", um.updateAvailable("Wed Jan 12 12:29:20 2011")

    print "TEST: date +1 (younger)",
    print "  update available:", um.updateAvailable("Fri Jan 14 12:29:20 2011")
    print "\n"

    for k,v in um.getDownloadDetails().items():
        print "%11s : %s" % (k, str(v)[:60])




if __name__ == '__main__':
    #cmdtest()
    app = wx.App(redirect = False)
    frame = wxUpdaterTestFrame()
    frame.onUpdate(-1)
    app.MainLoop()




