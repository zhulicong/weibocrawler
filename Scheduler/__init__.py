#!/usr/bin/env python
#coding=utf-8

import json
import time
import threading
from socket import socket, AF_INET, SOCK_STREAM

from pymongo.database import OperationFailure

from Scheduler.runner import UidDistributer
from Scheduler.settings import data_port as PORT, control_port

HOST = ''
BUFSIZE = 1024
ADDR = (HOST, PORT)

def action():
    distributer = UidDistributer()
    
    soc = socket(AF_INET, SOCK_STREAM)
    soc.bind((HOST, control_port))
    soc.listen(5)
    
    try:
        while True:
            client_soc, addr = soc.accept()
            try:
                data = client_soc.recv(BUFSIZE)
                if not data:
                    break
                data = json.loads(data)
                if data['action'] == 'GET':
                    client_soc.send(str(distributer.fetch_size))
                elif data['action'] == 'SET' and 'fetchsize' in data:
                    fetch_size = int(data['fetchsize'])
                    distributer.set_fetchsize(fetch_size)
                else:
                    break
            finally:
                client_soc.close()
    finally:
        soc.close()
        distributer.close()

def main():
    # start the action thread
    threading.Thread(target=action).start()
    
    distributer = UidDistributer()
    
    soc = socket(AF_INET, SOCK_STREAM)
    soc.bind(ADDR)
    soc.listen(40)
    
    try:
        while True:
            print 'Waiting for connection'
            client_soc, addr = soc.accept()
            print 'Connected from: ', addr
            data = None
            try:
                data = json.dumps(distributer.get())
                print 'sending data: ', data
                print 'timestamp: ', int(time.time())
                client_soc.send(data)
            except OperationFailure, e:
                print e
    finally:
        soc.close()
        distributer.close()

if __name__ == "__main__":
    main()