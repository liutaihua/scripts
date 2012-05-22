#-*- coding:utf8 -*-
#!/usr/bin/env Python 
#author:liutaihua
#email: defage@gmail.com


"""
Usage:
    [-h|--help] [-l machinelist]

-l  memcached machine list

    cache_info is save as file that file path is '/tmp/cache_file.txt'
    memory_info is save as file that file path is '/tmp/memory_file.txt'

Example:
    python statistics_cache.py -l "127.0.0.1 10.10.1.1 10.10.1.2 10.10.1.3"
"""


import os
import sys
import time
import getopt
import random
import paramiko


#cacheList = ['10.127.26.119','10.127.26.120','10.127.26.121','10.127.26.122']
rsa_key = '~/.ssh/id_rsa'
mc_conf_path = '/opt/scripts/memcached_monitor.conf'
memcached_binary = 'memcached'

def usage():
    print __doc__


'''
执行远程服务器命令
'''
def ssh_command(host,cmd,myport=58422,user='root'):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privatekeyfile = os.path.expanduser('%s'%rsa_key)
    mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
    try:
        ssh.connect(host,port=myport,username=user,pkey=mykey)
    except Exception, e:
        ssh.connect(host,port=myport,username=user,password='XXXXX YOUR PASS')

    stdin, stdout, stderr = ssh.exec_command(cmd)
    a = stdout.readlines()
    stdout = "Successful on:[%s],exec_commands: [%s]"%(host,cmd) + " result is: " + str(a)
    print stdout


'''
取得远程服务器内存信息
'''
def get_mem_info(cachelist,myport=58422,user='root'):
    mem_result_list = []
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privatekeyfile = os.path.expanduser('%s'%rsa_key)
    mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
    for host in cachelist:
        try:
            ssh.connect(host,port=myport,username=user,pkey=mykey)
        except paramiko.AuthenticationException:
            ssh.connect(host,port=myport,username=user,password='XXXX YOUR PASS')
        stdin, stdout, stderr = ssh.exec_command('free -m')
#        a = stdout.readlines()
#        b = a[1]
#        c = b.split()
#        stdout = c[1]
        stdout = stdout.readlines()[1].split()[1]
        result = host + ':' + stdout
        mem_result_list.append(result)
    for i in mem_result_list:
        a = i.split(':')
        mem_dict[a[0]] = int(a[1])
    return mem_dict


'''
取得远程服务器所有memcached进程的-m 后的使用内存数
'''
def get_cache_info(cachelist,myport=58422,user='root'):
    cache_result_list = []
    cmd = "ps -ef|grep '%s' |grep -v 'grep'|grep -o '\-m [0-9]*'|awk  '{a=a+$2}END{print a}'"%memcached_binary
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privatekeyfile = os.path.expanduser('%s'%rsa_key)
    mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
    for host in cachelist:
        try:
            ssh.connect(host,port=myport,username=user,pkey=mykey)
        except paramiko.AuthenticationException:
            ssh.connect(host,port=myport,username=user,password='XXX YOUR PASS')
        stdin, stdout, stderr = ssh.exec_command(cmd)
#        a = stdout.readlines()
#        b = a[0]
#        c = b.split()
#        stdout = c[0]
        tmp_result = stdout.readlines()[0].split()
        if tmp_result:
            result = host + ':' + tmp_result[0]
        else:
            result = host + ':' + '0'
        cache_result_list.append(result) 
    for i in cache_result_list:
        a = i.split(':')
        cache_dict[a[0]] = int(a[1])
    return cache_dict


'''
计算远程服务器物理内存是否大于已被使用的所有memcached的-m参数值的和
'''
def process(cache,memory):
    for key , vm in memory.items():
        vc = cache.get(key,0)
        sub = int(vm) - int(vc)
        if str(sub).isdigit():
            sub_dict[key] = sub
        else :
            sub_dict[key] = "Warning!memcached_cache is too large in this memory machine."
    return sub_dict
    



'''
远程服务器上执行启动需求的memcached进程
'''
def action(sub_dict,uc,port_dict):
    for key , value in sub_dict.items():
        if str(value).isdigit() and int(value) > int(uc) :
            for k , v in port_dict.items():
                port = random.randint(11211,11215)
                if port in v:
                    pass
                else :
                    if not str(value).isdigit():
                        print "warning!ERROR...,memory is not enough on: [%s]"%key
                        continue
                    start_mc_cmd = '%s -d -u nobody -m %s -p %s -A -c 10000'%(memcached_binary, uc, port)  #指定启动memcached进程的详细参数
                    ssh_command(key,start_mc_cmd)
                    markIp = key
                break
            break
        elif str(value).isdigit() and int(value) < int(uc) :
            print "warning!your request memcached_value is too lager on machine:%s"%key
        elif not str(value).isdigit():
            print "warning!ERROR...,memory is not enough on: [%s]"%key
        else :
            pass 
    return markIp
    

def get_mc_port(cachelist,myport=58422,user='root'):
    result_list = []
    tmp_list = []
    cmd = "ps -ef|grep '%s' |grep -v 'grep'|grep -o '\-p [0-9]*'|awk '{print $2}'"%memcached_binary
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privatekeyfile = os.path.expanduser('%s'%rsa_key)
    mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
    for host in cachelist:
        try:
            ssh.connect(host,port=myport,username=user,pkey=mykey)
        except paramiko.AuthenticationException:
            ssh.connect(host,port=myport,username=user,password='XXXX YOUR PASS')
        stdin, stdout, stderr = ssh.exec_command(cmd)
        a = stdout.readlines()
        for i in a:
            tmp_list.append(i.rstrip('\n'))
        port_dict[host] = tmp_list
    return port_dict


#uc = 200
#start_mc_cmd = '/opt/app/memcached/bin/memcached -d -u nobody -m %s -p 11232 -A -c 10000'%uc  #指定启动memcached进程的详细参数

def main(argv):
    if not argv:
        usage()
        sys.exit()
    try:
        opts, args = getopt.getopt(argv, "h:l:", ["help", "cacheList="])
    except getopt.GetoptError,err:
        print err
        usage()
        sys.exit()
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-l"):
            cacheList = arg.split()
        else:
            usage()
            sys.exit()
#    cacheList = [your cache list]
    print cacheList
    cache_info = get_cache_info(cacheList)
    memory_info = get_mem_info(cacheList)
    cache_file = open('/tmp/cache_info.txt','w')
    memory_file = open('/tmp/memory_info.txt','w')
    result_mem_cache_file = open('/tmp/result_mem-cache_file.txt','w')

    for key, value in cache_info.items():
        cache_file.write("%s\n"%''.join([str(key),' ','memcache进程总占用内存大小',':',str(value)]))
    cache_file.close()
    for key, value in memory_info.items():
        memory_file.write("%s\n"%''.join([str(key),' ','物理内存大小',':',str(value)]))
    memory_file.close()

    for key, value in memory_info.items():
        if cache_dict.has_key(key):
           result = int(value) - int(cache_info[key])
           result_mem_cache_file.write("%s 剩余内存空间: %s, machines_memory: %s, sub_cache: %s\n"%(key,result, value, cache_info[key]))
    result_mem_cache_file.close()
    


if __name__ == "__main__":
    cache_dict = {} #存放从cache服务器取到的服务器IP和对应的已使用memcached进程的-m数之和
    mem_dict = {}   #存放从cache服务器取到的服务器IP和对应的服务器物理内存大小
    sub_dict = {}   #存放经过prcess函数处理后的结果（物理内存-cache已使用总和）
    port_dict = {}  #取回从cache服务器取到的已经使用的memcached的port
    main(sys.argv[1:])
    print cache_dict
    print mem_dict
