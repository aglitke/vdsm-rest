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

from Storage.StorageDriver import StorageDriver
import sqlite3
import pickle

class LocalDB(StorageDriver):
    def __init__(self, conf):
        self.path = conf['path']
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        self.types = self._getTypes(c)
        c.close()
        conn.close()

    def _getTypes(self, cursor):
        sql = "select name from sqlite_master where type = 'table'"
        result = cursor.execute(sql)
        ret = []
        for row in result:
            ret.append(row[0])
        return ret

    def getTypes(self):
        return self.types

    def createType(self, type):
        """
        XXX: Vulnerable to a SQL injection attack!  Luckily the code passing in
        the parameter is trusted.
        """
        if type in self.getTypes():
            return True
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        sql = "create table '%s' (uuid text primary key, obj blob)" % type
        c.execute(sql)
        conn.commit()
        self.types = self._getTypes(c)
        c.close()
        conn.close()
        return True
        
    def deleteType(self, type):
        if type not in self.getTypes():
            return False
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        sql = "drop table '%s'" % type
        c.execute(sql)
        conn.commit()
        self.types = self._getTypes(c)
        c.close()
        conn.close()
        return True
        
    def getItems(self, type):
        if type not in self.getTypes():
            return []
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        sql = "select uuid from '%s'" % type
        result = c.execute(sql)
        ret = []
        for row in result:
            ret.append(row[0])
        c.close()
        conn.close()
        return ret

    def getItem(self, type, uuid):
        if type not in self.getTypes():
            return None
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        t = (uuid,)
        sql = "select obj from '%s' where uuid = ?" % type
        result = c.execute(sql, t).fetchone()
        c.close()
        conn.close()
        if result is None:
            return None
        else:
            return pickle.loads(str(result[0]))
        
    def createItem(self, type, uuid, data):
        if type not in self.getTypes():
            return False
        obj = pickle.dumps(data)
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        t = (uuid, obj)
        sql = "insert into '%s' (uuid, obj) values (?, ?)" % type
        c.execute(sql, t)
        conn.commit()
        c.close()
        conn.close()
        return []

    def updateItem(self, type, uuid, data):
        if type not in self.getTypes():
            return False
        obj = pickle.dumps(data)
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        t = (obj, uuid)
        sql = "update '%s' set obj=? where uuid = ?" % type
        c.execute(sql, t)
        conn.commit()
        c.close()
        conn.close()
        return True

    def deleteItem(self, type, uuid):
        if type not in self.getTypes():
            return False
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        t = (uuid,)
        sql = "delete from '%s' where uuid=?" % type
        c.execute(sql, t)
        conn.commit()
        c.close()
        conn.close()
        return True
