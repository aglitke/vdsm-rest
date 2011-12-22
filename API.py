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

import sys
import json
import uuid
import cherrypy
from utils import *
from vdsmUtils import *
import Storage.LocalDB

sys.path.append('/usr/share/vdsm')
import vdscli
from storage.sd import LOCALFS_DOMAIN, DATA_DOMAIN
from storage.volume import COW_FORMAT, SPARSE_VOL, LEAF_VOL, BLANK_UUID, PREALLOCATED_VOL
from storage.storage_exception import *

def validate_method(allowed):
    method = cherrypy.request.method.upper()
    if method not in allowed:
        raise cherrypy.HTTPError(405)
    return method

class vdsmObjectError(Exception): pass

# The requested resource could not be found
class ResourceNotFound(vdsmObjectError): pass

# An invalid argument was supplied
class InvalidArgument(vdsmObjectError): pass

# The requested operation is not valid
class InvalidOperation(vdsmObjectError):
    def __init__(self, message="Invalid Operation"):
        self.message = message

def lookup_sp(conn, sdUUID):
    """
    We need to populate spUUID specially, since it has not been passed
    in as part of the URI.  Eventually SP will be going away and this can
    be removed.
    """
    ret = conn.vdsm.getStorageDomainInfo(sdUUID)
    vdsOK(ret)
    return ret['info']['pool'][0]

def lookup_volume(conn, uuid):
    """
    XXX: Consider making this a part of the VDSM API
    Given a volume UUID, search all connected storage domains and return
    a Volume object if found
    """
    ret = conn.vdsm.getConnectedStoragePoolsList()
    vdsOK(ret)
    spList = ret['poollist']
    for sp in spList:
        ret = conn.vdsm.getStorageDomainsList(sp)
        vdsOK(ret)
        sdList = ret['domlist']
        for sd in sdList:
            ret = conn.vdsm.getImagesList(sd)
            vdsOK(ret)
            imgList = ret['imageslist']
            for img in imgList:
                ret = conn.vdsm.getVolumesList(sd, sp, img)
                vdsOK(ret)
                volList = ret['uuidlist']
                if uuid in volList:
                    volume = Volume(conn)
                    volume.lookup(uuid, sd, sp, img)
                    return volume
    raise VolumeDoesNotExist()

def json_get_or_make_id(obj):
    if 'id' not in obj or obj['id'] == '':
        return str(uuid.uuid4())
    else:
        return obj['id']

class ConnectionManager:
    def __init__(self):
        self.vdsm = vdscli.connect()
        self.storage = Storage.LocalDB.LocalDB({'path': '/var/lib/vdsm/vdsm.db'})
        self.storage.createType("vms")
        self.storage.createType("storagepools")

class Controller(object):
    def __call__(self): pass

class Task(Controller):
    def __init__(self, conn):
        self.conn = conn
        self.UUID = None
        self.target = None
        self.info = {}
        self.stats = {}

    def lookup(self, UUID):
        self.UUID = UUID
        ret = self.conn.vdsm.getTaskInfo(self.UUID)
        try:
            vdsOK(ret)
        except vdsmException, e:
            if e.code == 401: # Task id unknown
                raise ResourceNotFound()
            raise

        self.info['verb'] = ret['TaskInfo']['verb']
        ret = self.conn.vdsm.getTaskStatus(self.UUID)
        vdsOK(ret)
        self.info['message'] = ret['taskStatus']['message']
        self.info['code'] = ret['taskStatus']['code']
        self.info['result'] = ret['taskStatus']['taskResult']
        self.info['state'] = ret['taskStatus']['taskState']

    def set_target(self, target):
        self.target = target

    @cherrypy.expose
    def index(self):
        return render_template('task', { 'task': self } )

    # TODO: Add a wait method that doesn't return until the task is finished
    # This may require a callback mechanism from vdsm

class Tasks(Controller):
    def __init__(self, conn):
        self.conn = conn

    def getTasks(self):
        tasks = []
        ret = self.conn.vdsm.getAllTasksInfo()
        vdsOK(ret)
        for uuid in ret['allTasksInfo'].keys():
            tasks.append(uuid)
        return tasks

    @cherrypy.expose
    def index(self):
        tasks = self.getTasks()
        return render_template('tasks', { 'tasks': tasks })

    def _dispatch_lookup(self, uuid):
        task = Task(self.conn)
        try:
            task.lookup(uuid)
            return task
        except ResourceNotFound:
            return None

class VMDrive(Controller):
    # This is essentially a Volume with different methods and presentation
    def __init__(self, vmUUID, spUUID, sdUUID, imgUUID, volUUID):
        self.vmUUID = vmUUID
        self.spUUID = spUUID
        self.sdUUID = sdUUID
        self.imgUUID = imgUUID
        self.volUUID = volUUID

    @cherrypy.expose
    def index(self):
        data = { 'vmUUID': self.vmUUID, 'spUUID': self.spUUID,
                 'sdUUID': self.sdUUID, 'imgUUID': self.imgUUID,
                 'volUUID': self.volUUID }
        return render_template('vmdrive', data)

class VMDrives(Controller):
    def __init__(self, vm):
        self.vm = vm

    @cherrypy.expose
    def index(self):
        data = { 'vmUUID': self.vm.UUID, 'drives': self.vm.drive_list }
        return render_template('vmdrives', data)

    @cherrypy.expose
    def define(self, *args):
        validate_method(('POST',))
        rawbody = cherrypy.request.body.read()
        params = json.loads(rawbody)
        uuid = self.vm._define_drive(params['volume'])
        uri = "/vdsm-api/vms/%s/drives/%s " % (self.vm.UUID, uuid)
        raise cherrypy.HTTPRedirect(uri, 303)

    def _dispatch_lookup(self, uuid):
        for d in self.vm.drive_list:
            if d['volume'] == uuid:
                return VMDrive(self.vm.UUID, d['sp'], d['sd'],
                               d['image'], d['volume'])
        return None

class VMNics(Controller):
    def __init__(self, vm):
        pass

class VM(Controller):
    def __init__(self, conn):
        self.conn = conn
        self.UUID = None
        #self.drive_list = None
        #self.nic_list = None
        
        self.drives = VMDrives(self)
        self.drives.exposed = True
        self.nics = VMNics(self)
        self.nics.exposed = True

    def _get_stats(self):
        stats = { 'status': 'Down' }
        ret = self.conn.vdsm.getVmStats(self.UUID)
        try:
            vdsOK(ret)
        except vdsmException, e:
            if e.code == 1: # Virtual machine does not exist
                self.stats = stats
                return
            else:
                raise
        
        for k in ('displayPort', 'displayIp', 'status', 'pauseCode', 'guestIPs'):
            if k in ret['statsList'][0]:
                stats[k] = ret['statsList'][0][k]
        self.stats = stats

    def _lookup(self, UUID):
        """
        Load VM from storage.  VM is stored in the native VDSM file format
        """
        config = self.conn.storage.getItem('vms', UUID)
        if config is None:
            raise ResourceNotFound()

        self.UUID = UUID
        self.name = config['vmName']
        self.memory = config['memSize']
        self.cpus = config.get('smp', 1)
        self.boot = config.get('boot', 'c')
        self.floppy = config.get('floppy', None)
        self.cdrom = config.get('cdrom', None)
        self.sound = config.get('soundDevice', None)
        self.display = config.get('display')
        
        self.drive_list = []
        for d in config.get('drives', []):
            drive = { 'sd': d['domainID'], 'sp': d['poolID'],
                      'image': d['imageID'], 'volume': d['volumeID'] }
            self.drive_list.append(drive)
        
        self.nic_list = []
        if 'macAddr' in config:
             macs = config['macAddr'].split(',')
             models = config['nicModel'].split(',')
             bridges = config['bridge'].split(',')
             for i in xrange(0, len(macs)):
                 self.nic_list.append({ 'macAddr': macs[i], 'nicModel': models[i],
                                    'bridge': bridges[i] })
        self._get_stats()

    def _to_native(self):
        """
        Convert this VM class into a native VDSM representation and create it
        in storage.
        """
        c = {}
        c['vmId'] = self.UUID
        c['vmName'] = self.name
        c['memSize'] = str(self.memory)
        c['smp'] = str(self.cpus)
        c['boot'] = self.boot
        c['display'] = self.display
        if self.floppy: c['floppy'] = self.floppy
        if self.cdrom: c['cdrom'] = self.cdrom
        if self.sound: c['soundDevice'] = self.sound
        
        c['drives'] = []
        for d in self.drive_list:
            drive = { 'domainID': d['sd'], 'poolID': d['sp'],
                      'imageID': d['image'], 'volumeID': d['volume'] }
            c['drives'].append(drive)
        
        c['macAddr'] = ','.join(map(lambda x: x['macAddr'], self.nic_list))
        c['nicModel'] = ','.join(map(lambda x: x['nicModel'], self.nic_list))
        c['bridge'] = ','.join(map(lambda x: x['bridge'], self.nic_list))
        return c

    def new_from_json(self, data):
        """
        Initialize this VM instance with properties from a JSON object
        """
        obj = json.loads(data)
        self.UUID = json_get_or_make_id(obj)
        self.name = obj['name']
        self.memory = obj['memory']
        self.cpus = obj.get('cpus', 1)
        self.boot = obj.get('boot', 'c')
        self.floppy = obj.get('floppy', None)
        self.cdrom = obj.get('cdrom', None)
        self.sound = obj.get('soundDevice', None)
        self.display = obj.get('display', 'vnc')
        
        # Support shortcut drives and nics specification
        self.drive_list = []
        for d in obj.get('drives', []):
            drive = { 'sd': d['storagedomain'], 'sp': d['storagepool'],
                      'image': d['image'], 'volume': d['volume'] }
            self.drive_list.append(drive)
        for volUUID in obj.get('drive_volumes', []):
            volume = lookup_volume(self.conn, volUUID)
            drive = { 'sd': volume.sdUUID, 'sp': volume.spUUID,
                      'image': volume.imgUUID, 'volume': volume.UUID }
            self.drive_list.append(drive)
        
        self.nic_list = []
        for n in obj.get('nics', []):
            nic = { 'macAddr': n['macAddr'], 'nicModel': n['nicModel'],
                    'bridge': n['bridge'] }
            self.nic_list.append(nic)
        self.conn.storage.createItem('vms', self.UUID, self._to_native())

    def _save(self):
        self.conn.storage.updateItem('vms', self.UUID, self._to_native())

    def _delete(self):
        # XXX: Don't delete the vm if it's running
        self.conn.storage.deleteItem('vms', self.UUID)

    def _update(self, config):
        updates = {}
        allowed = ('name', 'memory', 'cpus', 'boot', 'floppy', 'cdrom')
        for (k,v) in config.items():
            if k not in allowed:
                raise InvalidArgument("Property '%s' cannot be updated" % k)
            updates[k] = v
        for (k,v) in updates.items():
            setattr(self, k, v)
        self._save()

    def _start(self):
        config = self._to_native()
        ret = self.conn.vdsm.create(config)
        vdsOK(ret)

    def _stop(self):
        ret = self.conn.vdsm.destroy(self.UUID)
        vdsOK(ret)

    def _pause(self):
        ret = self.conn.vdsm.pause(self.UUID)
        vdsOK(ret)

    def _continue(self):
        ret = self.conn.vdsm.cont(self.UUID)
        vdsOK(ret)

    def _ticket(self, password, timeout, previous="keep"):
        ret = self.conn.vdsm.setVmTicket(self.UUID, password, timeout, previous)
        vdsOK(ret)

    def _define_drive(self, volUUID):
        for drive in self.drives:
            if drive['volume'] == volUUID:
                raise InvalidArgument("Drive '%s' already defined" % volUUID)

        volume = lookup_volume(self.conn, volUUID)
        drive = { 'sd': volume.sdUUID, 'sp': volume.spUUID,
                  'image': volume.imgUUID, 'volume': volume.UUID }
        self.drive_list.append(drive)
        self._save()
        return volume.UUID

    @cherrypy.expose
    def index(self):
        data = {}
        data['vmUUID'] = self.UUID
        for k in ( 'name', 'memory', 'cpus', 'boot', 'floppy', 'cdrom',
                   'display', 'stats'):
            data[k] = getattr(self, k)
        return render_template('vm', data)

    @cherrypy.expose
    def undefine(self, *args):
        validate_method(('POST',))
        self._delete()
        cherrypy.response.status = 204
        return

    @cherrypy.expose
    def update(self, *args):
        validate_method(('POST',))
        rawbody = cherrypy.request.body.read()
        params = json.loads(rawbody)
        self._update(params)
        raise cherrypy.HTTPRedirect("/vdsm-api/vms/%s" % self.UUID, 303)

    @cherrypy.expose
    def start(self, *args):
        validate_method(('POST',))
        self._start()
        raise cherrypy.HTTPRedirect("/vdsm-api/vms/%s" % self.UUID, 303)

    @cherrypy.expose
    def stop(self, *args):
        validate_method(('POST',))
        self._stop()
        raise cherrypy.HTTPRedirect("/vdsm-api/vms/%s" % self.UUID, 303)
    
    @cherrypy.expose
    def pause(self, *args):
        validate_method(('POST',))
        self._pause()
        raise cherrypy.HTTPRedirect("/vdsm-api/vms/%s" % self.UUID, 303)

    @cherrypy.expose
    def cont(self, *args):
        validate_method(('POST',))
        self._continue()
        raise cherrypy.HTTPRedirect("/vdsm-api/vms/%s" % self.UUID, 303)

    @cherrypy.expose
    def ticket(self, *args):
        validate_method(('POST',))
        rawbody = cherrypy.request.body.read()
        params = json.loads(rawbody)
        pw = params['password']
        timeout = params.get('timeout', 60)
        prev = params.get('previous', 'keep')
        self._ticket(pw, timeout, prev)

class VMs(Controller):
    def __init__(self, conn):
        self.conn = conn

    @cherrypy.expose
    def index(self):
        vms = self.conn.storage.getItems('vms')
        return render_template('vms', { 'vms': vms })

    @cherrypy.expose
    def define(self, *args):
        validate_method(('POST',))
        rawbody = cherrypy.request.body.read()
        print "before VM"
        vm = VM(self.conn)
        print "After VM"
        vm.new_from_json(rawbody)
        print "after load"
        raise cherrypy.HTTPRedirect("/vdsm-api/vms/%s" % vm.UUID, 303)

    def _dispatch_lookup(self, uuid):
        vm = VM(self.conn)
        try:
            vm._lookup(uuid)
            return vm
        except ResourceNotFound:
            return None

class Volume(Controller):
    def __init__(self, conn):
        self.conn = conn
        self.UUID = None
        self.imgUUID = None
        self.sdUUID = None
        self.spUUID = None
        self.info = {}
        self.path = None

    def lookup(self, UUID, sdUUID, spUUID, imgUUID):
        self.UUID = UUID
        self.sdUUID = sdUUID
        self.spUUID = spUUID
        self.imgUUID = imgUUID

        ret = self.conn.vdsm.getVolumeInfo(self.sdUUID, self.spUUID,
                                           self.imgUUID, self.UUID)
        try:
            vdsOK(ret)
        except vdsmException, e:
            if e.code == 201: # Volume does not exist
                raise ResourceNotFound()
            else:
                raise

        for i in ('voltype', 'parent', 'format', 'apparentsize', 'ctime',
                  'legality', 'mtime', 'disktype', 'capacity', 'truesize',
                  'type', 'children', 'description'):
            self.info[i] = ret['info'][i]
        ret = self.conn.vdsm.getVolumePath(self.sdUUID, self.spUUID,
                                           self.imgUUID, self.UUID)
        vdsOK(ret)
        self.path = ret['path']

    def new_from_json(self, data, sdUUID, spUUID, imgUUID):
        # XXX: Add support for child volumes (might be able to infer volType)
        obj = json.loads(data)
        self.UUID = json_get_or_make_id(obj)
        self.imgUUID = imgUUID
        self.sdUUID = sdUUID
        self.spUUID = spUUID
        if self.spUUID is None:
            self.spUUID = lookup_sp(self.conn, self.sdUUID)

        #self.path = obj['path']
        self.info = {}
        for i in ('voltype', 'parent', 'format','disktype', 'capacity',
                  'type', 'description'):
            self.info[i] = obj.get(i, None)
        
        bytes_per_sector = 512
        size = self.info['capacity'] / bytes_per_sector
        fmt = volumeTypeGetCode(self.info['format'])
        prealloc = volumeTypeGetCode(self.info['type'])
        voltype = volumeTypeGetCode(self.info['voltype'])
        
        ret = self.conn.vdsm.createVolume(self.sdUUID, self.spUUID, self.imgUUID, 
                               size, fmt, prealloc, voltype, self.UUID,
                               self.info['description'], BLANK_UUID, BLANK_UUID)
        vdsOK(ret)
        task = Task(self.conn)
        task.lookup(ret['uuid'])
        task.set_target("/vdsm-api/storagedomains/%s/images/%s/volumes/%s/" %
                        (self.sdUUID, self.imgUUID, self.UUID))
        return task

    def _delete(self):
        ret = self.conn.vdsm.deleteVolume(self.sdUUID, self.spUUID, self.imgUUID,
                                          [self.UUID])
        vdsOK(ret)
        task = Task(self.conn)
        task.lookup(ret['uuid'])
        return task

    @cherrypy.expose
    def index(self):
        data = { 'sdUUID': self.sdUUID, 'spUUID': self.spUUID,
                 'imgUUID': self.imgUUID, 'volUUID': self.UUID,
                 'info': self.info, 'path': self.path }
        return render_template('volume', data)

    @cherrypy.expose
    def delete(self, *args):
        validate_method(('POST',))
        task = self._delete()
        cherrypy.response.status = "202" # Accepted
        return render_template('task', { 'task': task} )

class Volumes(Controller):
    def __init__(self, conn, imgUUID, sdUUID, spUUID):
        self.conn = conn
        self.imgUUID = imgUUID
        self.sdUUID = sdUUID
        self.spUUID = spUUID

    @cherrypy.expose
    def index(self):
        # We need to populate sp specially, since it has not been passed
        # in as part of the URI.  Eventually SP will be going away and this can
        # be removed.
        #sp = self.conn.getDomain(self.sd).spUUID
        ret = self.conn.vdsm.getVolumesList(self.sdUUID, self.spUUID,
                                            self.imgUUID)
        vdsOK(ret)
        volumes = ret['uuidlist']

        data = { 'sdUUID': self.sdUUID, 'imgUUID': self.imgUUID, 'volumes': volumes }
        return render_template('volumes', data)

    @cherrypy.expose
    def create(self, *args):
        validate_method(('POST',))
        rawbody = cherrypy.request.body.read()
        volume = Volume(self.conn)
        task = volume.new_from_json(rawbody, self.sdUUID, self.spUUID, self.imgUUID)

        cherrypy.response.status = "202" # Accepted
        return render_template('task', { 'task': task} )

    def _dispatch_lookup(self, uuid):
        volume = Volume(self.conn)
        try:
            volume.lookup(uuid, self.sdUUID, self.spUUID, self.imgUUID)
            return volume
        except ResourceNotFound:
            return None

class Image(Controller):
    def __init__(self, conn):
        self.conn = conn
        self.UUID = None
        self.sdUUID = None
        self.spUUID = None
        self.volumes = None
        
    def lookup(self, UUID, sdUUID, spUUID):
        self.UUID = UUID
        self.sdUUID = sdUUID
        self.spUUID = spUUID
        
        # Just verify the existance of this image
        ret = self.conn.vdsm.getImagesList(self.sdUUID)
        vdsOK(ret)
        if UUID not in ret['imageslist']:
            raise ResourceNotFound();

        self.volumes = Volumes(self.conn, self.UUID, self.sdUUID, self.spUUID)
        self.volumes.exposed = True

    def new_from_json(self, data, sdUUID, spUUID=None):
        obj = json.loads(data)
        self.UUID = json_get_or_make_id(obj)
        self.sdUUID = sdUUID
        self.spUUID = spUUID
        if self.spUUID is None:
            self.spUUID = lookup_sp(self.conn, self.sdUUID)
        ret = self.conn.vdsm.createImage(self.sdUUID, self.spUUID, self.UUID)
        vdsOK(ret)
        task = Task(self.conn)
        task.lookup(ret['uuid'])
        task.set_target("/vdsm-api/storagedomains/%s/images/%s" %
                        (self.sdUUID, self.UUID))
        return task

    def _delete(self):
        ret = self.conn.vdsm.deleteImage(self.sdUUID, self.spUUID, self.UUID)
        vdsOK(ret)
        task = Task(self.conn)
        task.lookup(ret['uuid'])
        return task

    @cherrypy.expose
    def index(self):
        data = { 'imgUUID': self.UUID, 'sdUUID': self.sdUUID }
        return render_template('image', data)

    @cherrypy.expose
    def delete(self, *args):
        validate_method(('POST',))
        task = self._delete()
        cherrypy.response.status = "202" # Accepted
        return render_template('task', { 'task': task} )

class Images(Controller):
    def __init__(self, conn, sdUUID, spUUID):
        self.conn = conn
        self.sdUUID = sdUUID
        self.spUUID = spUUID

    @cherrypy.expose
    def index(self):
        ret = self.conn.vdsm.getImagesList(self.sdUUID)
        vdsOK(ret)
        images = ret['imageslist']
        data = { 'sdUUID': self.sdUUID, 'images': images}
        return render_template('images', data)

    @cherrypy.expose
    def create(self, *args):
        validate_method(('POST',))
        rawbody = cherrypy.request.body.read()

        image = Image(self.conn)
        task = image.new_from_json(rawbody, self.sdUUID, self.spUUID)
        cherrypy.response.status = "202" # Accepted
        return render_template('task', { 'task': task} )

    def _dispatch_lookup(self, uuid):
        image = Image(self.conn)
        try:
            image.lookup(uuid, self.sdUUID, self.spUUID)
            return image
        except ResourceNotFound:
            return None

class StorageDomain(Controller):
    def __init__(self, conn):
        self.conn = conn
        self.UUID = None
        self.spUUID = None
        self.info = { 'version': 0, 'class': DATA_DOMAIN }
        self.stats = {}
        self.images = None

    def lookup(self, UUID):
        self.UUID = UUID
        ret = self.conn.vdsm.getStorageDomainInfo(self.UUID)
        try:
            vdsOK(ret)
        except vdsmException, e:
            if e.code == 358: # Storage domain does not exist
                raise ResourceNotFound();
            else:
                raise

        if len(ret['info']['pool']) > 0:
            self.spUUID = ret['info']['pool'][0]
        for i in ('lver', 'version', 'role', 'remotePath', 'type', 'class',
                  'master_ver', 'name', 'spm_id'):
            self.info[i] = ret['info'][i]

        self.images = Images(self.conn, self.UUID, self.spUUID)
        self.images.exposed = True

    def new_from_json(self, data):
        obj = json.loads(data)
        self.UUID = json_get_or_make_id(obj)
        self.info['type'] = obj['type']
        self.info['name'] = obj['name']
        self.info['remotePath'] = obj['remotePath']
        
        sdType = sdTypeGetCode(self.info['type'])
        self._connect_server()
        ret = self.conn.vdsm.createStorageDomain(sdType, self.UUID,
                                    self.info['name'], self.info['remotePath'],
                                    self.info['class'], self.info['version'])
        try:
            vdsOK(ret)
        except vdsmException, e:
            if e.code == 365: # Storage domain already exists
                raise InvalidOperation("Storage domain already exists")
            else:
                raise

    def _attach(self, spUUID):
        if self.spUUID is not None:
            raise InvalidOperation("The storage domain is already attached")
        ret = self.conn.vdsm.attachStorageDomain(self.UUID, spUUID)
        vdsOK(ret)

    def _activate(self):
        if self.spUUID is None:
            raise InvalidOperation("The storage domain is not attached to a pool")
        ret = self.conn.vdsm.activateStorageDomain(self.UUID, self.spUUID)
        vdsOK(ret)

    def _deactivate(self):
        if self.spUUID is None: # XXX: also need to confirm status == Active
            raise InvalidOperation("The storage domain is not active")
        ret = self.conn.vdsm.deactivateStorageDomain(self.UUID, self.spUUID,
                                            BLANK_UUID, self.info['master_ver'])
        vdsOK(ret)

    def _detach(self):
        # XXX: Raise error if sd is attached and active
        if self.spUUID is None:
            raise InvalidOperation("The storage domain is not attached")
        ret = self.conn.vdsm.detachStorageDomain(self.UUID, self.spUUID,
                                            BLANK_UUID, self.info['master_ver'])
        vdsOK(ret)

    def _delete(self):
        if self.spUUID is not None:
            raise InvalidOperation("Cannot delete an attached storage domain")
        ret = self.conn.vdsm.formatStorageDomain(self.UUID)
        vdsOK(ret)
        self._disconnect_server()

    def _connect_server(self):
        sdType = sdTypeGetCode(self.info['type'])
        ret = self.conn.vdsm.connectStorageServer(sdType, "",
                            [dict(id=1, connection=self.info['remotePath'])])
        vdsOK(ret)
        return bool(ret['statuslist'][0]['status'])

    def _disconnect_server(self):
        sdType = sdTypeGetCode(self.info['type'])
        ret = self.conn.vdsm.disconnectStorageServer(sdType, BLANK_UUID,
                            [dict(id=1, connection=self.info['remotePath'])])
        vdsOK(ret)
        return bool(ret['statuslist'][0]['status'])

    @cherrypy.expose
    def index(self):
        data = {}
        data['sdUUID'] = self.UUID
        data['spUUID'] = self.spUUID
        data['info'] = self.info
        return render_template('storagedomain', data)

    @cherrypy.expose
    def delete(self, *args):
        validate_method(('POST',))
        self._delete()
        cherrypy.response.status = 204
        return

    @cherrypy.expose
    def attach(self, *args):
        validate_method(('POST',))
        rawbody = cherrypy.request.body.read()
        params = json.loads(rawbody)
        self._attach(params['storagepool'])
        url = "/vdsm-api/storagedomains/%s" % self.UUID
        raise cherrypy.HTTPRedirect(url, 303)
        
    @cherrypy.expose
    def detach(self, *args):
        validate_method(('POST',))
        self._detach()
        url = "/vdsm-api/storagedomains/%s" % self.UUID
        raise cherrypy.HTTPRedirect(url, 303)
        
    @cherrypy.expose
    def activate(self, *args):
        validate_method(('POST',))
        self._activate()
        url = "/vdsm-api/storagedomains/%s" % self.UUID
        raise cherrypy.HTTPRedirect(url, 303)
                
    @cherrypy.expose
    def deactivate(self, *args):
        validate_method(('POST',))
        self._deactivate()
        url = "/vdsm-api/storagedomains/%s" % self.UUID
        raise cherrypy.HTTPRedirect(url, 303)

class StorageDomains(Controller):
    def __init__(self, conn):
        self.conn = conn

    @cherrypy.expose
    def index(self):
        ret = self.conn.vdsm.getStorageDomainsList()           
        vdsOK(ret)
        domains = ret['domlist']
        return render_template('storagedomains', { 'domains': domains })
    
    @cherrypy.expose
    def create(self, *args):
        validate_method(('POST',))
        rawbody = cherrypy.request.body.read()
        try:
            domain = StorageDomain(self.conn)
            domain.new_from_json(rawbody)
        except InvalidOperation, e:
            error_invalid_operation(e)

        raise cherrypy.HTTPRedirect("/vdsm-api/storagedomains/%s" % domain.UUID, 303)

    def _dispatch_lookup(self, uuid):
        domain = StorageDomain(self.conn)
        try:
            domain.lookup(uuid)
            return domain
        except ResourceNotFound:
            return None

class StoragePool(Controller):
    def __init__(self, conn):
        self.conn = conn
        self.UUID = None        

    def lookup(self, UUID):
        config = self.conn.storage.getItem('storagepools', UUID)
        if config is None:
            raise ResourceNotFound()
        
        self.UUID = UUID
        self.info = { 'type': config['type'], 'name': config['name'],
                      'master_uuid': config['master_uuid'],
                      'master_ver': config['master_ver'],
                      'pool_status': 'disconnected' }
        self.dominfo = {}

        ret = self.conn.vdsm.getStoragePoolInfo(self.UUID)
        try:
            vdsOK(ret)
        except vdsmException, e:
            if e.code == 309: # Unknown pool id, pool not connected
                # Additional details are only available for connected pools
                return
            else:
                raise

        for i in ('name', 'isoprefix', 'master_uuid', 'version', 'spm_id',
                  'type', 'master_ver', 'lver', 'pool_status'):
            self.info[i] = ret['info'][i]
        for sdUUID, dominfo in ret['dominfo'].items():
            self.dominfo[sdUUID] = { 'status': dominfo['status'],
                                     'diskfree': dominfo['diskfree'],
                                     'disktotal': dominfo['disktotal'] }

    def new_from_json(self, data):
        obj = json.loads(data)
        self.UUID = json_get_or_make_id(obj)
        spType = sdTypeGetCode(obj['type'])
        self.info = { 'id': self.UUID, 'type': spType, 'name': obj['name'],
                      'master_uuid': obj['master_uuid'],
                      'master_ver': obj['master_ver'],
                      'pool_status': 'disconnected' }
        ret = self.conn.vdsm.createStoragePool(spType, self.UUID,
                        self.info['name'], self.info['master_uuid'],
                        [self.info['master_uuid'],], self.info['master_ver'])
        vdsOK(ret)
        self.conn.storage.createItem('storagepools', self.UUID, self.info)

    def _delete(self, key):
        # XXX: hostID should come from a config file
        hostID = 1
        # XXX: Don't delete the pool if it's active
        ret = self.conn.vdsm.disconnectStoragePool(self.UUID, hostID, key)
        vdsOK(ret)
        self.conn.storage.deleteItem('storagepools', self.UUID)

    def _connect(self, key):
        # XXX: hostID should come from a config file
        hostID = 1
        ret = self.conn.vdsm.connectStoragePool(self.UUID, hostID, key,
                            self.info['master_uuid'], self.info['master_ver'])
        vdsOK(ret)
        
    def _disconnect(self, key):
        # XXX: hostID should come from a config file
        hostID = 1
        ret = self.conn.vdsm.disconnectStoragePool(self.UUID, hostID, key)
        vdsOK(ret)

    def _spmStatus(self):
        ret = self.conn.vdsm.getSpmStatus(self.UUID)
        vdsOK(ret)
        status = {}
        for k in ('spmId', 'spmStatus', 'spmLver'):
            status[k] =  ret['spm_st'][k]
        return status
        
    def _spmStart(self, prevId=-1, prevLver=-1, recoveryMode=-1, scsiFencing=0):
        ret = self.conn.vdsm.spmStart(self.UUID, prevId, prevLver, recoveryMode,
                                      scsiFencing)
        try:
            vdsOK(ret)
        except vdsmException, e:
            if e.code == 656: # Operation not allowed while SPM is active
                raise InvalidOperation("SPM is already active")
            else:
                raise

        task = Task(self.conn)
        task.lookup(ret['uuid'])
        return task

    def _spmStop(self):
        ret = self.conn.vdsm.spmStop(self.UUID)
        vdsOK(ret)

    @cherrypy.expose
    def index(self):
        data = {}
        data['spUUID'] = self.UUID
        data['info'] = self.info
        data['dominfo'] = self.dominfo
        return render_template('storagepool', data)

    @cherrypy.expose
    def delete(self, *args):
        validate_method(('POST',))
        rawbody = cherrypy.request.body.read()
        params = json.loads(rawbody)
        self._delete(params['key'])
        cherrypy.response.status = 204
        return

    @cherrypy.expose
    def connect(self, *args):
        validate_method(('POST',))
        rawbody = cherrypy.request.body.read()
        params = json.loads(rawbody)
        self._connect(params['key'])
        url = "/vdsm-api/storagepools/%s" % self.UUID
        raise cherrypy.HTTPRedirect(url, 303)
        
    @cherrypy.expose
    def disconnect(self, *args):
        validate_method(('POST',))
        rawbody = cherrypy.request.body.read()
        params = json.loads(rawbody)
        self._disconnect(params['key'])
        url = "/vdsm-api/storagepools/%s" % self.UUID
        raise cherrypy.HTTPRedirect(url, 303)

    @cherrypy.expose
    def spmstart(self, *args):
        validate_method(('POST',))
        task = self._spmStart()
        cherrypy.response.status = "202" # Accepted
        return render_template('task', { 'task': task} )
        
    @cherrypy.expose
    def spmstop(self, *args):
        validate_method(('POST',))
        self._spmStop()
        url = "/vdsm-api/storagepools/%s" % self.UUID
        raise cherrypy.HTTPRedirect(url, 303)

class StoragePools(Controller):
    def __init__(self, conn):
        self.conn = conn
    
    @cherrypy.expose
    def index(self):
        pools = self.conn.storage.getItems('storagepools')
        return render_template('storagepools', { 'pools': pools })

    @cherrypy.expose
    def create(self, *args):
        validate_method(('POST',))
        rawbody = cherrypy.request.body.read()
        
        pool = StoragePool(self.conn)
        pool.new_from_json(rawbody)
        raise cherrypy.HTTPRedirect("/vdsm-api/storagepools/%s" % pool.UUID, 303)

    def _dispatch_lookup(self, uuid):
        pool = StoragePool(self.conn)
        try:
            pool.lookup(uuid)
            return pool
        except ResourceNotFound:
            return None

class Root(Controller):
    def __init__(self):
        self.conn = ConnectionManager()
        self.storagedomains = StorageDomains(self.conn)
        self.storagedomains.exposed = True
        self.storagepools = StoragePools(self.conn)
        self.storagepools.exposed = True
        self.vms = VMs(self.conn)
        self.vms.exposed = True
        self.tasks = Tasks(self.conn)
        self.tasks.exposed = True

    @cherrypy.expose
    def index(self):
        return render_template('root', {})

def error_not_found(e):
    raise cherrypy.HTTPError(404, e.message)

def error_invalid_operation(e):
    raise cherrypy.HTTPError(400, e.message)
