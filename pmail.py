#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author:   yanglei@snda.com, zhangjing.jack@snda.com, liutaihua@snda.com
# created:  circa 2010-05
# vim conf: set et, ts=4, sw=4

"""
Mandatory:
    -t|--to             a comma separated list of mail recipients

Optional:
    -a|--attachments    path to your mail attachments
    -s|--subject        the subject of your mail
    -c|--content        the body of your mail
    -f|--from           the from address displated in the received mail
    -r|--read           read attachments content for mail content
    -n|--noatt          force do not send attachments

Examples:

    pmail -t foo@bar.com                                             # shortest form, but what's the purpose to send a empty mail?
    pmail -t foo@bar.com -a /etc/resolv.conf                         # send file quickly, subject and content will be generated automatically
    pmail -t foo@bar.com,fox@bar.com -a /etc/resolv.conf,/etc/hosts  # send multiple files to multiple people
    pmail -t foo@bar.com -s "year 2046" -c "a good movied!"          # maybe you don't have a file to send?
    pmail -t foo@bar.com -r "/etc/resolv.conf"                       # slurp the given file as the content of email
    pmail -t foo@bar.com -r "/etc/resolv.conf,/etc/hosts"            # slurp multiple files
    pmail -t foo@bar.com -s "testmail" -c "test123" -a "2003.txt"    # the standard way to send mail, but it's painful to conceive subject and content, right?
"""


import os, sys, getopt, smtplib, base64, time, socket
from datetime import datetime
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.Utils import COMMASPACE, formatdate
from email import Encoders

# in MB
attachment_max_size = 10
subject = ''
content = ''
noattach = False
no_att = False

def main(argv):
    if not argv:
        usage()
        sys.exit()
    try:
        opts, args = getopt.getopt(argv, "hm:u:p:s:t:f:c:a:r:", ["help", "mail=", "user=", "passwd=", "subject=", "to=", "content=", "attachments=", "read="])
    except getopt.GetoptError,err:
        print err
        usage()
        sys.exit()

    mail_host="mail.snda.com"
    username="ptwarn@snda.com"
    passwd="8ikju76yh"
    global subject, content, noattach, read_list, read

    attachment_list = []
    read_list = []
    attachments = False
    read = False
    to_addr = False

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-m", "--mail"):
            mail_host = arg
        elif opt in ("-u", "--user"):
            username = arg
        elif opt in ("-p", "--passwd"):
            passwd = arg
        elif opt in ("-s", "--subject"):
            subject = arg
        elif opt in ("-t", "--to"):
            to_addr = arg
        elif opt in ("-c", "--content"):
            content = arg
        elif opt in ("-r", "--read"):
            read = arg
        elif opt in ("-a", "--attachments"):
            attachments = arg
        elif opt in ("-n", "--noatt"):
            no_att = arg
        else:
            usage()
            sys.exit()

    if not to_addr:
        usage()
        sys.exit()

    # in case we've no attachment to send
    if attachments:
        attachment_list = [ i.strip() for i in attachments.split(",")]
    else:
        noattach = True
    

    if subject.__len__ < 1:
        subject = '[pmail] sent from:%s' % getLocalIp()
    else:
        subject += " [pmail] sent from:%s" % getLocalIp()

    if not content:
        if read:
            read_list = [i.strip() for i in read.split(",")]
            #content  = "%s\n" % getAllAttachMD5(read_list)
            for file in read_list:
                #content += "\n# file: %s\n\n" % file
                content += open(file).read()
        elif attachment_list:
            #content  = "%s\n" % getAllAttachMD5(attachment_list)
            for file in attachment_list:
                #content += "\n# file: %s\n\n" % file
                content += open(file).read()

            noattach = False
        elif noattach:
            content = 'there is no attachement(s)'
        #else:
        #    content += getAllAttachMD5(attachment_list)


    to_list = to_addr.split(",")

    if noattach:
        send_mail(mail_host, username, passwd, subject, to_list, content, False)
    else:
        send_mail(mail_host, username, passwd, subject, to_list, content, attachment_list)

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
    
    msg.preamble = 'This is a multi-part message in MIME format.'

    if read:
        for f in read_list:
            if f.endswith('.html'):
                msg_text = MIMEText(content, 'html')
            else:
                msg_text = MIMEText(content, 'plain', 'utf-8')
        msg.attach(msg_text)
    elif attachment_list:
        for f in attachment_list:
            if f.endswith('.html'):
                content_trans = content.replace('\n','<br>')
                msg_text = MIMEText(content_trans, 'html')
            else:
                msg_text = MIMEText(content, 'plain', 'utf-8')

    #msg.attach(msg_text)

    if noattach:
        pass
    elif read:
        pass
    else:
        handle_attachments(msg, attachment_list)

    # Message is fully built now
    try:
        try:
            s = smtplib.SMTP()
        except socket.error, msg:
            print 'please modify your /etc/hosts, add a reverse entry to match your `uname -n` output'
            return False

        s.connect(mail_host)

        # mail.snda.com is crappy, cram-md5 is not supported
        s.docmd("AUTH LOGIN", base64.b64encode(username))
        s.docmd(base64.b64encode(passwd), "")

        s.sendmail(username, to_list, msg.as_string())
        print 'send succeed!'
        s.close()
        return True
    except Exception, e:
        print str(e)
        return False

def usage():
    print __doc__

if __name__ == '__main__':
    main(sys.argv[1:])


