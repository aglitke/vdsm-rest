{
  "images":
  [
#set first = 1
#for $image in $images
#if first == 1# #set first = 0# #else#    ,#end if#
    { "id": "$image", "href": "/vdsm-api/storagedomains/$sdUUID/images/$image" }
#end for
  ]
}
