#!/bin/bash

rooms="family_room garage move office patio"

for add_to in $rooms
do
cat <<EOF
drop_${add_to}:
  alias: Drop ${add_to} from group
  sequence:
  - service: media_player.unjoin
    data: {}
    target:
      entity_id: media_player.${add_to}

EOF
    for to_add in $rooms
    do
	if [ "$add_to" != "$to_add" ]
	then
cat <<EOF
${add_to}_add_${to_add}:
  alias: 'Add $to_add to $add_to'
  sequence:
  - service: media_player.join
    data:
      group_members:
      - media_player.${to_add}
    target:
      entity_id: media_player.${add_to}
EOF
	    
	fi
    done
    echo ""
	    
done
