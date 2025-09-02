docker-compose down
docker container prune -f
docker rmi $(docker images -f "dangling=true" -q) 2>/dev/null || true
git pull
docker-compose build
docker-compose up -d
docker ps
sleep 6
docker logs mangotestingplatform-mango_server-1
docker logs mangotestingplatform-mango_actuator-1