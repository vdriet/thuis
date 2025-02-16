docker stop thuis
docker rm thuis
docker run --publish 8088:8088 --volume /opt/thuis/envdb.json:/usr/src/app/envdb.json --name thuis thuis
