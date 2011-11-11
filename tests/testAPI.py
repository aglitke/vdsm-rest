#!/usr/bin/env python
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

import unittest
import urllib2
import json
import uuid
import time
import sys

host = "http://localhost:8080/vdsm-api"

def request(url, obj=None):
    headers = { 'content-type': 'application/json',
                'Accept': 'application/json' }
    if obj is not None:
        data = json.dumps(obj)
    else:
        data = None
    req = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(req).read()
    if response == "":
        return None
    else:
        return json.loads(response)

def wait_task(task, maxTries=20):
    global host
    url = "%s/tasks/%s" % (host, task['id'])
    while task['state'] not in ('finished', 'failed', 'recovered'):
        maxTries -= 1
        if maxTries <= 0: return False
        time.sleep(2)
        task = request(url)
    return True

def create_image(sd):
    global host
    url = "%s/storagedomains/%s/images/create" % (host, sd)
    imgUUID = str(uuid.uuid4())
    data = { "id": imgUUID }
    task = request(url, data)
    if wait_task(task):
        return imgUUID
    return None

def delete_image(sd, img):
    global host
    url = "%s/storagedomains/%s/images/%s/delete" % (host, sd, img)
    data_str = "{}"
    task = request(url, data_str)
    return wait_task(task)

def create_volume(sd, img, sizeMB, desc,
                  leaf=True, sparse=True, raw=True):
    global host
    url = "%s/storagedomains/%s/images/%s/volumes/create" % (host, sd, img)
    
    cap = sizeMB * 1024 * 1024
    volType = "LEAF" if leaf else "INTERNAL"
    type = "SPARSE" if sparse else "PREALLOCATED"
    format = "RAW" if raw else "COW"    
    volUUID = str(uuid.uuid4())
    data = { "id": volUUID, "description": desc,
             "voltype": volType, "type": type, "disktype": "8",
             "format": format, "capacity": cap }
    task = request(url, data)
    if wait_task(task):
        return volUUID
    return None

def delete_volume(sd, img, vol):
    global host
    url = "%s/storagedomains/%s/images/%s/volumes/%s/delete" % \
            (host, sd, img, vol)
    task = request(url, {})
    return wait_task(task)

def create_domain(sddef):
    global host
    url = "%s/storagedomains/create" % host
    request(url, sddef)

class RestTest(unittest.TestCase):
    def image_and_volume_create_delete(self):
        sd = '24862862-f29b-40a6-8698-976dcfc42023'
        img = create_image(sd)
        self.assertNotEqual(None, img)
        vol = create_volume(sd, img, 1024, "Test Volume")
        self.assertNotEqual(None, vol)
        self.assertTrue(delete_volume(sd, img, vol))
        self.assertTrue(delete_image(sd, img))

    def do_second_domain(self):
        sddef = { "id": "a76d93e2-53da-4200-bef6-38deac6a5681",
                  "type": "LOCALFS",
                  "name": "Test Domain 2",
                  "remotePath": "/var/lib/vdsm/storage2" }
        request("%s/storagedomains/create" % host, sddef)
        request("%s/storagedomains/%s/attach" % (host, sddef['id']),
                {"storagepool": "6e4d6a96-d3da-419c-8905-b5eec55c44e2"})
        #print "*** Perform any extra commands you want ***"
        #sys.stdin.readline()
        request("%s/storagedomains/%s/detach" % (host, sddef['id']), {})
        request("%s/storagedomains/%s/delete" % (host, sddef['id']), {})
        
                  
    def test_storage_setup_teardown(self):
        global host
        spdef = { "id": "6e4d6a96-d3da-419c-8905-b5eec55c44e2",
                  "name": "Local storage pool",
                  "type": "LOCALFS",
                  "master_ver": "0",
                  "master_uuid": "09adc482-e0f8-4b14-a73d-1bc4703e09f2" }
        sddef = { "id": "09adc482-e0f8-4b14-a73d-1bc4703e09f2",
                  "type": "LOCALFS",
                  "name": "Test Domain",
                  "remotePath": "/var/lib/vdsm/storage" }
        imgdef = { "id": "f9ef39d2-8b1e-43b9-8977-7e1ba01daa58" }
        voldef = { "id": "47bd7538-c48b-4b94-ba94-cf8922151d86",
                   "description": "Test create volume",
                   "voltype": "LEAF",
                   "type": "SPARSE",
                   "disktype": "8",
                   "format": "RAW",
                   "capacity": 10737418240 }
        keyarg = { "key": "mykey" }

        # Create domain
        request("%s/storagedomains/create" % host, sddef)
        # Create pool
        request("%s/storagepools/create" % host, spdef)
        # Connect to pool
        request("%s/storagepools/%s/connect" % (host, spdef['id']), keyarg)
        # Start SPM
        task = request("%s/storagepools/%s/spmstart" % (host, spdef['id']), {})
        wait_task(task)
        #Create image
        url = "%s/storagedomains/%s/images/create" % (host, sddef['id'])
        task = request(url, imgdef)
        wait_task(task)
        # Create volume
        url = "%s/storagedomains/%s/images/%s/volumes/create" % \
               (host, sddef['id'], imgdef['id'])
        task = request(url, voldef)
        wait_task(task)
        
        self.do_second_domain()
        
        # Delete volume
        url = "%s/storagedomains/%s/images/%s/volumes/%s/delete" % \
            (host, sddef['id'], imgdef['id'], voldef['id'])
        task = request(url, {})
        wait_task(task)
        # Delete image
        url = "%s/storagedomains/%s/images/%s/delete" % \
               (host, sddef['id'], imgdef['id'])
        task = request(url, {})
        wait_task(task)
        # Deactivate domain
        request("%s/storagedomains/%s/deactivate" % (host, sddef['id']), {})
        # Detach domain
        request("%s/storagedomains/%s/detach" % (host, sddef['id']), {})
        # Stop SPM
        request("%s/storagepools/%s/spmstop" % (host, spdef['id']), {})
        # Disconnect pool
        request("%s/storagepools/%s/disconnect" % (host, spdef['id']), keyarg)
        # Delete domain
        request("%s/storagedomains/%s/delete" % (host, sddef['id']), {})
        # Delete pool
        request("%s/storagepools/%s/delete" % (host, spdef['id']), keyarg)

if __name__ == '__main__':
    unittest.main()
