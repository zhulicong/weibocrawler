#!/usr/bin/env python
#coding=utf-8

import threading
import os

import tornado.ioloop
import tornado.web

from Monitor.handlers import routines
from Monitor.nodes import node_check
from Monitor.settings import debug

settings = {'debug': debug, 
            "static_path": os.path.join(os.path.dirname(__file__), "static"),}
application = tornado.web.Application(routines, **settings)

def main():
    threading.Thread(target=node_check).start()
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
    
if __name__ == "__main__":
    main()