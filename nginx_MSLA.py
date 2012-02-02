#!/usr/bin/env python
# -*-mode: python; coding: iso-8859-1 -*-
#
# Copyright (c) Liu taihua <defage@gmail.com>

"""
Usage:
    [-h|--help] [-t interval=60] [-c cluster=Nanhui] [-H prefer=hostname|IP] [-v|--verbose True|False]

Example:
    python ngx_SLA.py -t 60 -c Nanhui -H hostname -v True
"""

import os
import socket
import getopt
import string
import socket
import subprocess
import commands
import sys
import time
import re
import threading
from collections import defaultdict


normal_status_list = [200,302,301,304,404]
dynamic_err_list = [500+i for i in range(9)]
static_err_list = [500+i for i in range(9)]
static_err_list.append(404)
tsdb_server = 'msla.op.sdo.com'
tsdb_port = 4242
log_file = '/dev/shm/nginx_metrics/metrics.log'
re_status = re.compile('(?<=\s)\d{3}(?=\s)')
re_upstream = re.compile('(?<=\s)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\:\d+(?=\s)')
re_cost = re.compile('(?<=\s)\d+\.\d+|\-(?=\s)')
re_static = re.compile('(?<=\s)\/[^?]*?\.(gif|png|jpg|jpeg|js|css|swf)')
re_dynamic_err = re.compile('(?<=\s)5\d{2}(?=\s)')
re_static_err = re.compile('(?<=\s)5\d{2}|404(?=\s)')
re_ipv4 = re.compile('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
#re_domain = re.compile()




class BackwardsReader:
    """Read a file line by line, backwards"""
    def __init__(self, file):
        self.file = file
        self.buf = ""
        try:
            self.file.seek(-1, 2)
        except Exception,e:
            print e
        self.trailing_newline = 0
        lastchar = self.file.read(1)
        if lastchar == "\n":
            self.trailing_newline = 1
            self.file.seek(-1, 2)

    BLKSIZE = 4096

    def readline(self):
        while 1:
            newline_pos = string.rfind(self.buf, "\n")
            pos = self.file.tell()
            if newline_pos != -1:
                # Found a newline
                line = self.buf[newline_pos+1:]
                self.buf = self.buf[:newline_pos]
                if pos != 0 or newline_pos != 0 or self.trailing_newline:
                    line += "\n"
                return line
            else:
                if pos == 0:
                    # Start-of-file
                    return ""
                else:
                    # Need to fill buffer
                    toread = min(self.BLKSIZE, pos)
                    self.file.seek(-toread, 1)
                    self.buf = self.file.read(toread) + self.buf
                    self.file.seek(-toread, 1)
                    if pos - toread == 0:
                        self.buf = "\n" + self.buf

def getLocalIp():
    from socket import socket, SOCK_DGRAM, AF_INET
    s = socket(AF_INET, SOCK_DGRAM)
    s.connect(('8.8.8.8',0))
    LocalIp = s.getsockname()[0]
    s.close()
    return LocalIp

def usage():
    print __doc__

def conn_socket4sendmsg(msg, host, port):
    sk = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        sk.connect((host, port),)
    except Exception,e:
        print e
    sk.send("%s\n"%msg)
    sk.close()
    

def send_msg2tsdb(host, port, log_file, target, cluster, COLLECTION_INTERVAL=60, verbose=True):
    while True:
        rc_static = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        rc_dynamic = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        stop = int(time.time()) - COLLECTION_INTERVAL
        br = BackwardsReader(open(log_file))
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:
            sock.connect((host,port),)
        except Exception, e:
            print e

        while True:
            line = br.readline()
            if not line:
                print "not line:",repr(line)
                break
            if int(float(line.split()[0])) >= stop:
                domain = line.split()[1]
                #upstream = re.sub('\:\d{1,5}','',line.split()[4])
                upstream = re_upstream.findall(line)
                status = re_status.findall(line)
                if status:
                    status = status[0]
                else:continue
                cost  = line.split()[-1]

                '''sometimes uri can be empty, like: 1302221251.460 aig.sdo.com - 400 - 10.129.1.230 -'''
                if line.split()[2] == "-":continue

                '''It's weird that the domain part is an IP address, so we don't process them now'''
                if re_ipv4.findall(domain):continue

                if re_static.findall(line):
                    if upstream:
                        upstream = re_upstream.findall(line)[0].split(":")[0]
                    else:
                        cost = 0.001
                        upstream = getLocalIp()
                    if cost == "-":
                        continue
                    else:
                        cost = float(cost)
                    rc_static[domain][upstream]['throughput'] += 1
                    rc_static[domain][upstream]['latency'] += cost

                    if int(status) in static_err_list:
                        rc_static[domain][upstream][status] += 1
                else:
                    if upstream:
                        upstream = re_upstream.findall(line)[0].split(":")[0]
                    else:
                        cost = 0.003
                        upstream = getLocalIp()
                    if cost == "-":
                        continue
                    else:
                        cost = float(cost)
                    rc_dynamic[domain][upstream]['throughput'] += 1
                    rc_dynamic[domain][upstream]['latency'] += cost

                    if int(status) in dynamic_err_list:
                        rc_dynamic[domain][upstream][status] += 1
            else:break
        for k, v in rc_static.items():
            for k1, v1 in v.items():
                for k2, v2 in v1.items():
                    if k2 in ['throughput','latency']:
                        result = "put nginx.%s %s %s domain=%s upstream=%s host=%s virtualized=no cluster=%s type=static"%(k2,int(time.time()),v2,k,k1,target,cluster)
                        if verbose:
                            print result
                        try:
                            sock.send("%s\n"%result)
                        except Exception, e:
                            conn_socket4sendmsg(result, host, port)    
                            print e
                    else:
                        result = "put nginx.error %s %s domain=%s upstream=%s code=%s host=%s virtualized=no cluster=%s type=static"%(int(time.time()),v2,k,k1,k2,target,cluster)
                        if verbose:
                            print result
                        try:
                            sock.send("%s\n"%result)
                        except Exception, e:
                            conn_socket4sendmsg(result, host, port)    
                            print e
        
        for k, v in rc_dynamic.items():
            for k1, v1 in v.items():
                for k2, v2 in v1.items():
                    if k2 in ['throughput','latency']:
                        result = "put nginx.%s %s %s domain=%s upstream=%s host=%s virtualized=no cluster=%s type=dynamic"%(k2,int(time.time()),v2,k,k1,target,cluster)
                        if verbose:
                            print result
                        try:
                            sock.send("%s\n"%result)
                        except Exception, e:
                            conn_socket4sendmsg(result, host, port)    
                            print e
                    else:
                        result = "put nginx.error %s %s domain=%s upstream=%s code=%s host=%s virtualized=no cluster=%s type=dynamic"%(int(time.time()),v2,k,k1,k2,target,cluster)
                        if verbose:
                            print result
                        try:
                            sock.send("%s\n"%result)
                        except Exception, e:
                            conn_socket4sendmsg(result, host, port)    
                            print e
        time.sleep(60)

def main(argv):
    if not argv:
        usage()
        sys.exit()
    verbose = False
    try:
        opts, args = getopt.getopt(argv, "ht:c:H:v:", ["help", "interval=", "cluster=","target=","verbose=False"])
    except getopt.GetoptError,err:
        print err
        usage()
        sys.exit()

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-t"):
            interval = int(arg)
        elif opt in ("-c"):
            cluster = arg
        elif opt in ("-H"):
            target = arg
        elif opt in ("-v|--verbose"):
            verbose = arg
        else:
            usage()
            sys.exit()

    if verbose not in ["True","False"]:
        usage()
        sys.exit() 

    if target == "hostname":
        target = commands.getoutput("hostname")
    else:
        target = getLocalIp()

    COLLECTION_INTERVAL = interval  # seconds
    host = tsdb_server
    port = tsdb_port
    send_msg2tsdb(host, port, log_file, target, cluster, COLLECTION_INTERVAL, verbose)


if __name__ == "__main__":
    main(sys.argv[1:])
