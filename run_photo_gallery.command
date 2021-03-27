#!/bin/bash
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd "${DIR}"

docker-compose down
docker-compose up

open http://0.0.0.0:5000