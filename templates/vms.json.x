{
  "vms":
  [
#set first = 1
#for $vm in $vms
#if first == 1# #set first = 0# #else#    ,#end if#
    { "id": "$vm", "href": "/vdsm-api/vms/$vm" }
#end for
  ]
}
