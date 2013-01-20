#!/usr/bin/env python
#coding=utf-8
'''
Created on 2012-10-23

@author: Chine
'''

import json
from datetime import datetime, timedelta
import time
# added for datetime.strptime is not thread-safe
from threading import Lock

from pyquery import PyQuery as pq

class WeiboParser(object):
    narrow_mode, c_mode = range(2)
    
    def __init__(self, html, user, storage):
        self.user = user
        self.storage = storage
        
        self.doc = pq(html)
        if len(self.doc.find("div.W_main_narrow")) > 0:
            self.parse_mode = self.narrow_mode
            print 'narrow mode'
        elif len(self.doc.find("div.W_main")) > 0:
            self.parse_mode = self.c_mode
            print 'c mode'
            
        for node in self.doc.find('script'):
            text = pq(node).text()
            if 'STK' in text:
                text = text.replace('STK && STK.pageletM && STK.pageletM.view(', '')[:-1]
                try:
                    json_data = json.loads(text)
                    if 'js' in json_data:
                        is_feed = False
                        for js in json_data['js']:
                            if 'feed' in js.lower():
                                is_feed = True
                        if not is_feed:
                            continue
                    else:
                        continue
                    if 'html' in json_data:
                        html = json_data['html']
                        self.doc = pq(html)
                except ValueError:
                    continue
                        
                    
    def parse(self):
        if self.parse_mode == self.narrow_mode:
            
            def _parse_weibo(i):
                print 'start parse weibo'
                
                node = pq(this)
                weibo = {'mid': node.attr['mid']}
                is_forward = node.attr['isforward'] is not None
                content = node.find('p')\
                    .filter(lambda i: pq(this).attr['node-type'] == 'feed_list_content')\
                    .eq(0).text()
                weibo['content'] = content
                if is_forward:
                    forward = node.children('dd.content')\
                        .children('dl.comment')\
                        .children('dt')\
                        .children('em').text()
                    weibo['forward'] = forward
                self.storage.save_weibo(weibo)
                
            self.doc.find('dl.feed_list.W_linecolor').each(_parse_weibo)
        
        elif self.parse_mode == self.c_mode:
            
            def _parse_weibo(i):
                print 'start parse weibo'
                
                node = pq(this)
                weibo = {'mid': node.attr['mid']}
                is_forward = node.attr['isforward'] is not None
                content = node.children('div.WB_feed_datail')\
                    .children('div.WB_detail')\
                    .children('div.WB_text')\
                    .text()
                weibo['content'] = content
                if is_forward:
                    forward = node.find('div.WB_media_expand').eq(0)\
                        .children('div').children('div.WB_text').text()
                    weibo['forward'] = forward
                self.storage.save_weibo(weibo)
            
            self.doc.find('div.WB_feed_type.SW_fun').each(_parse_weibo)
         
def check_page_right(html):
    try:
        doc = pq(html)
        title = doc.find('title').text().strip()
        return title != u'微博广场' and title != u'新浪微博-新浪通行证'
    except AttributeError:
        return False
   
class CnWeiboParser(object):
    strptime_lock = Lock() # added lock for datetime.strptime method is not thread-safe.
    
    def __init__(self, html, user, storage):
        self.user = user
        self.storage = storage
        self.doc = pq(html)
        
    def _strptime(self, string, format_):
        self.strptime_lock.acquire()
        try:
            return datetime.strptime(string, format_)
        finally:
            self.strptime_lock.release()
        
    def parse_datetime(self, dt_str):
        dt = None
        if u'秒' in dt_str:
            sec = int(dt_str.split(u'秒', 1)[0].strip())
            dt = datetime.now() - timedelta(seconds=sec)
        elif u'分钟' in dt_str:
            sec = int(dt_str.split(u'分钟', 1)[0].strip()) * 60
            dt = datetime.now() - timedelta(seconds=sec)
        elif u'今天' in dt_str:
            dt_str = dt_str.replace(u'今天', datetime.now().strftime('%Y-%m-%d'))
            # dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
            dt = self._strptime(dt_str, '%Y-%m-%d %H:%M')
        elif u'月' in dt_str and u'日' in dt_str:
            this_year = datetime.now().year
            # dt = datetime.strptime('%s %s' % (this_year, dt_str), '%Y %m月%d日 %H:%M')
            dt = self._strptime('%s %s' % (this_year, dt_str), '%Y %m月%d日 %H:%M')
        else:
            # dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
            dt = self._strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        return time.mktime(dt.timetuple())
        
    def parse(self):
        def _parse_weibo(i):
            node = pq(this)
            
            if node.attr('id') is None:
                return
            
            n = 0
            divs = node.children('div')
            for div in divs:
                if len(pq(div).find('img.ib')) == 0:
                    n += 1
            if n == 0:
                return
            
            weibo = {}
            is_forward = True if len(divs) == 2 else False
            content = pq(divs[0]).children('span.ctt').text()
            if is_forward:
                weibo['forward'] = content
            else:
                weibo['content'] = content
            if is_forward:
                div = pq(divs[-1])
                weibo['content'] = div.text().split(u'赞')[0].strip(u'转发理由:').strip()
            # get weibo's datetime
            dt_str = pq(divs[-1]).children('span.ct').text()
            if dt_str is not None:
                dt_str = dt_str.replace('&nbsp;', ' ').split(u'来自', 1)[0].strip()
            weibo['ts'] = int(self.parse_datetime(dt_str))
            self.storage.save_weibo(weibo)
        
        self.doc.find('div.c').each(_parse_weibo)
        
        pg = self.doc.find('div#pagelist.pa')
        if len(pg) == 1 and u'下页' in pg.text():
            return 'http://weibo.cn%s' % pq(pg.find('a')[0]).attr('href')
        
    def get_uid(self):
        link = self.doc.find('div.u a').eq(1).attr('href')
        return link.strip('/').split('/')[0]
        
class CnInfoParser(object):
    def __init__(self, html, user, storage):
        self.user = user
        self.storage = storage
        self.doc = pq(html)
        
    def parse(self):
        div = self.doc.find('div.tip:first').next('div.c').html()
        if div is None:
            return
        div = div.replace('\n', '').replace('<br />', '<br/>')
        info = {}
        for itm in div.split('<br/>'):
            if len(itm.strip()) == 0:
                continue
            kv = tuple(itm.split(':', 1))
            if len(kv) != 2 or len(kv[1].strip()) == 0:
                continue
            k, v = kv[0], pq(kv[1]).text().strip('更多>>').strip()
            info[k] = v
        self.storage.save_info(info)
        return info

class CnRelationshipParser(object):
    def __init__(self, html, user, storage):
        self.user = user
        self.storage = storage
        self.doc = pq(html)
        
    def parse(self):
        def _parse_user(i):
            node = pq(this)
            if len(node.children('img')) > 0:
                return
            # self.storage.save_user((node.attr('href'), node.text(), ))
            self.storage.save_user((node.attr('href'), self.user, ))
        
        self.doc.find('table tr td a:first').each(_parse_user)
        
        pg = self.doc.find('div#pagelist.pa')
        if len(pg) == 1 and u'下页' in pg.text():
            return 'http://weibo.cn%s' % pq(pg.find('a')[0]).attr('href')