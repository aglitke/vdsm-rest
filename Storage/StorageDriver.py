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

class StorageDriver(object):
    def __init__(self, conf):
        pass

    def getTypes(self):
        return []

    def createType(self, type):
        return False
        
    def deleteType(self, type):
        return False
        
    def getItems(self, type):
        return []

    def getItem(self, type, uuid):
        return None
        
    def createItem(self, type, uuid, data):
        return False
        
    def updateItem(self, type, uuid, data):
        return False
        
    def deleteItem(self, type, uuid):
        return False

