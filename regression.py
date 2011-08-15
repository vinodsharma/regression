#!/usr/bin/env python
#
# vim:ts=4:sw=4:expandtab
######################################################################

"""Worker task: does the actual browsing work."""

import sys
import random
import time
import os
import argparse
import uuid
import logging
import browser
from collections import deque
from logging import *
from browser import Browser
import re

workq = deque()

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.strip(),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            add_help=False)
    parser.add_argument("-h", "--help", action="help",
                        help="Show this help message and exit")
    parser.add_argument("-i", "--id", default=None,
            help="ID to assign to worker (for debugging)")
#    parser.add_argument("-l", "--logname", default="/tmp/worker",
#            help="Name of database to store results in")
    parser.add_argument("-m", "--branch-factor", type=int, default=5,
            help="Branching factor of crawl tree")
    parser.add_argument("-t", "--timeout", type=int, default=10,
            help="Maximum # of secs to wait for page load")
    parser.add_argument("-c", "--css-loadtime", type=float, default=1.5,
            help="Maximum # of secs to wait for css to load")
    parser.add_argument("-u", "--url-file", default="sites.txt",
            help="List of URLs from to explore")
    parser.add_argument("-p", "--proxy", default=None,
            help="Proxy to use when generating load")
    parser.add_argument("-w", "--wait-time", type=float, default=4.0,
            help="Average # seconds to pause between page visits.")
    parser.add_argument("-l", "--log-dir", default="/tmp",
            help="log directory for logs")
    parser.add_argument("-e", "--error-tolerance", default=10,
            help="page size error tolerance limit")
    parser.add_argument("-v", "--verbose-output", action='store_true', default=False,
            help="show javascript console messages in logs")
    args = parser.parse_args()
    return args

def do_click_test(urlItem):
    info("Click Test Started")
    info("Clicking on:"+urlItem)
    oldUrl = br.getUrl()
    br.JsMouseClickEvent(urlItem, timeout=args.timeout)
    br.gtk_sleep(1000)
    info("Click Test Done")

def do_page_size_test(urlItem):
    returnedPageHeight = br.getDocumentHeight()
    if returnedPageHeight:
        info("Page Size Test Started")
        no_proxy_url = urlItem
        no_proxy_url =re.sub(args.proxy+'/', '', no_proxy_url)
        no_proxy_br.visit(no_proxy_url, timeout=args.timeout)
        no_proxy_br.gtk_sleep(1000)
        expectedPageHeight = no_proxy_br.getDocumentHeight()
        info("Page size: "+urlItem+"::"+"returnedPageHeight="+
                    str(returnedPageHeight)+"::"+"expectedPageHeight="+str(expectedPageHeight))
        if expectedPageHeight:
            errorvalue = (abs(returnedPageHeight-expectedPageHeight) *100)/expectedPageHeight
            if int(errorvalue) > int(args.error_tolerance):
                error("page size error::"+urlItem+"::"+"returnedPageHeight="+
                    str(returnedPageHeight)+"::"+"expectedPageHeight="+str(expectedPageHeight))
        info("Page Size Test Done")
            
            
def do_go_back_test():
    info("Going Back Test Started")
    oldUrl = br.getUrl()
    br.JsGoBack(timeout=args.timeout)
    info("Going Back Test Done")
    
def do_browse_work(url):
    info("do browse work"+url)
    if args.proxy:
        target_url = "%s/"%(args.proxy) + url
        try:
            br.visit(target_url, timeout=args.timeout)
        except browser.TimeoutException:
            warn("Timed out while visiting  %s"%(target_url))
            return
        else:
            time.sleep(random.normalvariate(args.wait_time, 0.5))
            
        #test page size error for main page
        try:
            do_page_size_test(target_url)
        except browser.TimeoutException:
            warn("Timed out while doing page size test on %s"%(target_url))

        urlList = []
        br.GetUrlList(urlList)
        #random.shuffle(urlList)
        info("urlcount: " +str(len(urlList)))
        for urlItem in urlList:
            # only click on branch_factor 
            # number of urls on this page
            info("branch factor "+str(br.branch_factor))
            if br.branch_factor < 1:
                break;
            
            anchorElem = br.GetAnchorElement(urlItem)
            # this can happen when we come to this page after hitting go back
            # and the url element present earlier on the same page does not 
            # exist
            if anchorElem < 0:
                continue
            # set the id attributes value so that later we can uniquely search it
            anchorElem.setAttribute('id',urlItem)
            
            #test mouse click
            try:
                do_click_test(urlItem)
            except browser.TimeoutException:
                warn("Timed out while clicking on %s"%(urlItem))
                return
            else:
                time.sleep(random.normalvariate(args.wait_time, 0.5))
            
            #test page size error
            try:
                do_page_size_test(urlItem)
            except browser.TimeoutException:
                warn("Timed out while doing page size test on %s"%(urlItem))
            else:
                time.sleep(random.normalvariate(args.wait_time, 0.5))
            
            #test go back
            try:
                do_go_back_test()
            except browser.TimeoutException:
                warn("Timed out while going from %s"%(br.getUrl()))
                return
            else:
                time.sleep(random.normalvariate(args.wait_time, 0.5))
            
            br.branch_factor -=1

if __name__ == '__main__':
    args = parse_args()
    if args.id == None:
        args.id = str(uuid.uuid4())[0:2]

    logFileName = os.path.join(args.log_dir,"worker-"+args.id)
    logging.basicConfig(level=logging.INFO,
      format="[worker-%s] "%(args.id) + "%(levelname)s %(message)s",
      filename=logFileName,
      filemode='w')
    
    #will be used for visitng pages through cloudterminal
    br = Browser(args.branch_factor,args.verbose_output,False,args.css_loadtime)
    #will be used for visiting without cloudterminal
    no_proxy_br = Browser(args.branch_factor,False,True,args.css_loadtime)
    info("Worker started")

    # Read the URLS
    with open(args.url_file, "r") as f:
        lines = f.readlines()
    for line in lines:
        url = "http://" + line.strip()
        workq.append(url)

    while len(workq):
        url = workq.popleft()
        br.branch_factor = args.branch_factor
        do_browse_work(url)
    
    info("Worker terminating.")
