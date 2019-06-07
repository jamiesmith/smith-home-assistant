#!/bin/bash

function logit
{
    echo $*
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> /tmp/ha-restart-history.log
}

if [ $(docker-compose ps homeassistant | grep -c Up) -gt 0 ]
then
    logit "Up!"
    docker-compose restart
else
    logit "Down"
    docker-compose up -d
fi

