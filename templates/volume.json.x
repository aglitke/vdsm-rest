{
  "resource": "volume",
  "id": "$volUUID",
  "href": "/vdsm-api/storagedomains/$sdUUID/images/$imgUUID/volumes/$volUUID",
  "description": "$info['description']",
  "voltype": "$info['voltype']",
  "type": "$info['type']",
  "disktype": "$info['disktype']",
  "format": "$info['format']",
  "path": "$path",
  "apparentsize": $info['apparentsize'],
  "truesize": $info['truesize'],
  "capacity": $info['capacity'],
  "ctime": "$info['ctime']",
  "mtime": "$info['mtime']",
  "legality": "$info['legality']",
  "parent": "$info['parent']",
  "children": [
#set first = 1
#for c in $info['children']
#if first == 1# #set first = 0# #else#    ,#end if#
    { "id": "$c", "href": "/vdsm-api/storagedomains/$sdUUID/images/$imgUUID/volumes/$c" }
#end for
  ],
  "actions": {}
}
