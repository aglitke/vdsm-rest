<storagepools>
#for $pool in $pools
  <storagepool id="$pool" href="/vdsm-api/storagepools/$pool" />
#end for
</storagepools>
