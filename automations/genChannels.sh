#!/bin/bash

room=${1:garage}

function doOne
{
    local room=$1
    local controller=$2
    local scene=$3
    local data=$4
    local command=$5

    local roomPrefix="$room"
    [ -n "$roomPrefix" ] && roomPrefix="${roomPrefix}_"
  
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
    - service: script.${roomPrefix}${command}

EOF
}

function commonRooms
{
    local room=$1
    local controller=${room}quad
    doOne $room $controller 1 0 play_classic_rewind
    doOne $room $controller 1 1 play_classic_vinyl
    doOne $room $controller 2 0 play_tom_petty
    doOne $room $controller 2 1 play_grateful_dead
    doOne $room $controller 3 0 volume_down
    doOne $room $controller 3 1 play_80s
    doOne $room $controller 4 0 volume_up
    doOne $room $controller 4 1 media_stop
}

function patio
{
    local room="patio"
    local main="family_room"
    local controller=${room}quad
    doOne $room $controller 1 0 play_classic_rewind
    doOne $room $controller 1 1 play_tom_petty
    doOne $main $controller 2 0 add_patio
    doOne $room $controller 2 1 drop_patio
    doOne $room $controller 3 0 volume_down
    doOne $room $controller 3 1 play_80s
    doOne $room $controller 4 0 volume_up
    doOne $room $controller 4 1 media_stop
}

function doKitchen
{
    # Kitchen is harder

    quad=kitchenquad4
    
    doOne family_room ${quad}   1 0 play_classic_rewind # Works
    doOne family_room ${quad}   1 1 play_classic_vinyl  # works
    doOne family_room ${quad}   2 0 play_jimmy_buffett
    doOne family_room ${quad}   2 1 play_70s
    doOne family_room ${quad}   3 0 play_tom_petty 
    doOne family_room ${quad}   3 1 play_80s
    doOne family_room ${quad}   4 0 play_grateful_dead
    doOne family_room ${quad}   4 1 play_grateful_dead 

    local quad=kitchenquad3
    doOne ""          ${quad} 1 0 turn_on_accent_lighting 
    doOne ""          ${quad} 1 1 turn_off_accent_lighting 
    doOne family_room ${quad} 2 0 volume_up 
    doOne family_room ${quad} 2 1 add_patio 
    doOne family_room ${quad} 3 0 turn_off 
    doOne ""          ${quad} 3 1 cabinet_lights_toggle 
    doOne family_room ${quad} 4 0 volume_down 
    doOne family_room ${quad} 4 1 remove_patio 
}

commonRooms garage > garage.yaml
patio > patio.yaml
doKitchen > kitchen.yaml
