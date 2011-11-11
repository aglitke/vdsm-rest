{
  "storagedomains": 
  [
#set first = 1
#for $domain in $domains
#if first == 1# #set first = 0# #else#    ,#end if#
    { "id": "$domain", "href": "/vdsm-api/storagedomains/$domain" }
#end for
  ]
}
