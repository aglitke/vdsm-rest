{
  "resource": "storagepool",
  "id": "$spUUID",
  "href": "/vdsm-api/storagepools/$spUUID",
  "pool_status": "${info['pool_status']}",
#if $info['pool_status'] == "connected"
  "name": "${info['name']}",
  "isoprefix": "${info['isoprefix']}",
  "master_uuid": "${info['master_uuid']}",
  "version": "${info['version']}",
  "spm_id": "${info['spm_id']}",
  "type": "${info['type']}",
  "master_ver": "${info['master_ver']}",
  "lver": "${info['lver']}",
  "domains": [
#set first = 1
#for $sdUUID, $sdStats in $dominfo.items()
#if first == 1# #set first = 0# #else#    ,#end if#
    { "id": "$sdUUID", "href": "/vdsm-api/storagedomains/$sdUUID",
      "status": "${sdStats['status']}",
      "diskfree": ${sdStats['diskfree']},
      "disktotal": ${sdStats['disktotal']}
    }
#end for
  ],
#end if
  "actions": {}
}
