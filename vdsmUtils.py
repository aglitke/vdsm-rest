# VDSM REST API
# Copyright (C) 2011 Adam Litke, IBM Corporation
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

import time
import sys

sys.path.append('/usr/share/vdsm')
import storage.volume
import storage.sd

class vdsmException(Exception):
    def __init__(self, result):
        self.code = result['status']['code']
        self.message = result['status']['message']

    def __repr__(self):
        return 'vdsmException: code:%i, message:"%s"' \
               % (self.code, self.message)

    def __str__(self):
        return self.__repr__()

def vdsOK(d, ignore_errors=[]):
    print d
    if d['status']['code'] and d['status']['code'] not in ignore_errors:
        raise vdsmException(d)
    else:
        return d

def waitTask(s, taskid):
    while vdsOK(s.getTaskStatus(taskid))['taskStatus']['taskState'] != 'finished':
        time.sleep(3)
    vdsOK(s.clearTask(taskid))

def volumeTypeGetCode(fmt_str):
    for (k,v) in storage.volume.VOLUME_TYPES.items():
        if v == fmt_str:
            return k
    raise KeyError("Invalid volume type string: %s" % fmt_str)

def sdTypeGetCode(fmt_str):
    for (k,v) in storage.sd.DOMAIN_TYPES.items():
        if v == fmt_str:
            return k
    raise KeyError("Invalid storage domain type string: %s" % fmt_str)
