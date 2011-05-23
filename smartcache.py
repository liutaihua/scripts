#!/usr/bin/env python
#-*- coding:utf8 -*-
#author:liutaihua
#email: defage@gmail.com


"""
Usage:
    [-h|--help] [-m memcachedSize] [-c memcachedNum] [-l machinelist]
-s
    The size of demand( must be a Integer)
-c  The number of instance( must be a Integer )

Example:(2 instance that each 4G)
    python select_cache.py -s 8000 -c 2
"""


import os
import sys
import json
import time
import urllib
import getopt
import random
import paramiko
import Queue, threading, sys  
from threading import Thread


from threadpool import ThreadPool, makeRequests

rsa_key = '~/.ssh/id_rsa'
memcached_binary = '/opt/app/commonCache/bin/memcached'

server_index_api = 'http://op.sdo.com/cache-mgmt-nh/rest/list/server'
instance_api = 'http://op.sdo.com/cache-mgmt-nh/rest/list/instance'


def usage():
    print __doc__

'''work thread pool'''
# working thread  
class Worker(Thread):  
    worker_count = 0  
    def __init__( self, workQueue, resultQueue, timeout = 0, **kwds):  
        Thread.__init__( self, **kwds )  
        self.id = Worker.worker_count  
        Worker.worker_count += 1  
        self.setDaemon( True )  
        self.workQueue = workQueue  
        self.resultQueue = resultQueue  
        self.timeout = timeout  
  
    def run( self ):  
        ''' the get-some-work, do-some-work main loop of worker threads '''  
        while True:  
            try:  
                callable, args, kwds = self.workQueue.get(timeout=self.timeout)  
                res = callable(*args, **kwds)  
                #print "worker[%2d]: %s" % (self.id, str(res) )  
                self.resultQueue.put( res )  
            except Queue.Empty:  
                break  
            #except :  
                #print 'worker[%2d]' % self.id, sys.exc_info()[:2]  
            #    pass
                  
class WorkerManager:  
    def __init__( self, num_of_workers=10, timeout = 0):  
        self.workQueue = Queue.Queue()  
        self.resultQueue = Queue.Queue()  
        self.workers = []  
        self.timeout = timeout  
        self._recruitThreads( num_of_workers )  
  
    def _recruitThreads( self, num_of_workers ):  
        for i in range( num_of_workers ):  
            worker = Worker( self.workQueue, self.resultQueue, self.timeout )  
            self.workers.append(worker)  
  
    def start(self):  
        for worker in self.workers:  
            worker.start()  
  
    def wait_for_complete( self):  
        # ...then, wait for each of them to terminate:  
        while len(self.workers):  
            worker = self.workers.pop()  
            worker.join( )  
            if worker.isAlive() and not self.workQueue.empty():  
                self.workers.append( worker )  
        print "All jobs are are completed."  
  
    def add_job( self, callable, *args, **kwds ):  
        self.workQueue.put( (callable, args, kwds) )  
  
    def get_result( self, *args, **kwds ):  
        return self.resultQueue.get( *args, **kwds )






'''
执行远程服务器命令
'''
def ssh_command(host,cmd,myport=58422,user='root'):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privatekeyfile = os.path.expanduser('%s'%rsa_key)
    mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
    ssh.connect(host,port=myport,username=user,pkey=mykey)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    result = stdout.readlines()
    return result


'''
取得远程服务器内存信息
'''
def get_mem_info(host, sleep=0):
    result = ssh_command(host, 'free -m')[1].split()[1]
    mem_dict[host] = int(result)
    #return result


'''
取得远程服务器所有memcached进程的-m 后的使用内存数
'''
def get_cache_info(host, sleep=0):
    cmd = "ps -ef|grep 'memcached' |grep -v 'grep'|grep -o '\-m [0-9]*'|awk  '{a=a+$2}END{print a}'"
    result = ssh_command(host,cmd)[0].split()
    if result:
        cache_dict[host] = int(result[0])
    else:
        cache_dict[host] = 0
    #return result


'''
process the cache ant memory result,for starting the new instance
'''
def process(cache,memory, size, count):
    single_cache_size = size / count
    times = 0
    port_dict = {}
    mem_cache_dict = {}
    dest_result_dict = {}
    l = json.loads(urllib.urlopen(instance_api).read())
    for i in l:
        ip = str(i.split(':')[0])
        port = str(i.split(':')[1])
        if port_dict.has_key(ip):
            port_dict[ip].append(port)
        else:
            port_dict[ip] = port.split()
    
    for k , v in memory.items():
        '''for sorting memory_dict and cache_dict,filte top 20'''
        mem_cache_dict[k] = int(v - cache[k])
    sortd_mem_cache_dict = sorted(mem_cache_dict.items(),key=lambda d:d[1],reverse=True)
    for i in range(20):
        key = sortd_mem_cache_dict[i][0]
        value = sortd_mem_cache_dict[i][1]
        dest_result_dict[key] = value

    for info in sorted(dest_result_dict.items(), key=lambda d:d[1],reverse=True):
        host = info[0]
        if times < count:
            if int(info[1]) - single_cache_size > 3000:
                while True:
                    new_port = random.randint(11211, 11230)
                    if new_port in port_dict[info[0]]:
                        continue
                    else:
                        dest_port = new_port
                        break
                start_mc_cmd = '%s -d -u nobody -m %s -p %s -A -c 10240'%(memcached_binary, single_cache_size, dest_port)
                print "===================== new instance nifo ====================="
                print "starting memcached on " ,host, " ",dest_port
                print "the cmd is: ", start_mc_cmd
                #ssh_command(host, start_mc_cmd)

                memcached_monitor_conf = ssh_command(host, "locate memcached_monitor.conf")[0].split('\n')[0]
                print "memcached_monitor_conf path is(Make sure the path is correct):",memcached_monitor_conf
                #ssh_command(host, "echo %s >> %s"%(start_mc_cmd, memcached_monitor_conf))
                #ssh_command(host, "echo %s >> /etc/rc.local"%start_mc_cmd)
                print "=========================== end ============================="
                print "\n"
            else: continue
                
            times += 1


def main(argv):
    if not argv:
        usage()
        sys.exit()
    try:
        opts, args = getopt.getopt(argv, "hs:c:", ["help", "size=", "count="])
    except getopt.GetoptError,err:
        print err
        usage()
        sys.exit()

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-s"):
            size = int(arg)
        elif opt in ("-c"):
            count = int(arg)
        else:
            usage()
            sys.exit()

    cacheList = [str(i) for i in json.loads(urllib.urlopen(server_index_api).read())]
    cacheList.remove("10.127.26.110")
    cacheList.remove("10.127.30.31")
    cacheList.remove("10.127.30.32")
    cacheList.remove("10.127.30.33")
    print cacheList
    wm = WorkerManager(17)
    for host in cacheList:
        wm.add_job(get_cache_info, host, 0.1)
        wm.add_job(get_mem_info, host, 0.1)
    wm.start()
    wm.wait_for_complete()
    #pool = ThreadPool(55)
    #requests = makeRequests(get_cache_info, (cacheList))
    #requests2 = makeRequests(get_mem_info, (cacheList))
    #[pool.putRequest(req) for req in requests]
    #[pool.putRequest(req) for req in requests2]
    #pool.wait()

    process(cache_dict,mem_dict, size, count)


if __name__ == "__main__":
    cache_dict = {} #存放从cache服务器取到的服务器IP和对应的已使用memcached进程的-m数之和
    mem_dict = {}   #存放从cache服务器取到的服务器IP和对应的服务器物理内存大小
    sub_dict = {}   #存放经过prcess函数处理后的结果（物理内存-cache已使用总和）
    main(sys.argv[1:])
