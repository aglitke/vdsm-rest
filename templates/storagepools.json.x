{
  "storagepools":
  [
#set first = 1
#for $pool in $pools
#if first == 1# #set first = 0# #else#    ,#end if#
    { "id": "$pool", "href": "/vdsm-api/storagepools/$pool" }
#end for
  ]
}
