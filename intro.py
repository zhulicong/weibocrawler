#!/usr/bin/env python
#coding=utf-8
'''
Created on 2012-11-5

@author: Chine
'''

import sys
import os

if __name__ == "__main__":
    reload(sys)
    sys.setdefaultencoding('utf-8')
    
    dirname = os.path.dirname(os.path.abspath(__file__))
    args = sys.argv
    if len(args) <= 1 or (args[1] not in ('sch', 'crw', 'mnt')):
        print 'Error! Please choose "sch"(scheduler), "crw"(crawler) or "mnt"(monitor)!'
    else:
        if args[1] == 'sch':
            import Scheduler
            Scheduler.main()
        elif args[1] == 'mnt':
            import Monitor
            Monitor.main()
        else:
            import WeiboCrawler
            WeiboCrawler.main()