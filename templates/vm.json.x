{
  "resource": "vm",
  "id": "$vmUUID",
  "href": "/vdsm-api/vms/$vmUUID",
  "name": "$name",
  "memory": $memory,
  "cpus": $cpus,
  "status": "$stats['status']",
  "display": "$display",
#if 'displayIp' in $stats
  "displayIp": "$stats['displayIp']",
  "displayPort": "$stats['displayPort']",
#end if
#if 'guestIPs' in $stats
  "guestIPs": "$stats['guestIPs']",
#end if
  "boot": "$boot",
  "floppy": "$floppy",
  "cdrom": "$cdrom",
  "drives": "/vdsm-api/vms/$vmUUID/drives",
  "nics": "/vdsm-api/vms/$vmUUID/nics",
  "actions": {}
}
