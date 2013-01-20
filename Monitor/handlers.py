#!/usr/bin/env python
#coding=utf-8
'''
Created on 2012-11-20

@author: Chine
'''

import json
import re
import os
import logging
from datetime import datetime
from socket import socket, AF_INET, SOCK_STREAM

import tornado.web
from pymongo import Connection

from Monitor.log import logger, log_file
from Monitor.nodes import register_node, stop_node, nodes
from Monitor.settings import scheduler_host, scheduler_control_port, \
                                mongo_host, mongo_port

BUFSIZE = 1024
def create_socket():
    print 'try to connect to socket server', scheduler_host, scheduler_control_port
    addr = (scheduler_host, scheduler_control_port)
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect(addr)
    
    return client_socket

def sort_nodes(nodes):
    def _cmp(n1, n2):
        host_cmp = cmp(n1.host, n2.host)
        if host_cmp != 0:
            return host_cmp
        return cmp(n1.inst, n2.inst)
    return sorted(nodes, cmp=_cmp)

def read_log(start=0, counts=10):
    if not os.path.exists(log_file):
        return
    f = open(log_file)
    try:
        segments = []
        contents = list(f)
        if len(contents) == 0:
            # if log file is empty
            return
        contents.reverse()
        
        size = -1
        last_seg = -1
        for i, line in enumerate(contents):
            blank_before = line.split(' ')[0]
            if len(blank_before) == 0:
                continue
            else:
                try:
                    datetime.strptime(blank_before, '%Y-%m-%d')
                    size += 1
                    if size >= start and size < start + counts:
                        segments.append((last_seg + 1, i))
                    last_seg = i
                except ValueError:
                    continue
        
        results = []
        for seg in segments:
            result = contents[seg[0]: seg[1]+1]
            result.reverse()
            html = '<p>%s</p>' % result[0].strip('\n')
            if len(result) > 1:
                html += '<p><blockquote>%s</blockquote></p>' \
                    % ''.join([l.replace('\n', '<br />') for l in result[1:]])
            results.append(html)
        
        return size+1, results
    finally:
        f.close()

class IndexHandler(tornado.web.RequestHandler):
    def initialize(self):
        for i in range(3):
            try:
                if mongo_host is not None or mongo_port is not None:
                    self.conn = Connection(mongo_host, mongo_port)
                else:
                    self.conn = Connection()
                self.db = self.conn.tfidf
                break
            except Exception, e:
                if i < 2:
                    continue
                else:
                    raise e
    
    @tornado.web.asynchronous
    def get(self):
        try:
            weibos = self.db.weibo.count()
            completes = self.db.completes.count()
            users = self.db.users.count()
            errors = self.db.errors.count()
            
            tasks = sort_nodes(nodes.values())
            
            fetch_size = 0
            s_error = False
            try:
                soc = create_socket()
                try:
                    data = {'action': 'GET'}
                    soc.send(json.dumps(data))
                    fetch_size = soc.recv(BUFSIZE)
                finally:
                    soc.close()
            except Exception, e:
                print e
                s_error = True
                
            logs = read_log()
            n_logs = 0
            if logs is not None:
                (n_logs, logs) = logs
            next_log_start = 10
            
            kwargs = {
                'weibos': weibos,
                'completes': completes,
                'users': users,
                'errors': errors,
                'tasks': tasks,
                'fetch_size': fetch_size,
                's_error': s_error,
                'n_logs': n_logs,
                'logs': logs,
                'next_log_start': next_log_start
            }
            self.render('templates/index.html', **kwargs)
        finally:
            self.conn.close()
        
class StatisticsHandler(IndexHandler):
    @tornado.web.asynchronous
    def get(self):
        try:
            weibos = self.db.weibo.count()
            completes = self.db.completes.count()
            users = self.db.users.count()
            errors = self.db.errors.count()
            
            kwargs = locals()
            del kwargs['self']
            self.write(json.dumps(kwargs))
            self.finish()
        finally:
            self.conn.close()

class NodesHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.render('templates/tasks.html', tasks=sort_nodes(nodes.values()))
    
class SettingsHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        fetch_size = 0
        s_error = False
        try:
            soc = create_socket()
            try:
                data = {'action': 'GET'}
                soc.send(json.dumps(data))
                fetch_size = soc.recv(BUFSIZE)
            finally:
                soc.close()
        except Exception, e:
            print e
            s_error = True
        self.render('templates/settings.html', fetch_size=fetch_size, s_error=s_error)
        
class FetchsizeSetHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def post(self):
        fetch_size = self.request.arguments['fetchsize'][0]
        s_error=False
        try:
            soc = create_socket()
            try:
                data = {'action': 'SET', 'fetchsize': fetch_size}
                soc.send(json.dumps(data))
                fetch_size = soc.recv(BUFSIZE)
            finally:
                soc.close()
        except Exception, e:
            print e
            s_error = True
        self.write('1' if not s_error else '0')
        self.finish()
        
class LogsShowHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        start = int(self.request.arguments.get('start', [0, ])[0])
        counts = int(self.request.arguments.get('size', [10, ])[0])
        
        logs = read_log(start, counts)
        n_logs = 0
        if logs is not None:
            (n_logs, logs) = logs
        next_log_start = start + counts
        self.render('templates/logs.html', 
                    logs=logs, 
                    n_logs=n_logs,
                    next_log_start=next_log_start)
        
    
class LogAddHandler(tornado.web.RequestHandler):
    tuple_reg = re.compile("^\([^\(\)]*\)$")
    float_reg = re.compile("^\d*\.\d+$")
    int_reg = re.compile("^\d+$")
    
    def _extract(self, string):
        if self.tuple_reg.match(string):
            return tuple(json.loads('[%s]' % string[1: -1].replace('None', 'null')))
        elif self.float_reg.match(string):
            return float(string)
        elif self.int_reg.match(string):
            return int(string)
        return string
    
    def post(self):
        args = dict(
            [(k, self._extract(''.join(v))) for (k, v) in self.request.arguments.iteritems()]
        )
        args['remoteIP'] = self.request.remote_ip
        record = logging.makeLogRecord(args)
        logger.handle(record)
        
class HeartbeatRegisterHandler(tornado.web.RequestHandler):
    def post(self):
        inst = self.request.arguments.get('inst')[0]
        host = self.request.remote_ip
        fetch = self.request.arguments.get('fetch')[0]
        rm = int(self.request.arguments.get('rm', [0, ])[0]) == 1
        
        key = '%s%%%s' % (host, inst)
        register_node(key, fetch, remove=rm)
        print 'register from %s' % key
        
class HeartbeatStopHandler(tornado.web.RequestHandler):
    def post(self):
        inst = self.request.arguments.get('inst')[0]
        host = self.request.remote_ip
        
        key = '%s%%%s' % (host, inst)
        stop_node(key)
        print 'stop from %s' % key
    
routines = [
    (r'/', IndexHandler),
    (r'/log/add/', LogAddHandler),
    (r'/heartbeat/register/', HeartbeatRegisterHandler),
    (r'/heartbeat/stop/', HeartbeatStopHandler),
    (r'/grabs/stat/', StatisticsHandler),
    (r'/tasks/stat/', NodesHandler),
    (r'/settings/', SettingsHandler),
    (r'/fetchsize/set/', FetchsizeSetHandler),
    (r'/logs/show/', LogsShowHandler)
]