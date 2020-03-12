# Extends the official python Dockerimage by adding the docker-compose-updater
#
#  Author: Tobias Malkmus
#  E-Mail: malkmus@mps-med.de
#
# This Dockerfile adheres to the best practices for Dockerfiles please consider
# this when modifying the file
# https://docs.docker.com/develop/develop-images/dockerfile_best-practices/

FROM python:3.6-alpine

WORKDIR /

# TODO: improve caching here
COPY --chown=1000:1000 requirements.txt /
RUN pip install -r ./requirements.txt && rm /requirements.txt
COPY --chown=1000:1000 src/docker_compose_update.py /docker_compose_update.py

RUN mkdir -p /compose-mount && chown 1000:1000 /compose-mount

CMD ["python", "docker_compose_update.py", "-r", "/compose-mount/"]
