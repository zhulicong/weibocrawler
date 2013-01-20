#!/usr/bin/env python
#coding=utf-8

import json
import time
import os
import urllib
import urllib2
from socket import socket, AF_INET, SOCK_STREAM

from crawler import UserCrawler
from storage import MongoStorage, FileStorage
from fetcher import CnFetcher
from settings import scheduler_host, scheduler_port,\
                                  account, pwd, instance_index, \
                                  monitor_enable,\
                                  monitor_register_heartbeat_url as hb_url,\
                                  monitor_stop_heartbeat_url as stop_hb_url
from log import logger

SIZE = 3
tokens = range(SIZE)
give_ups = SIZE
def callback(token):
    def inner():
        if token not in tokens:
            tokens.append(token)
    return inner

# Monitor callbacks
def register_heartbeat(user, remove=False):
    def inner():
        try:
            if monitor_enable:
                params = {'inst': instance_index,
                          'fetch': user,
                          'rm': 0 if not remove else 1}
                urllib2.urlopen(hb_url, data=urllib.urlencode(params))
        except urllib2.URLError:
            logger.info('Cannot connect to monitor')
    return inner

def stop_heartbeat():
    try:
        if monitor_enable:
            params = {'inst': instance_index}
            urllib2.urlopen(stop_hb_url, data=urllib.urlencode(params))
    except urllib2.URLError:
        logger.info('Cannot connect to monitor')

buf_size = 1024
def create_socket():
    addr = (scheduler_host, scheduler_port)
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect(addr)
    
    return client_socket

cookie_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'cookies.txt')
def create_cookie_file():
    if not os.path.exists(cookie_file):
        f = open(cookie_file, 'w')
        try:
            return True
        finally:
            f.close()
    return False

errors = 0
def error_callback(threshold=5):
    def inner():
        global errors, give_ups
        errors += 1
        if errors >= threshold:
            give_ups = 0
    return inner
def reset_error_callback():
    global errors
    errors = 0
    
def dc():
    def run_callbacks(callbacks):
        for callback in callbacks:
            callback()
    
    global give_ups
    
    try:
        create = create_cookie_file()
        fetcher = CnFetcher(account, pwd, cookie_file if not create else None)
        if create:
            fetcher.login(cookie_filename=cookie_file)
        while give_ups > 0:
            n = 0
            while len(tokens) == 0:
                if give_ups > 0:
                    n += 1
                    time.sleep(n);
                else:
                    return
            
            token = tokens.pop()
            cb = callback(token)
            
            soc = create_socket()
            try:
                data = json.loads(soc.recv(buf_size))
                if data == None:
                    time.sleep(15)
                    cb()
                    continue
                elif len(data) == 0:
                    give_ups -= 1
                    continue
                
                user = data['user']
                is_uid = data['is_uid']
                crawled = data.get('crawled', False)
                follow = data.get('follow', None)
                
                # monitor callback
                register_heartbeat(user)()
                register_rm_cb = register_heartbeat(user, True)
                
                # success callbacks
                success_callbacks = (register_rm_cb, reset_error_callback)
                error_callbacks = (error_callback, register_rm_cb)
                
                try:
                    crawler = UserCrawler(user, is_uid=is_uid, fetcher=fetcher, 
                                          fetch_fans=follow is None, 
                                          callbacks=cb, 
                                          success_callbacks=success_callbacks,
                                          error_callbacks=error_callbacks)
                    # the user not exist
                    if crawler.user_not_exist or crawler.uid == 'attention':
                        cb()
                        run_callbacks(success_callbacks)
                        continue
                    
                    uid = crawler.uid
                    storage = MongoStorage(uid, follow, user=user)
                    
                    if crawled or storage.crawled: 
                        cb()
                        run_callbacks(success_callbacks)
                        storage.close()
                        continue
                    else:
                        crawler.set_storage(storage)
                        crawler.start()
                except Exception, e:
                    cb()
                    run_callbacks(error_callbacks)
                    # raise e
                    logger.exception(e)
            finally:
                soc.close()
    finally:
        # When run over, call stop heartbeat
        stop_heartbeat()
            
def local(db='file', folder=None, uids=[]):
    global give_ups
    
    create = create_cookie_file()
    fetcher = CnFetcher(account, pwd, cookie_file if not create else None)
    if create:
        fetcher.login(cookie_filename=cookie_file)
    while give_ups > 0:
        while len(tokens) == 0:
            if give_ups > 0:
                pass
            else:
                return
        
        token = tokens.pop()
        cb = callback(token)
        
        if len(uids) == 0:
            give_ups = 0
        else:
            uid = uids.pop()
            
            try:
                crawler = UserCrawler(uid, is_uid=True, fetcher=fetcher, 
                                      fetch_fans=False, callbacks=cb, span=False)
                uid = crawler.uid
                if db == 'file' and folder is not None:
                    storage = FileStorage(uid, folder)
                elif db == 'mongo':
                    storage = MongoStorage(uid)
                else:
                    raise ValueError('db must be "file" or "mongo", ' + 
                                     'when is "file", you must define folder parameter.')
                
                if storage.crawled: 
                    storage.complete()
                    cb()
                    continue
                else:
                    crawler.set_storage(storage)
                    crawler.start()
            except Exception, e:
                cb()
                # raise e
                logger.exception(e)
        
def main(is_dc=True, *args, **kwargs):
    if is_dc:
        dc()
    else:
        local(*args, **kwargs)

if __name__ == "__main__":
    import argparse
    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')
            
    parser = argparse.ArgumentParser('Task to crawl sina weibo.')
    parser.add_argument('-m', '--mode', metavar="mode", nargs="?",
                        choices=['dc', 'sg'], default='dc', const='dc',
                        help="crawl mode, distributed(dc) or single(sg), default: dc")
    parser.add_argument('-t', '--type', metavar="type", nargs="?",
                        choices=['mongo', 'file'], default='mongo', const="mongo",
                        help="under sg mode, define where to put the crawled data(mongo or file, " +
                            "default: mongo)")
    parser.add_argument('-l', '--loc', metavar="location", nargs="?",
                        help="under sg mode, and type is file, the paramer can work")
    parser.add_argument('uids', metavar="uids", type=int, nargs="*",
                        help="under sg mode, define the uids to crawl")
    args = parser.parse_args()
    
    is_dc = args.mode == 'dc'
    db = args.type
    folder = args.loc
    uids = args.uids
    main(is_dc=is_dc, db=db, folder=folder, uids=uids)
