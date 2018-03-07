#!/bin/bash

BUTTONS_PER_CONTROLLER=4

entityId="$1"
sceneId="$2"
sceneData="$3"
quadId=${entityId#zwave.quad*}

ts=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

read -r -d '' payload <<EOF
 EOF
{
    "sceneID": "$sceneId",
    "sceneData": "$sceneData",
    "entityID": "$entityId",
    "quadId": $quadId,
    "@timestamp": "$ts",
}
EOF


echo $payload >> /config/quad.log
