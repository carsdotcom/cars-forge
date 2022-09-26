#!/bin/bash

set -e

IP=$1
IMAGE=$2

docker run --rm -it --network 'host' --env IP=${IP} ${IMAGE}

