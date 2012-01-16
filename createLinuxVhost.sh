#!/bin/bash
set -e

if [ $# != 5 ]
then
   echo "usage: "$0" VMNAME CPU_NUM memorySize bit BridgeName"
   echo "Example:$0 sas01 4 3700 x64|x86 vlan22"
   echo DISK_SIZE\(DEFAULT SWAP:4G  ROOT:53G\)
   exit 1
fi
   

vg=xenvg
swap=4g
root=53g
data=0g
VMNAME=$1
cpu=$2
mem=$3
BIT=$4
BRIDGE=$5

DAY=`date +%Y%m%d`

IMG_DIR=/opt/data/xen
CONFIG_DIR=/opt/conf/xen
LOG_DIR=/opt/logs/xen
LOG_PATH=$LOG_DIR/createWindowsHost.log
if [ $BIT == "x86" ]; then
    IMG_NAME=_system_linux_centos54.i386.img
    IMG_MD5=b65282165f07eb1a61ce26b4454d8340
elif [ $BIT == "x64" ]; then
    IMG_NAME=_system_linux_centos54.x86_64.img
    IMG_MD5=86e18c509be4af86981d0eae0e8cf6b4
else
    echo "error bit"
    exit 1
fi

echo $IMG_NAME

IMG_PATH=$IMG_DIR/$IMG_NAME

VM_FULLNAME=linux-$BIT-$VMNAME-$DAY
VM_FULLNAME_ROOT=$VM_FULLNAME-ROOT
VM_FULLNAME_SWAP=$VM_FULLNAME-SWAP
VM_FULLNAME_DATA=$VM_FULLNAME-DATA
VM_FULLNAME_ROOT_PATH=/dev/$vg/$VM_FULLNAME_ROOT
VM_FULLNAME_SWAP_PATH=/dev/$vg/$VM_FULLNAME_SWAP
VM_FULLNAME_DATA_PATH=/dev/$vg/$VM_FULLNAME_DATA

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

if [ ! -f $IMG_PATH ]
  then
    echo "`date '+%Y-%m-%d %H:%M:%S'`  Downloading Linux image to $IMG_PATH ... Please wait, need few minutes"
    ftpserver='10.65.11.30'
    ftpuser='deploy'
    ftppass='deploy@sd123'
    ftp -n $ftpserver << EOF
        user $ftpuser $ftppass
        get xen/imgs/$IMG_NAME $IMG_PATH
        bye
EOF
fi

if [ `md5sum $IMG_PATH | awk '{print $1}'` != $IMG_MD5 ]; then
    echo Error! Linux image\($IMG_PATH\) is bad! Fail!
    exit 1
fi

if [ -f $CONFIG_PATH ]; then
    echo Error! The same name Vhost config file\($CONFIG_PATH\) already exists! Fail!
    exit 1
fi

lvcreate -L $swap -n $VM_FULLNAME_SWAP $vg
lvcreate -L $root -n $VM_FULLNAME_ROOT $vg

mkswap $VM_FULLNAME_SWAP_PATH
mkfs.ext3 $VM_FULLNAME_ROOT_PATH

mount $VM_FULLNAME_ROOT_PATH /mnt
tar zxf $IMG_PATH -C /mnt

if [ $data != 0 ] && [ $data != "0g" ]
then
  lvcreate -L $data -n $VM_FULLNAME_DATA $vg
  mkfs.ext3 $VM_FULLNAME_DATA_PATH
  echo "\
bootloader = '/usr/bin/pygrub'
memory = "$mem"
name = '"$VM_FULLNAME"'
vcpus = "$cpu"
vif = [ 'bridge=$BRIDGE' ]
disk = [ 'phy:$VM_FULLNAME_ROOT_PATH,sda2,w','phy:$VM_FULLNAME_SWAP_PATH,sda1,w','phy:$VM_FULLNAME_DATA_PATH,sda3,w' ]
localtime=1
rtc_timeoffset='0'" > $CONFIG_PATH

  if [ ! -d "/mnt/data" ]
  then
    mkdir /mnt/data
  fi

  sed -i 's/home/data/g' /mnt/etc/fstab
else
  echo "\
bootloader = '/usr/bin/pygrub'
memory = "$mem"
name = '"$VM_FULLNAME"'
vcpus = "$cpu"
vif = [ 'bridge=$BRIDGE' ]
disk = [ 'phy:$VM_FULLNAME_ROOT_PATH,sda2,w','phy:$VM_FULLNAME_SWAP_PATH,sda1,w' ]
localtime=1
rtc_timeoffset='0'" > $CONFIG_PATH
  sed -i '/home/d' /mnt/etc/fstab

fi

umount /mnt
echo "Guest OS "$VMNAME" created!"

#password: Welcome123

xm new $CONFIG_PATH
xm start $VM_FULLNAME
echo "xm start $VM_FULLNAME" >> /etc/rc.local
echo `date '+%Y-%m-%d %H:%M:%S'`  Succeed!!
