<images>
#for $image in $images
    <image id="$image"
           href="/vdsm-api/storagedomains/$sdUUID/images/$image />
#end for
</images>
