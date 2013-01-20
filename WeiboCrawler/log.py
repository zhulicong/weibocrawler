#!/usr/bin/env python
#coding=utf-8
'''
Created on 2012-11-12

@author: Chine
'''

import logging
import logging.handlers
import os

from settings import monitor_enable, monitor_log_add_url,\
                    monitor_host, monitor_port, instance_index

class FixedLogger(logging.Logger):
    def exception(self, msg, *args):
        """
        Convenience method for logging an ERROR with exception information.
        """
        extra = {'instance': instance_index}
        self.error(msg, exc_info=1, extra=extra, *args)

def get_logger(filename):
    logger = FixedLogger(logging.getLogger('crawler'))
    
    handler = logging.FileHandler(filename)
    formatter = logging.Formatter('%(asctime)s - %(module)s.%(funcName)s.%(lineno)d - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    # set level to INFO
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    '''
    Set http handler if monitor is set.
    The url is separated by host and ip which are defined in settings file.
    '''
    if monitor_enable:
        http_handler = logging.handlers.HTTPHandler(
            '%s:%s' % (monitor_host, monitor_port),
            monitor_log_add_url,
            method='POST'
        )
        http_handler.setLevel(logging.WARNING)
        logger.addHandler(http_handler)
    
    return logger

logger = get_logger(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crawler.log'))