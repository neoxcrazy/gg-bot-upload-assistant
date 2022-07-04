#!/bin/bash
apt update
apt install jq -y
compose_version=$(curl https://api.github.com/repos/docker/compose/releases/latest | jq .name -r)
output='/usr/local/bin/docker-compose'
curl -L "https://github.com/docker/compose/releases/download/$compose_version/docker-compose-$(uname -s)-$(uname -m)" -o $output
chmod +x $output
echo $(docker-compose --version)