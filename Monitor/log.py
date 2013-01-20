#!/usr/bin/env python
#coding=utf-8
'''
Created on 2012-11-20

@author: Chine
'''

import os
import logging

def get_logger(filename):
    logger = logging.getLogger('monitor')
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'monitor.log')
    handler = logging.FileHandler(filename)
    formatter = logging.Formatter(
        '%(asctime)s - %(module)s.%(funcName)s.%(lineno)d - %(levelname)s - %(remoteIP)s#%(instance)s - %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(logging.ERROR)
    logger.addHandler(handler)
    return logger

log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'monitor.log')
logger = get_logger(log_file)