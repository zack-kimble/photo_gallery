#!/bin/bash
flask db migrate -m "check for changes";
flask db upgrade;
echo $PHOTO_SOURCE;
nohup redis-server &
sleep 5 &
nohup rq worker photo-gallery-tasks &
flask run --host 0.0.0.0 &
bash
rq