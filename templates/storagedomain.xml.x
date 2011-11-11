<storagedomain id="$sdUUID"
               href="/vdsm-api/storagedomains/$sdUUID">
    <name>${info['name']}</name>
    <type>${info['type']}</type>
    <class>${info['class']}</class>
    <role>${info['role']}</role>
    <remotePath>${info['remotePath']}</remotePath>
    <version>${info['version']}</version>
    <master_ver>${info['master_ver']}</master_ver>
    <lver>${info['lver']}</lver>
    <spm_id>${info['spm_id']}</spm_id>
#if $spUUID is not None
    <storagepool id="$spUUID" href="/vdsm-api/storagepools/$spUUID" />
    <link rel="images" href="/vdsm-api/storagedomains/$sdUUID/images/" />
#end if
    <actions></actions>
</storagedomain>
