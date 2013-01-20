#!/usr/bin/env python
#coding=utf-8
'''
Created on 2012-10-23

@author: Chine
'''

# Weibo account
account = 'zhulicong89@gmail.com'
pwd = 'ZHULICONG'

# The index of crawler instance, 0 as default.
instance_index = 0

# Mongo relative
mongo_host = None
mongo_port = None

# Scheduler relative
scheduler_host = '127.0.0.1'
scheduler_port = 1123

# Monitor relative
monitor_enable = False
monitor_host = '127.0.0.1'
monitor_port = 8888
# Monitor urls
monitor_log_add_url = '/log/add/'
monitor_register_heartbeat_url = '/heartbeat/register/'
monitor_stop_heartbeat_url = '/heartbeat/stop/'

try:
    from WeiboCrawler.local_settings import *
except ImportError:
    pass

MONITOR_URL = lambda url: 'http://%s:%s%s' % (monitor_host, monitor_port, url)
# monitor_log_add_url = MONITOR_URL(monitor_log_add_url)
monitor_register_heartbeat_url = MONITOR_URL(monitor_register_heartbeat_url)
monitor_stop_heartbeat_url = MONITOR_URL(monitor_stop_heartbeat_url)
