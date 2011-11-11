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

import os, os.path, time
from Cheetah.Template import Template
import cherrypy

def can_accept(mime):
    #if mime == 'application/json':
    #    return True
    if not cherrypy.request.headers.has_key('Accept'):
        accepts = 'application/json'
    else:
        accepts = cherrypy.request.headers['Accept']

    if accepts.find(';') != -1:
        accepts, _ = accepts.split(';', 1)

    if mime in accepts.split(','):
        return True

    return False

def render_template(filename, data):
    if can_accept('application/json'):
        cherrypy.response.headers['Content-type'] = 'application/json'
        return Template(file='templates/%s.json.x' % filename,
                        searchList=[data]).respond()    
    #elif can_accept('application/xml'):
    #    cherrypy.response.headers['Content-type'] = 'application/xml'
    #    return Template(file='templates/%s.xml.x' % filename,
    #                   searchList=[data]).respond()    
    else:
        raise cherrypy.HTTPError(406,
                                 "This API only supports 'application/json'")
