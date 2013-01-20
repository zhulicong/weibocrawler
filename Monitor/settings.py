#!/usr/bin/env python
#coding=utf-8
'''
Created on 2012-11-26

@author: Chine
'''

debug = True

# Scheduler Control socket relative
scheduler_host = '127.0.0.1'
scheduler_control_port = 1124

# Mongo relative
mongo_host = None
mongo_port = None

try:
    from Monitor.local_settings import *
except ImportError:
    pass