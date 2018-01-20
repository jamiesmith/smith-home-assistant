#!/bin/bash


git pull --rebase
if [ $? -ne 0 ]
then
    echo "Git pull failed"
    exit 9
fi

if [ $(docker-compose ps homeassistant | grep -c Up) ]
then
    echo "Up!"
    docker-compose restart
else
    echo "Down"
    docker-compose start -d
fi

