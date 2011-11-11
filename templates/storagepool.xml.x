<storagepool id="$spUUID"
             href="/vdsm-api/storagepools/$spUUID">
    <pool_status>${info['pool_status']}</pool_status>
#if $info['pool_status'] == "connected"
    <name>${info['name']}</name>
    <isoprefix>${info['isoprefix']}</isoprefix>
    <master_uuid>${info['master_uuid']}</master_uuid>
    <version>${info['version']}</version>
    <spm_id>${info['spm_id']}</spm_id>
    <type>${info['type']}</type>
    <master_ver>${info['master_ver']}</master_ver>
    <lver>${info['lver']}</lver>
    <domains>
#for $sdUUID, $sdStats in $dominfo.items()
        <storagedomain id="$sdUUID" href="/vdsm-api/storagedomains/$sdUUID">
            <status>${sdStats['status']}</status>
            <diskfree>${sdStats['diskfree']}</diskfree>
            <disktotal>${sdStats['disktotal']}</disktotal>
        </storagedomain>
#end for
    </domains>
#end if
    <actions></actions>
</storagepool>
