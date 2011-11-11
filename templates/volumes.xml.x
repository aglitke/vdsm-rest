<volumes>
#for $volume in $volumes
    <volume id="$volume"
            href="/vdsm-api/storagedomains/$sdUUID/images/$imgUUID/volumes/$volume />
#end for
</volumes>
