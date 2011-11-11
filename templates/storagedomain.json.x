{
  "resource": "storagedomain",
  "id": "$sdUUID",
  "href": "/vdsm-api/storagedomains/$sdUUID",
  "name": "${info['name']}",
  "type": "${info['type']}",
  "class": "${info['class']}",
  "role": "${info['role']}",
  "remotePath": "${info['remotePath']}",
  "version": "${info['version']}",
  "master_ver": "${info['master_ver']}",
  "lver": "${info['lver']}",
  "spm_id": "${info['spm_id']}",
#if $spUUID is not None
  "storagepool": { "id": "$spUUID", "href": "/vdsm-api/storagepools/$spUUID" },
  "images": "/vdsm-api/storagedomains/$sdUUID/images/",
#end if
  "actions": {}
}
