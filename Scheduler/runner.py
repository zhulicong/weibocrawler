#!/usr/bin/env python
#coding=utf-8
'''
Created on 2012-10-31

@author: Chine
'''

import threading

from pymongo import Connection

from Scheduler.settings import mongo_host, mongo_port, start_uids, fetch_size

class UidDistributer(object):
    def __init__(self):
        self.fetch_size = fetch_size
        self.lock = threading.Lock()
        if mongo_host is not None or mongo_port is not None:
            self.connection = Connection(mongo_host, mongo_port)
        else:
            self.connection = Connection()
        self.db = self.connection.tfidf
        self.users = self.db.users
        self.completes = self.db.completes
        self.errors = self.db.errors
        self.starts = []
        for start_uid in start_uids:
            if not self._uid_crawed(start_uid):
                self.starts.append(start_uid)
    
    def __new__(cls, *args, **kwargs):
        if '_instance' not in vars(cls):
            cls._instance = super(UidDistributer, cls).__new__(cls, *args, **kwargs)
        return cls._instance
    
    def set_fetchsize(self, fetch_size):
        self.fetch_size = fetch_size
    
    def _uid_crawed(self, uid):
        return self.completes.find({'uid': uid}).count() > 0
    
    def get(self):
        self.lock.acquire()
        try:
            if self.fetch_size <= 0:
                return {}
            
            if len(self.starts) > 0:
                uid = self.starts.pop()
#                self.completes.insert({'uid': uid})
                self.fetch_size -= 1
                return {'user': uid, 'is_uid': True}
            item = self.users.find_one({'follows': {'$ne': []}})
            if item is not None:
                link = item['link']
                is_uid = link.startswith(u'/u/') \
                    or link.startswith(u'http://weibo.cn/u/')
                user = link.split('/')[-1]
                follow = item['follows'].pop()
                self.users.update({'link': link}, {'$pull': {
                    'follows': follow
                }})
                
                crawled = self._uid_crawed(user)
#                if not crawled:
#                    self.completes.update({'uid': user}, {'$addToSet': 
#                        {'follows': follow}}, upsert=True)
                self.fetch_size -= 1
                return {'user': user, 
                        'is_uid': is_uid, 
                        'crawled': crawled,
                        'follow': follow}
            item = self.errors.find_one()
            if item is not None:
                follow = None
                if 'follow' in item:
                    follow = item['follow']
                self.fetch_size -= 1
                self.errors.remove({'uid': item['uid']})
                return {'user': item['uid'],
                        'is_uid': True,
                        'crawled': False,
                        'follow': follow}
        finally:
            self.lock.release()
            
    def close(self):
        self.connection.close()