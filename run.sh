docker stop thuis
docker rm thuis
docker run \
        --detach \
        --publish 8088:8088 \
        --volume /opt/thuis/envdb.json:/usr/src/app/envdb.json \
        --volume /etc/hosts:/etc/hosts \
        --name thuis \
        --env-file env.list \
        thuis
