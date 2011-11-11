<storagedomains>
#for $domain in $domains
  <storagedomain id="$domain" href="/vdsm-api/storagedomains/$domain" />
#end for
</storagedomains>
