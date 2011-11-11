{
  "drives":
  [
#set first = 1
#for $drive in $drives
#if first == 1# #set first = 0# #else#    ,#end if#
    { "id": "$drive['volume']", "href": "/vdsm-api/vms/$vmUUID/drives/$drive['volume']" }
#end for
  ]
}
