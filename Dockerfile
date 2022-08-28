FROM debian:bullseye

RUN apt-get update -y \
    && apt-get -y install build-essential python3-dev python3-pip python3-setuptools python3-wheel \
    && pip3 install --upgrade pip pipenv==v2022.8.14
ENV BASE_DIR=/opt
WORKDIR ${BASE_DIR}
COPY Pipfile Pipfile.lock ./
RUN pipenv install --system

COPY src ./src
COPY secrets/deep-learning-project-295521-4e53abd7c726.json ./gcp-credentials.json
ENV GOOGLE_APPLICATION_CREDENTIALS=/opt/gcp-credentials.json

ENTRYPOINT [ "uwsgi", "--http", ":8080", "--module", "src.label_flickr_app:app" ]