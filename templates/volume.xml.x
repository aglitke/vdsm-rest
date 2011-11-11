<volume id="$volUUID"
       href="/vdsm-api/storagedomains/$sdUUID/images/$imgUUID/volumes/$volUUID">
    <description>$info['description']</description>
    <voltype>$info['voltype']</voltype>
    <type>$info['type']</type>
    <disktype>$info['disktype']</disktype>
    <format>$info['format']</format>
    <apparentsize>$info['apparentsize']</apparentsize>
    <truesize>$info['truesize']</truesize>
    <capacity>$info['capacity']</capacity>
    <ctime>$info['ctime']</ctime>
    <mtime>$info['mtime']</mtime>
    <legality>$info['legality']</legality>
    <parent>$info['parent']</parent>
    <children>
#for c in $info['children']
        <volume id="$c"
            href="/vdsm-api/storagedomains/$sdUUID/images/$imgUUID/volumes/$c" />
#end for
    </children>
    <actions></actions>
</image>
