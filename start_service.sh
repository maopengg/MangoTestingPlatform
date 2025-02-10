# shellcheck disable=SC2164
docker rmi $(docker images -f "dangling=true" -q)
cd /code/MangoTestingPlatform
git pull
docker-compose down
docker-compose build
docker-compose up -d
docker ps

