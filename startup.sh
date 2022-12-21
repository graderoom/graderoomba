#!/bin/bash

ID_FILE=.id
ID=""
if [ -f "$ID_FILE" ]
then
    ID=$(<.id)
fi

if [ -z "$ID" ]
then
    echo "No stored Graderoomba process ID"
else
    echo "Killing existing Graderoomba process $ID"
    kill -9 $ID
fi

nohup python3 graderoomba.py > .out 2> .err < /dev/null &
echo "$!" > .id
echo "Started Graderoomba process with ID $!"
