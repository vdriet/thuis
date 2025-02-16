docker stop thuis
docker rm thuis
docker run --publish 8088:8088 --name thuis thuis
