
import os
import urllib2
import time
from HTMLParser import HTMLParser

import wx


URL_WXFALSECOLOR = "http://code.google.com/p/pyrat/downloads/detail?name=wxfalsecolor.exe"



class IncrementalDownloader(object):
    
    def __init__(self, url, dlg=None):
        
        self._url = url
        self._dlg = dlg
        self._content_length = 0


    def update_dialog(self, bytes_so_far):
        """update progress bar to percentage of download"""
        if self._content_length != 0:
            percent = float(bytes_so_far) / self._content_length
            percent = round(percent*100, 2)
        else:
            return

        if self._dlg:
            (keepGoing, foo) = self._dlg.Update(percent, "download status: %d%%" % percent)
            print "TEST Downloaded %d of %d bytes (%0.2f%%)\n" % (bytes_so_far, self._content_length, percent)
            return keepGoing

        else:
            print "Downloaded %d of %d bytes (%0.2f%%)\n" % (bytes_so_far, self._content_length, percent)
            return True


    def chunk_read(self, response, chunk_size=250000):
        """retrieve download file in small bits and report progress"""
        bytes_so_far = 0
        data = ""
        keepGoing = True

        while keepGoing:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            bytes_so_far += len(chunk)
            data += chunk
            keepGoing = self.update_dialog(bytes_so_far)
        
        ## finally return data
        return data


    def download(self):
        print "TEST: start incremental download or", self._url
        response = urllib2.urlopen(self._url)
        content_length = response.info().getheader('Content-Length').strip()
        self._content_length = int(content_length)
        print "TEST: self._content_length=", self._content_length
        data = self.chunk_read(response)
        print "TEST: data = %d bytes" % len(data)
        return data, self._content_length 



class DownloadParser(HTMLParser):
    """parses the project's wxfalsecolor.exe download site"""

    def __init__(self, dfmt=""):
        
        HTMLParser.__init__(self)
        
        self._box_inner = False
        self._pagetitle = False
        self._tableheader = False
        self._expect_date = False
        self._expectDownload = False
        self._expect_description = False
        self._dateFormat = dfmt if dfmt != "" else "%a %b %d %H:%M:%S %Y"
        
        ## the things we need to find in page
        self.downloadLink = None
        self.filesize = None
        self.filename = "wxfalsecolor.exe"
        self.uploadedDate = None
        self.struct_time = None
        self.description = None
        self.version = None


    def _getDateFromAttributes(self, attrs):
        """extract the uploaded time stamp from 'title' attribute"""
        datestamp = "Thu Jan 1 00:00:00: 2000"
        for k,v in attrs:
            if k == "title": datestamp = v
        try:
            ## format: Thu Jan 13 12:29:20 2011
            self.struct_time = time.strptime(datestamp, self._dateFormat)
            self.uploadedDate = datestamp
        except ValueError:
            pass
        self._expect_date = False
   

    def getDetailsDict(self):
        """return dict with download details"""
        return {'url' :         self.downloadLink,
                'description' : self.description,
                'date' :        self.uploadedDate,
                'struct_time' : self.struct_time,
                'version' :     self.version,
                'filesize' :    self.filesize,
                'filename' :    self.filename}
   

    def _getVersionFromTitle(self, data):
        """extract version number from page title (upload summary)"""
        words = data.split()
        if "version" in words:
            try:
                self.version = float(words[words.index("version")+1])
            except:
                pass


    def handle_starttag(self, tag, attrs):
        """set attributes depending on html context"""
        
        ## summary (for version) is part of the title
        if tag == "title":
            self._pagetitle = True
        
        ## description is in <pre> tag
        elif tag == "pre":
            self._in_pre = True
        
        ## div for download link and file size 
        elif tag == "div":
            for k,v in attrs:
                if k == "class" and v == "box-inner":
                    self._box_inner = True
        
        ## important fields are preceeded by <th>
        elif tag == "th":
            self._tableheader = True

        ## upload date is the 'title' attribute of a <span>
        elif tag == "span" and self._expect_date:
            self._getDateFromAttributes(attrs)
            
        ## download links
        elif tag == "a" and self._box_inner:
            for k,v in attrs:
                if k == "href":
                    self.downloadLink = v
                    self._expectDownload = False


    def handle_endtag(self, tag):
        """reset context attributes"""
        if tag == "th":
            self._tableheader = False
        elif tag == "title":
            self._pagetitle = False
        elif tag == "pre":
            self._in_pre = False
        elif tag == "span":
            self._expect_date = False
        elif tag == "div":
            if self._box_inner:
                self._box_inner = False


    def handle_data(self, data):
        """process text information"""

        ## skip layout only tags (plenty of those)
        data = data.strip()
        if data == "":
            return
        
        ## file size from main download box
        if self._box_inner == True:
            if data.endswith("exe"):
                self.filename = data
            else:
                self.filesize = data
        
        ## set next attribute based on header text
        if self._tableheader:
            if data == "Uploaded:":
                self._expect_date = True
            elif data == "Description:":
                self._expect_description = True
            elif data == "File:":
                self._expectDownload = True
        
        ## check length of data to find download description
        elif self._expect_description and self._in_pre:
            self.description = data
            self._expect_description = False
        
        elif self._pagetitle:
            self._getVersionFromTitle(data)


    def hasData(self):
        """return True if all info fields were found"""
        if self.downloadLink == None:
            return False
        if self.uploadedDate == None:
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
                details.get('description', "no description available"),
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
        for header,value in [
                ("version:",     details.get('version', "n/a")),
                ("upload date:", details.get('date', "n/a")),
                ("size (Mb):",   details.get('filesize', "n/a")),
                ("description:", "")]:

            box = wx.BoxSizer(wx.HORIZONTAL)
            label1 = wx.StaticText(self, wx.ID_ANY, header, size=(85,-1))
            label1.SetFont(font_bold)
            box.Add(label1, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
            label2 = wx.StaticText(self, wx.ID_ANY, str(value), size=(150,-1))
            box.Add(label2, 1, wx.ALIGN_CENTRE|wx.ALL, 5)
            sizer.Add(box, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT, 10)





class UpdateManager(object):

    def __init__(self, date, url, format=""):
        
        self._parser = DownloadParser(format)
        self.date = date
        self.error = None
        self.parent = None
        self.url = url
        self.text = ""
        

    def getDownloadPage(self):
        """try to retrieve wxfalsecolor.exe download page"""
        try:
            page = urllib2.urlopen(self.url)
            self.text = page.read()
            page.close()
            print "have text", len(self.text)
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
        else:
            return self._parser.getDetailsDict()
   

    def showDetails(self):
        for k,v in self._parser.getDetailsDict().items():
            print "%11s : %s" % (k, str(v)[:60])
        

    def showDialog(self, parent):
        """show dialog according to update availability"""
        self.parent = parent
        available = self.updateAvailable()
        if available == True:
            details = self.getDownloadDetails()
            self._showDetailsDialog(details)
        elif self.error:
            self._showErrorDialog()
        else:
            self._showInfoDialog("No new updates available.", "Try again in a few weeks.")
    

    def _showDetailsDialog(self, details):
        """show dialog with details of the download file"""
        dlg = UpdateDetailsDialog(self.parent, details)
        dlg.CenterOnScreen()
        val = dlg.ShowModal()
        if val == wx.ID_OK:
            self.showFileSelector(details)
        else:
            print "skipping download"


    def _showErrorDialog(self, title="Error during update!"):
        """show error message dialog"""
        dlg = wx.MessageDialog(self.parent,
            "error message:\n%s" % self.error,
            title, 
            wx.OK|wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()
    

    def showFileSelector(self, details):
        """on download show a file selector to save data to"""
        filedialog = wx.FileDialog(self.parent,
                          message = 'save download',
                          defaultDir = os.getcwd(),
                          defaultFile = details.get("filename", "wxfalsecolor.exe"),
                          style = wx.SAVE)
        
        if filedialog.ShowModal() == wx.ID_OK:
            path = filedialog.GetPath()
            self.startDownload(path, details)
            if not self.error:
                self._showInfoDialog("Download completed.", 
                        "Enjoy the new version.\nfilepath: '%s'" % path)
        else:
            print "skipping download"
        
    
    def _showInfoDialog(self, title="title line", info="info line"):
        """show error message dialog"""
        dlg = wx.MessageDialog(self.parent,
                info,
                title, 
                wx.OK|wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
    

    def startDownload(self, path, details):
        """illustrate download with progress bar dialog"""
        print "TODO: start download with progress bar ..."
        
        filename = details.get("filename", "UNKNOWN")
        url = details['url'] 

        dlg = wx.ProgressDialog("downloading file '%s'" % details.get("filename", "unknown"),
                                "download status: 0%",
                                maximum = 101,
                                parent = self.parent,
                                style = wx.PD_APP_MODAL|wx.PD_CAN_ABORT|wx.PD_ELAPSED_TIME)
        
        indl = IncrementalDownloader(url, dlg)
        data, size = indl.download()
        dlg.Destroy()

        if data and len(data) == size:
            self.saveData(data, path)

        elif data and len(data) != size:
            self.error = "download file incomplete"
            _showErrorDialog(self,
                    title="Error during download!",
                    info="Download file is incomplete.\nPlease try again another time.")


    def saveData(self, data, path):
        """write downloaded data out to file"""
        try:
            f = file(path, "wb")
            f.write(data)
            f.close()
        except Exception, err:
            self.error = str(err)
            if self.parent:
                self._showErrorDialog(self, "Error saving file!")


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


