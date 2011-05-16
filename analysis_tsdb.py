#-*- coding:utf8 -*-
#!/usr/bin/env Python 
#author:liutaihua
#email: defage@gmail.com
"""
Usage:
    [-h|--help] [-st start date] [-et end date] [-i items] [-c host]

-s(--start_time)   start time,like this format:2011/03/20-12:00:00
-e(--end_time)     end time, like this format:2011/03/21-12:00:00


Example:
    python analysis_tsdb.py -s 2011/03/20-12:00:00 -e 2011/03/21-12:00:00
"""
import httplib
import urllib
import getopt
import os, sys
import re
#import json
import commands



import time
import smtplib, mimetypes, base64
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEImage import MIMEImage

import os, sys, getopt, smtplib, base64, time
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.Utils import COMMASPACE, formatdate
from email import Encoders

attachment_max_size = 10
subject = 'opentsdb'
content = 'opentsdb'
mail_host = 'mail.snda.com'
username = 'ptwarn@snda.com'
passwd = '8ikju76yh'
frommail = 'ptwarn@snda.com'
to_list = ['liutaihua@snda.com']

def getAbsoultePath(attachment):
    cur = os.getcwd()
    return os.path.join(cur, attachment)

def getAllAttachMD5(attachment_list):
    rc = {}
    for attachment in attachment_list:
        abs_attach = getAbsoultePath(attachment)
        rc[abs_attach] = getOneAttachMD5(abs_attach)
    
    msg = ''
    for k,v in sorted(rc.items()):
        msg = msg + v + ' ' + k + "\n"
    
    return msg

def getOneAttachMD5(attachment):
    try: 
        from hashlib import md5
    except ImportError:
        from md5 import md5
    md5 = md5()

    try:
        f = open(attachment, 'rb')
        for chunk in iter(lambda: f.read(8192), ''):
            md5.update(chunk)

        return md5.hexdigest()
    except Exception, e:
        print str(e)
        sys.exit()

def getLocalIp():
    from socket import socket, SOCK_DGRAM, AF_INET
    s = socket(AF_INET, SOCK_DGRAM)
    s.connect(('8.8.8.8',0))
    LocalIp = s.getsockname()[0]
    s.close()
    return LocalIp

def handle_attachments(msg, attachment_list):
    for f in attachment_list:
        try:
            if (os.path.getsize(f)/1024/1024 > attachment_max_size):
                raise Exception('Sorry, max allowed attachment size is ' + str(attachment_max_size) + 'mb.')

            handle = open(f, 'rb')
            part = MIMEBase('application', "octet-stream")
            part.set_payload(handle.read())
            handle.close()
            Encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachments; filename="%s"' % os.path.basename(f))
            msg.attach(part)
        except Exception, e:
            print str(e)
            sys.exit()
    return msg


def send_mail(mail_host, username, passwd, subject, to_list, content, attachment_list):
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = username
    msg['To'] = COMMASPACE.join(to_list)
    msg['Date'] = formatdate(localtime=True)
    
    #msg['CC'] = "zhangjing.jack@snda.com"
    msg.preamble = 'This is a multi-part message in MIME format.'

    msg_text = MIMEText(content, 'plain', 'utf-8')
    msg.attach(msg_text)

    handle_attachments(msg, attachment_list)

    # Message is fully built now
    try:
        s = smtplib.SMTP()
        s.connect(mail_host)

        # mail.snda.com is crappy, cram-md5 is not supported
        s.docmd("AUTH LOGIN", base64.b64encode(username))
        s.docmd(base64.b64encode(passwd), "")

        # try:
        #     # attmept a 'standard' login
        #     s.login(mail_user,mail_passwd)
        # except smtplib.SMTPAuthenticationError, e:
        #     # if login fails, try again using a manual plain login method
        #     s.docmd("AUTH LOGIN", base64.b64encode(mail_user))
        #     s.docmd(base64.b64encode(mail_passwd), "")

        print 'sending mail ...'
        s.sendmail(username, to_list, msg.as_string())
        s.close()
        return True
    except Exception, e:
        print str(e)
        return False


def usage():
    print __doc__



start_time = ''
end_time = ''
def main(argv):
    #start_time = commands.getoutput('date +%m%d') + "-00:00:00"
    #end_time = commands.getoutput('date +%m%d') + "-10:01:00"
    global start_time, end_time
    #if not argv:
    #    usage()
    #    sys.exit()
    try:
        opts, args = getopt.getopt(argv, "h:s:e:", ["help", "start_time=","end_time="])
    except getopt.GetoptError,err:
        print err
    #    usage()
    #    sys.exit()
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-s", "--start_time"):
            start_time = arg.split()[0]
        elif opt in ("-e", "--end_time"):
            end_time = arg.split()[0]
        else:
            pass
    #        usage()
    #        sys.exit()
    if not start_time:
        start_time = commands.getoutput('date -d "1 week ago" +%Y/%m/%d') + "-00:00:00"
    if not end_time:
        end_time = commands.getoutput('date +%Y/%m/%d') + "-00:01:00"
    #domain_list = json.loads(urllib.urlopen('http://op.sdo.com/msla/suggest?type=tagv&q=').read())
    #dest_domain_list = []
    #for domain in domain_list:
    #    p = re.compile('.*\.sdo\.com')
    #    if p.match(domain):
    #        dest_domain_list.append(p.match(domain).group())
    url_all = ''.join(['/msla/q?','start=',start_time,'＆','end=',end_time,'&m=sum:nginx.throughput','{domain=*}','&ascii'])
    url_error = ''.join(['/msla/q?','start=',start_time,'＆','end=',end_time,'&m=sum:nginx.error','{domain=*}','&ascii'])

    print url_all , url_error

    date = ''.join(start_time.split('/')[1:]).split('-')[0] + "-" + ''.join(end_time.split('/')[1:]).split('-')[0]

    server_error = httplib.HTTPConnection("op.sdo.com")
    server_all = httplib.HTTPConnection("op.sdo.com")

    server_error.request('GET',url_error)
    server_all.request('GET',url_all)

    info_error = server_error.getresponse().read()
    info_all = server_all.getresponse().read()

    error_file_name = '/tmp/%s-nginx.error.log'%date
    all_file_name = '/tmp/%s-nginx.throughput.log'%date


    file_error = open(error_file_name, 'w')
    file_all = open(all_file_name, 'w')

    file_error.write(info_error)
    file_all.write(info_all)

    file_all.close()
    file_error.close()

    err_command = "awk '{a[$5] +=$3}END{for(i in a) print i,a[i]}' %s |grep 'sdo.com'"%error_file_name
    all_command = "awk '{a[$5] +=$3}END{for(i in a) print i,a[i]}' %s |grep 'sdo.com'"%all_file_name


    result_error = commands.getoutput(err_command)
    result_all = commands.getoutput(all_command)


    filetmp = open('/tmp/test.txt','w')
    filetmp.write(result_error)
    filetmp.write("=====================================================================================")
    filetmp.write(result_all)

    dict = {}
    dict2 = {}
    for i in result_error.split('\n'):
        if i.split()[1] != '0':
            dict[i.split()[0]] = i.split()[1]
    for i in result_all.split('\n'):
        dict2[i.split()[0]] = i.split()[1]
    mail_msg_file = open('/tmp/opentsdb_msg.txt','w')
    availability_sub_list = []
    availability = 0
    error_sub = 0
    all_sub = float(0)
    for key, value in dict.items():
        if dict2.has_key(key):
            tmp_v = "%.5f"%(float(100)-(float(value)/float(dict2[key]))*100)
            availability += float(tmp_v)
            availability_sub_list.append("%.5f"%(float(100)-(float(value)/float(dict2[key]))*100))
            error_sub += int(value)
            all_sub += float(dict2[key])
            mail_msg = ''.join([key.split('=')[1]," ", "%.5f"%(float(100)-(float(value)/float(dict2[key]))*100)," ", value, " ", dict2[key]])
            mail_msg_file.write('%s\n'%mail_msg)
            print key, "%.5f"%((float(value)/float(dict2[key]))*100), value, dict2[key]
    availability_dest = availability / len(availability_sub_list)
    sub_msg = "总计:" + "%s"%availability_dest + "    " "%s"%error_sub + "    " + "%s"%all_sub
    mail_msg_file.write(sub_msg) 
        
    mail_msg_file.close()

    subject = 'opentsdb-data[%s]'%date
    content = 'MSLA数据，见附件' 
    attachment_list = ['/tmp/opentsdb_msg.txt']
    send_mail(mail_host, username, passwd, subject, to_list, content, attachment_list)




if __name__ == "__main__":
    main(sys.argv[1:])



