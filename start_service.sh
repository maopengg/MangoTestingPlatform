# shellcheck disable=SC2164
cd /code/MangoTestingPlatform
git pull
docker-compose down
docker-compose build
docker-compose up -d
docker ps

