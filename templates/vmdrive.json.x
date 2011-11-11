{
  "resource": "drive",
  "id": "$volUUID",
  "href": "/vdsm-api/vms/$vmUUID/drives/$volUUID",
  "storagepool":
      { "id": "$spUUID", "href: "/vdsm-api/storagepools/$spUUID" },
  "storagedomain":
      { "id": "$sdUUID", "href: "/vdsm-api/storagedomains/$sdUUID" },
  "image":
      { "id": "$imgUUID", "href: "/vdsm-api/storagedomains/$sdUUID/images/$imgUUID" },
  "volume":
      { "id": "$volUUID", "href: "/vdsm-api/storagedomains/$sdUUID/images/$imgUUID/volumes/$volUUID" },
  "actions": {}
}
