#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2010  StumbleUpon, Inc.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
"""df disk space and inode counts for TSDB """
#
# dfstat.py
#
# df.1kblocks.total      total size of fs
# df.1kblocks.used       blocks used
# df.1kblocks.available  blocks available
# df.inodes.total        number of inodes
# df.inodes.used        number of inodes
# df.inodes.free        number of inodes

# All metrics are tagged with mount= and fstype=
# This makes it easier to exclude stuff like
# tmpfs mounts from disk usage reports.

# Because tsdb does not like slashes in tags, slashes will
# be replaced by underscores in the mount= tag.  In theory
# this could cause problems if you have a mountpoint of
# "/foo/bar/" and "/foo_bar/".


import os
import socket
import subprocess
import sys
import time
import re
import threading


COLLECTION_INTERVAL = 60  # seconds
i = 0 


## {{{ http://code.activestate.com/recipes/439045/ (r2)
#!/usr/bin/env python
# -*-mode: python; coding: iso-8859-1 -*-
#
# Copyright (c) Peter Astrand <astrand@cendio.se>

import os
import string

class BackwardsReader:
    """Read a file line by line, backwards"""
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

    def __init__(self, file):
        self.file = file
        self.buf = ""
        self.file.seek(-1, 2)
        self.trailing_newline = 0
        lastchar = self.file.read(1)
        if lastchar == "\n":
            self.trailing_newline = 1
            self.file.seek(-1, 2)

# Example usage
#def main():
#    br = BackwardsReader(open('dfstat.py'))
#    stop = 10
#    while stop:
#        line = br.readline()
#        if not line:
#            break
#        print repr(line)
#        stop -=1



def main():
    throughput = 0
    stop = int(time.time()) - COLLECTION_INTERVAL
    br = BackwardsReader(open('/dev/shm/nginx_metrics/metrics.log'))
    stream_list = []
    while True:
        line = br.readline()
        if int(float(line.split()[0])) >= stop:
            domain = line.split()[1]
            upstream = re.sub('\:\d{1,5}','',line.split()[4])
            cost  = line.split()[-1]
            stream_list.append(domain + ' ' + upstream + ' ' + cost)
        else:
            all_ips = map(lambda x:x.split()[1],stream_list)
            #print all_ips
            count_list = map(lambda x:{x:all_ips.count(x)}, all_ips)
            d = {}
            for i in count_list:
                for k, v in i.items():
                    d[k] = v
            for k, v in d.items():
                print "put nginx.throughput %s %s upstream=%s"%(time.time(), v, k)
            break

if __name__ == "__main__":
    main()
