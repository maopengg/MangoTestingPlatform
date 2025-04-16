docker-compose down
docker container prune -f
docker rmi $(docker images -f "dangling=true" -q) 2>/dev/null || true
cd /code/MangoTestingPlatform
git pull
docker-compose build
docker-compose up -d
docker ps

