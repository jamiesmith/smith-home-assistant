#!/bin/bash


# JRS-TMP git pull --rebase
# JRS-TMP if [ $? -ne 0 ]
# JRS-TMP then
# JRS-TMP     echo "Git pull failed"
# JRS-TMP     exit 9
# JRS-TMP fi

if [ $(docker-compose ps homeassistant | grep -c Up) ]
then
    echo "Up!"
    docker-compose restart
else
    echo "Down"
    docker-compose start -d
fi

