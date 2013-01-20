#!/usr/bin/env python
#coding=utf-8
'''
Created on 2012-10-31

@author: Chine
'''

# Data socket relative
data_port = 1123

# Control socket relative
control_port = 1124

# Weibo crawl start weibo users uids
start_uids = []

# Weibo fetch user size
fetch_size = 500

# Mongo relative
mongo_host = None
mongo_port = None

try:
    from Scheduler.local_settings import *
except ImportError:
    pass