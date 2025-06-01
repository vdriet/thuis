docker stop thuis
docker rm thuis
docker run \
        --detach \
        --publish 8088:8088 \
        --volume /opt/thuis/envdb.json:/usr/src/app/envdb.json \
        --volume /opt/thuis/zonnesterkte.json:/usr/src/app/zonnesterkte.json \
        --name thuis \
        --env-file env.list \
        thuis
