#!/usr/bin/env python
#coding=utf-8
'''
Created on 2012-10-30

@author: Chine
'''

import urllib2
import threading
import time
import random

from settings import account, pwd
from fetcher import CnFetcher
from parser import CnWeiboParser, CnInfoParser, CnRelationshipParser,\
                                check_page_right
from log import logger

def iterable(obj):
    try:
        iter(obj)
        return True
    except TypeError:
        return False

class UserCrawler(threading.Thread):
    def __init__(self, user, is_uid=None, 
                 storage=None, fetcher=None, 
                 fetch_fans=True, span=True, 
                 # dozens of callbacks
                 callbacks=None,  
                 success_callbacks=None, 
                 error_callbacks=None,
                 ):
        super(UserCrawler, self).__init__()
        
        logger.info('fetch user: %s' % user)
        if is_uid is True:
            self.uid = user
        elif is_uid is False:
            self.uid = None
        else:
            try:
                int(user)
                self.uid = user
            except ValueError:
                self.uid = None
        if self.uid is not None:
            self.url = 'http://weibo.cn/u/%s' % self.uid
        else:
            self.url = 'http://weibo.cn/%s' % user
        if fetcher is None:
            self.fetcher = CnFetcher(account, pwd)
            self.fetcher.login()
        else:
            self.fetcher = fetcher
        self.storage = storage
        
        self.user_not_exist = False
        html = self._fetch(self.url)
        if html is None:
            self.user_not_exist = True
        elif self.uid is None:
            parser = CnWeiboParser(html, user, self.storage)
            self.uid = parser.get_uid()
        self.fetch_fans = fetch_fans
        self.span = span
        self.error = False
        self.callbacks = callbacks
        self.success_callbacks = success_callbacks
        self.error_callbacks = error_callbacks
        
    def _check_user_exist(self, html):
        # If user not exist or forbiddened by weibo, directly return False 
        if u'抱歉，您当前访问的用户状态异常，暂时无法访问。' in html:
            self.error = True
            self.user_not_exist = True
            return False
        return True
        
    def _fetch(self, url):
        html = self.fetcher.fetch(url)
        if not self._check_user_exist(html):
            return
        right = check_page_right(html)
        tries = 0
        while not right and tries <= 6:
            time.sleep(10)
            self.fetcher.login()
            sec = 10 * (tries + 1) if tries <= 2 else (
                600 * (tries - 2) if tries < 6 else 3600)
            time.sleep(sec)
            html = self.fetcher.fetch(url)
            if not self._check_user_exist(html):
                return
            right = check_page_right(html)
            if right:
                return html
            tries += 1
        else:
            return html
        self.error = True
        
    @property
    def info_link(self):
        return 'http://weibo.cn/%s/info' % self.uid
    
    @property
    def follow_link(self):
        return 'http://weibo.cn/%s/follow' % self.uid
    
    @property
    def fav_link(self):
        return 'http://weibo.cn/%s/fans' % self.uid
    
    def set_storage(self, storage):
        self.storage = storage
    
    def _crawl(self, url, parser_cls):
        def start(url):
            html = self._fetch(url)
            parser = parser_cls(html, self.uid, self.storage)
            return parser.parse()
        
        error = None
        for i in range(3):
            try:
                return start(url)
            except urllib2.HTTPError, e:
                if e.code == 404:
                    self.error = True
                    continue
                else:
                    error = e
                    continue
            except urllib2.URLError, e:
                error = e
                continue
            time.sleep(i * 5)
        if error is not None:
            raise error
        
    def _get_random_sec(self, maximun=40):
        return random.random() * maximun
        
    def crawl_info(self):
        url = self.info_link
        self._crawl(url, CnInfoParser)
        
    def crawl_weibos(self):
        url = self.url
        while url is not None:
            url = self._crawl(url, CnWeiboParser)
            if self.span:
                time.sleep(self._get_random_sec())
            
    def crawl_follow(self):
        url = self.follow_link
        while url is not None:
            url = self._crawl(url, CnRelationshipParser)
            if self.span:
                time.sleep(self._get_random_sec())
            
    def crawl_fans(self):
        url = self.fav_link
        while url is not None:
            url = self._crawl(url, CnRelationshipParser)
            if self.span:
                time.sleep(self._get_random_sec())
            
    def crawl(self):
        if self.error is True:
            return
        
        if self.fetch_fans:
            print "start to fetch %s's fans" % self.uid
            self.crawl_fans()
        print "start to fetch %s's info" % self.uid
        self.crawl_info()
        print "start to fetch %s's weibo" % self.uid
        self.crawl_weibos()
        
        # Add to completes when finished
        self.storage.complete()
        
    def _call_callbacks(self, callbacks):
        if callbacks is not None:
            if iterable(callbacks):
                for callback in callbacks:
                    callback()
            else:
                callbacks()
        
    def check_error(self, force=False):
        if force is True:
            self.error = True
        if self.error is True:
            if not self.user_not_exist:
                self.storage.error()
            self._call_callbacks(self.error_callbacks)
        return self.error
            
    def run(self):
        assert self.storage is not None
        try:
            self.crawl()
            self.check_error()
            if not self.error:
                self._call_callbacks(self.success_callbacks)
        except Exception, e:
            self.check_error(force=True)
            # raise e
            logger.info('error when crawl: %s' % self.uid)
            logger.exception(e)
        finally:
            if hasattr(self.storage, 'close'):
                self.storage.close()
            if self.callbacks is not None:
                self._call_callbacks(self.callbacks)
