#!/usr/bin/env python
#coding=utf-8
'''
Created on 2012-11-21

@author: Chine
'''

import time
from datetime import datetime
from threading import Lock

nodes = {}
RUNNING, PENDING, STOPPED = range(3)

class Node(object):
    def __init__(self, host, instance, status=RUNNING):
        self.host = host
        self.inst = instance
        self.status = status
        self.last_trick = int(time.time())
        self.fetches = []
        
    def __eq__(self, other):
        return self.host == other.host and self.inst == other.inst
    
    def __hash__(self):
        return hash(self.host) * hash(self.inst)
    
    def key(self):
        return '%s%%%s' % (self.host, self.inst)
    
    def activate(self):
        self.last_trick = int(time.time())
        
    @property
    def last_update_date(self):
        return datetime.fromtimestamp(self.last_trick).strftime('%Y-%m-%d %H:%M:%S')
    
register_lock = Lock()
def register_node(node_key, fetch, remove=False):
    register_lock.acquire()
    try:
        if node_key in nodes:
            node = nodes[node_key]
            if remove is False and fetch not in node.fetches:
                node.fetches.append(fetch)
            elif remove is True and fetch in node.fetches:
                node.fetches.remove(fetch)
            node.activate()
            if node.status != RUNNING:
                node.status = RUNNING
        else:
            host, inst = tuple(node_key.split('%'))
            node = Node(host, inst)
            if remove is False:
                node.fetches.append(fetch)
            nodes[node_key] = node
    finally:
        register_lock.release()
        
def stop_node(node_key):
    register_lock.acquire()
    try:
        if node_key in nodes:
            node = nodes[node_key]
            if node.status != STOPPED:
                node.status = STOPPED
    finally:
        register_lock.release()
        
def node_check(threshold=600):
    while True:
        register_lock.acquire()
        try:
            for node in nodes.values():
                if node.status == RUNNING and\
                     time.time() - node.last_trick >= threshold:
                    node.status = PENDING
        finally:
            register_lock.release()
        time.sleep(60)