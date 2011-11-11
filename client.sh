#!/bin/bash

HOST=localhost:8080
BASE=/vdsm-api

while [ $# -gt 0 ]; do
  case $1 in
    -f) FILE=$2; shift 2 ;;
    -d) DATA=$2; shift 2 ;;
    *) URI="$1"; shift ;;
  esac
done

URL="http://$HOST/$BASE$URI"

if [ -n "$FILE" ]; then
  ARGS="-X POST -d @$FILE"
fi
if [ -n "$DATA" ]; then
  ARGS="-X POST -d"
  set -- "$DATA"
fi

echo "curl $ARGS $@ -H 'Content-type: application/json' -H 'Accept: application/json' $URL"
curl $ARGS "$@" -H 'Content-type: application/json' -H 'Accept: application/json' \
        $URL
