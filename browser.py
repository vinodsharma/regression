#!/usr/bin/env python
#
# vim:ts=4:sw=4:expandtab
######################################################################

"""Worker task: does the actual browsing work."""

import gtk
import sys
import pywebkitgtk as webkit
import random
from datetime import datetime
from datetime import timedelta
import time
import os
import getopt
import argparse
import uuid
import logging
from collections import deque
from logging import *
import gobject
import signal
import urlparse

class TimeoutException(Exception): 
    pass 

def randstr(l = 32):
    return "".join(["%.2x" % random.randint(0, 0xFF) for i in range(l/2)])

class DOMWalker:
    def __init__(self, branch_factor):
        self.__indent = 0
        self.branch_factor = branch_factor
        self.child_urls = []

    def __dump(self, node):
        i = 0
        #print >> sys.stderr,  " "*self.__indent, node.__class__.__name__
        if node.nodeName == "A" and self.branch_factor > 0:
            #print >> sys.stderr,  " "*self.__indent, node.__class__.__name__
            if node.hasAttribute("href") and  node.__getattribute__("href").find("http") != -1:
                #print >> sys.stderr,  "  "*self.__indent, node.__getattribute__("href")
                urlval = node.__getattribute__("href")
                self.child_urls.append(urlval)
                #print >> sys.stderr,  "  "*self.__indent, "http://safly-beta.dyndns.org/?q="+node.__getattribute__("href")
                #print >> sys.stderr,  "  "*self.__indent, node.nodeName
                self.branch_factor -= 1

    def walk_node(self, node, callback = None, *args, **kwargs):
        if callback is None:
            callback = self.__dump

        callback(node, *args, **kwargs)
        self.__indent += 1
        children = node.childNodes
        for i in range(children.length):
            child = children.item(i)
            self.walk_node(child, callback, *args, **kwargs)
            self.__indent -= 1


class Browser():
    def __init__(self, branch_factor=0, verbose_output=False, no_proxy=False, css_loadtime=1.5):
        self.branch_factor = branch_factor
        self.verbose_output = verbose_output
        self.css_loadtime = css_loadtime
        #to indicate that it is a no proxy browser
        self.no_proxy = no_proxy
        self.__bid = randstr(16)
        self.__webkit = webkit.WebView()
        self.__webkit.SetConsoleMessageCallback(self._console_message)
        self.__webkit.SetScriptAlertCallback(self._script_alert)
        self.__webkit.SetDocumentLoadedCallback(self._DOM_ready)
        self.result = None
        self.tid = None
        self.timed_out = None
        info("Spawned new browser " + str(self.__bid))

    def __del__(self):
        pass

    def __timeout_callback(self):
        debug("Timeout Callback")
        if gtk.main_level() > 0:
            gtk.mainquit()
        # Set a flag so that the main thread knows to raise a
        # TimeoutException.
        self.timed_out = True
        # CAUTION: don't raise a TimeoutException here as we are in GTK
        # thread context. An exception raised here will not be seen by
        # the primary thread.
        # Don't do this: raise TimeoutException

    #if loading a page taked more than timeout miliseconds
    #visit will timout. Default timeout value is 5000
    def visit(self, url, timeout=5):
        info("Visiting URL: " + url)
        document = self.__webkit.GetDomDocument()
        document.title = " - LOADING"
        timeout_ms = timeout*1000
        self.timed_out = False
        self.tid = gobject.timeout_add(timeout_ms, self.__timeout_callback)
        self.pageLoaded = False
        if self.no_proxy:
            self.dom_loaded =False
        self.__webkit.LoadDocument(url)
        
        # we are waiting for image loader to appear
        # dont decrease this value
        self.gtk_sleep(500)
      
        # wait for page to get load
        # if browser is no proxy browser then wait for 
        # dom to get loaded
        # else we wait for loading image from proxy to get 
        # disappeared
        info("Waiting For Page to Get Loaded")
        if self.no_proxy:
            while not self.dom_loaded:
                self.gtk_sleep(100)
                if self.timed_out:
                    break;
        else:
            while self.checkDiv():
                self.gtk_sleep(100)
                if self.timed_out:
                    break;
        # wait time for stylesheet to get loaded
        self.gtk_sleep(self.css_loadtime*1000)
        # Disable the timeout
        if self.tid:
            gobject.source_remove(self.tid)
            self.tid = None
        if self.timed_out:
            raise TimeoutException
        else:
            return True

    def url(self):
        window = self.__webkit.GetDomWindow()
        return window.location.href

    def _DOM_node_inserted(self, event):
        target = event.target
        # target can be: Element, Attr, Text, Comment, CDATASection,
        # DocumentType, EntityReference, ProcessingInstruction
        parent = event.relatedNode
        #print >> sys.stderr,  "NODE INSERTED", target, parent

    def _DOM_node_removed(self, event):
        target = event.target
        # target can be: Element, Attr, Text, Comment, CDATASection,
        # DocumentType, EntityReference, ProcessingInstruction
        parent = event.relatedNode
        #print >> sys.stderr,  "NODE REMOVED", target, parent

    def _DOM_node_attr_modified(self, event):
        target = event.target
        # target can be: Element
        name = event.attrName
        change = event.attrChange
        newval = event.newValue
        oldval = event.prevValue
        parent = event.relatedNode
        #print >> sys.stderr,  "NODE ATTR MODIFIED", target, name, change, newval, oldval, parent

    def _DOM_node_data_modified(self, event):
        target = event.target
        # target can be: Text, Comment, CDATASection, ProcessingInstruction
        parent = event.target.parentElement
        newval = event.newValue
        oldval = event.prevValue
        #print >> sys.stderr,  "NODE DATA MODIFIED", target, newval, oldval, parent
        #print >> sys.stderr,  dir(target)
        #print >> event.target.getElementsByTagName('div').nodeName
        #print >> event.target.attributes[0].nodeName
        node=event.target.parentElement
        #print target.textContent
        #print target.parentElement.attributes.length

        if node.attributes:
            for i in range(node.attributes.length):
                attribute = node.attributes.item(i)
                attrName = attribute.nodeName
                attrValue = attribute.nodeValue
                #print attrName, "-->", attrValue
                if attrName == "name" and attrValue == "is_loaded":
                    #print node.innerHTML;
                    #print target.textContent
                    if node.innerHTML == "1":
                        self._is_Page_Loaded()

        #print dir(event.target)

    def _DOM_ready(self):
        document = self.__webkit.GetDomDocument()
        window = self.__webkit.GetDomWindow()
        document.addEventListener('DOMNodeInserted', self._DOM_node_inserted,
                                        False)
        document.addEventListener('DOMNodeRemoved', self._DOM_node_removed,
                                        False)
        document.addEventListener('DOMAttrModified', self._DOM_node_attr_modified,
                                        False)
        document.addEventListener('DOMCharacterDataModified', self._DOM_node_data_modified,
                                        False)
        print >> sys.stderr,  "URL:", document.URL
        print >> sys.stderr,  "Title:", document.title
        print >> sys.stderr,  "Cookies:", document.cookie
        if self.no_proxy:
            self.dom_loaded =True


    def JsMouseClickEvent(self,elemid,timeout=5):
        oldURL = self.getUrl()
        timeout_ms = timeout*1000
        self.timed_out = False
        self.tid = gobject.timeout_add(timeout_ms, self.__timeout_callback)
        self.pageLoaded = False
        document = self.__webkit.GetDomDocument()
        document.title = " - LOADING"
        # Execute JS code
        script = "var evt = document.createEvent('MouseEvents');\
                     evt.initMouseEvent('click', true, true, document.defaultView, 1, 0, 0, 0, 0, false, false, false, false, 0, null);\
                     document.getElementById('"+elemid+"').dispatchEvent(evt);";
        self.__webkit.ExecuteJsScript(script);
        
        self.gtk_sleep(5)
        info("Waiting For Page to Get Loaded")
        while True:
            document = self.__webkit.GetDomDocument()
            #info("Title: "+document.title)
            #if document.URL != oldURL:
            if document.title.find("LOADED") >=0:
                break;
            #info("waitforclicktofinish: "+ document.URL)
            self.gtk_sleep(100)
            if self.timed_out:
                break;

        # wait time for stylesheet to get loaded
        self.gtk_sleep(self.css_loadtime*1000)
        
        # Disable the timeout
        if self.tid:
            gobject.source_remove(self.tid)
            self.tid = None
        if self.timed_out:
            raise TimeoutException
        else:
            return True
    
    def JsGoBack(self,timeout=5):
        oldURL = self.getUrl()
        timeout_ms = timeout*1000
        self.timed_out = False
        self.tid = gobject.timeout_add(timeout_ms, self.__timeout_callback)
        self.pageLoaded = False
        document = self.__webkit.GetDomDocument()
        document.title = " - LOADING"
        # Execute JS code
        script = "history.go(-1)";
        self.__webkit.ExecuteJsScript(script);
        
        # wait for page to load
        self.gtk_sleep(5)
        info("Waiting For Page to Get Loaded")
        while True:
            document = self.__webkit.GetDomDocument()
            #if document.URL != oldURL:
            if document.title.find("LOADED") >=0:
                break;
            #info("waitforgobackfinish: "+ document.URL)
            self.gtk_sleep(100)
            if self.timed_out:
                break;
       
        # wait time for stylesheet to get loaded
        self.gtk_sleep(self.css_loadtime*1000)
        
        # Disable the timeout
        if self.tid:
            gobject.source_remove(self.tid)
            self.tid = None
        if self.timed_out:
            raise TimeoutException
        else:
            return True
        
    

    def _console_message(self,message):
        #print >> sys.stderr, "console log: ",message
        message = str(message)
        if (message.find("failed") or message.find("error")) >= 0:
            #print >> sys.stderr, "console log: ",message
            error("console message: "+message)
        else:
            #pass
            if self.verbose_output:
                info("console message: "+message)
    
    def _script_alert(self,message):
        # any alert box is treated as an error
        error("script alert: "+message)
        #print >> sys.stderr, "script alert: ",message

    # return an anchor element whose href attribute 
    # value is equal to url argument. if not such element
    # return -1
    def GetAnchorElement(self,url):
        document = self.__webkit.GetDomDocument()
        urlElemList = document.getElementsByTagName("A")
        for i in range(urlElemList.length):
            node = urlElemList.item(i)
            if node.__getattribute__("href") == url:
                return node
        return -1

    def GetUrlList(self, urllist):
        document = self.__webkit.GetDomDocument()
        urlElemList = document.getElementsByTagName("A")
        for i in range(urlElemList.length):
            node = urlElemList.item(i)
            if node.hasAttribute("href") and  node.__getattribute__("href").find("http") != -1:
                urlval = node.__getattribute__("href")
                parsedUrl = urlparse.urlparse(urlval)
                parsedDocUrl = urlparse.urlparse(document.URL)
                # we add the url to the list only when it points to different page
                if (parsedUrl.netloc != parsedDocUrl.netloc) or (parsedUrl.path != parsedDocUrl.path):
                    urllist.append(urlval)

    def getUrl(self):
        document = self.__webkit.GetDomDocument()
        return document.URL
    
    #check if loading image is still present or not
    #when this image is not present we assume page is loaded
    def checkDiv(self):
        document = self.__webkit.GetDomDocument()
        divElemList = document.getElementsByTagName("div")
        for i in range(divElemList.length):
            node = divElemList.item(i)
            divid = node.__getattribute__("id")
            #print "divid: ",divid
            if node.hasAttribute("id") and  node.__getattribute__("id").find("loader") != -1: 
                return True
        return False
    
    def quitgtk(self):
        if gtk.main_level() > 0:
            gtk.mainquit()

    def gtk_sleep(self,time):
        tid = gobject.timeout_add(int (time), self.quitgtk)
        gtk.main()
        gobject.source_remove(tid)
    
    def getDocumentHeight(self):
        document = self.__webkit.GetDomDocument()
        try:
            return document.height
        except:
            return None
    
    def getDocumentWidth(self):
        document = self.__webkit.GetDomDocument()
        try:
            return document.width
        except:
            return None
    
    def GetDocument(self):
        return self.__webkit.GetDomDocument()
