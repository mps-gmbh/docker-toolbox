# Extends the official python Dockerimage by adding the docker-compose-updater
#
# This Dockerfile adheres to the best practices for Dockerfiles please consider
# this when modifying the file
# https://docs.docker.com/develop/develop-images/dockerfile_best-practices/

FROM python:3.8.2-alpine3.11

WORKDIR /

# Install Docker and docker-compose
RUN apk add \
docker \
gcc \
libc-dev \
libffi-dev \
make \
openssl-dev \
python-dev \
&& pip install docker-compose

COPY cron-init.sh /cron-init.sh

COPY requirements.txt /
RUN pip install -r ./requirements.txt && rm /requirements.txt
COPY src/docker_compose_update.py /docker_compose_update.py

CMD ["python", "docker_compose_update.py", "-r", "/compose-mount/"]
