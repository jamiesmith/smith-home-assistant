#!/bin/bash

room=${1:garage}

function doOne
{
    controller=${room}quad
    scene=$1
    data=$2
    command=$3
    
cat <<EOF
- id: ${controller}_scene_${scene}_${command}
  alias: ${room} QuadMote $command
#  hide_entity: true
  trigger:
    platform: event
    event_type: zwave.scene_activated
    event_data:
      entity_id: zwave.${controller}
      scene_id: $scene
      scene_data: $data
  action:
    - service: script.${room}_${command}

EOF
}


doOne 1 0 play_classic_rewind
doOne 1 1 play_classic_vinyl
doOne 2 0 play_tom_petty
doOne 2 1 play_grateful_dead
doOne 3 0 volume_down
doOne 3 1 play_80s
doOne 4 0 volume_up
doOne 4 1 media_stop
