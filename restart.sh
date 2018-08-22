#!/bin/bash

function logit
{
    echo $*
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> /tmp/ha-restart-history.log
}

# JRS-TMP git pull --rebase
# JRS-TMP if [ $? -ne 0 ]
# JRS-TMP then
# JRS-TMP     echo "Git pull failed"
# JRS-TMP     exit 9
# JRS-TMP fi

if [ $(docker-compose ps homeassistant | grep -c Up) -gt 0 ]
then
    logit "Up!"
    docker-compose restart
else
    logit "Down"
    docker-compose up -d
fi

