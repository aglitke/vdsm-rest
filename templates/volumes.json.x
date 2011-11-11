{
  "volumes":
  [
#set first = 1
#for $volume in $volumes
#if first == 1# #set first = 0# #else#    ,#end if#
    { "id": "$volume", "href": "/vdsm-api/storagedomains/$sdUUID/images/$imgUUID/volumes/$volume" }
#end for
  ]
}
