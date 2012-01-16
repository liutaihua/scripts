#!/bin/sh
# duming@snda.com
# create:   2011-08-12
# modified: 2011-08-13

if [ $# != 6 ]
then
   echo Error! Please usage: $0 VM_NAME CPU_COUNTS MEM_SIZE BIT VNC_PORT NET_BRIDGE
   echo Example:$0 ecardsrv01 4 3700 x86\|x64 11 vlan22
   echo DISK_SIZE\(DEFAULT C:15G  D:43G\)
   echo Quit!
   exit 1
fi

VMNAME=$1
CPU=$2
MEM=$3
BIT=$4
VNC=$5
BRIDGE=$6
DISK=43G
VG=xenvg

DAY=`date +%Y%m%d`

IMG_DIR=/opt/data/xen
CONFIG_DIR=/opt/conf/xen
LOG_DIR=/opt/logs/xen
LOG_PATH=$LOG_DIR/createWindowsHost.log
IMG_NAME=windows2003_$BIT.img.gz

if [ $BIT == "x86" ]; then
    IMG_MD5=ffb09c62e2d0c9faf57612d6bf1c6948
elif [ $BIT == "x64" ]; then
    IMG_MD5=6dfafab83ca994a9795e0002610f22ac
else
    echo "error bit"
    exit 1
fi

IMG_PATH=$IMG_DIR/$IMG_NAME

VM_FULLNAME=windows-$BIT-$VNC-$VMNAME-$DAY
VM_FULLNAME_DATA=$VM_FULLNAME-DATA
VM_FULLNAME_PATH=/dev/$VG/$VM_FULLNAME
VM_FULLNAME_DATA_PATH=/dev/$VG/$VM_FULLNAME_DATA

CONFIG_PATH=$CONFIG_DIR/$VM_FULLNAME

if [ ! -d $IMG_DIR ]; then
    mkdir -p $IMG_DIR
fi

if [ ! -d $CONFIG_DIR ]; then
    mkdir -p $CONFIG_DIR
fi

if [ ! -d $LOG_DIR ]; then
    mkdir -p $LOG_DIR
fi

if [ `md5sum $IMG_PATH | awk '{print $1}'` != $IMG_MD5 ]; then
    echo Error! Windows image\($IMG_PATH\) is bad! Fail! 
    exit 1
fi

if [ -f $CONFIG_PATH ]; then
    echo Error! The same name Vhost config file\($CONFIG_PATH\) already exists! Fail!
    exit 1
fi

echo `date '+%Y-%m-%d %H:%M:%S'`  Create Vhost Disk
lvcreate -L 15G -n $VM_FULLNAME $VG
lvcreate -L $DISK -n $VM_FULLNAME_DATA $VG

echo `date '+%Y-%m-%d %H:%M:%S'`  Save Vhost confige file at $CONFIG_PATH
echo "\
import os, re
arch = os.uname()[4]
if re.search('64', arch):
        arch_libdir = 'lib64'
else:
        arch_libdir = 'lib'
kernel = '"/usr/lib/xen/boot/hvmloader"'
builder = 'hvm'
name = '"$VM_FULLNAME"'
memory = $MEM
disk = ['phy:$VM_FULLNAME_PATH,hda,w', 'phy:$VM_FULLNAME_DATA_PATH,hdb,w']
vif = ['type=ioemu, bridge=$BRIDGE']
vcpus=$CPU
on_reboot = 'restart'
on_crash = 'restart'
boot = 'c'
sdl=0
vnc=1
vncunused=1
vnclisten='"0.0.0.0"'
vncpasswd=''
vncdisplay=$VNC
apic=1
acpi=1
stdvga=0
localtime=1
rtc_timeoffset='0'
serial='pty'
usbdevice='tablet'
on_xend_start='"start"'
on_xend_stoip='"shutdown"'"> $CONFIG_PATH

echo `date '+%Y-%m-%d %H:%M:%S'`  VHost creating ..... Please wait, need long time\(aboute 20 minutes\) ..... 
gzip -dc $IMG_PATH | dd of=$VM_FULLNAME_PATH

echo `date '+%Y-%m-%d %H:%M:%S'`  VHost starting ..... Please wait, need aboute a minute .....
echo VNC port is $VNC
xm new $CONFIG_PATH
xm start $VM_FULLNAME
echo "xm start $VM_FULLNAME" >> /etc/rc.local
echo `date '+%Y-%m-%d %H:%M:%S'`  Succeed!!
