FROM debian:bullseye

RUN apt-get update -y \
    && apt-get -y install build-essential python3-dev python3-pip python3-setuptools python3-wheel libpq-dev \
    && pip3 install --upgrade pip pipenv==v2022.8.14
ENV BASE_DIR=/opt
WORKDIR ${BASE_DIR}
COPY Pipfile Pipfile.lock ./
RUN pipenv install --system

COPY flickr_app ./flickr_app
COPY db ./db
COPY secrets/gcp-credentials.json ./gcp-credentials.json
ENV GOOGLE_APPLICATION_CREDENTIALS=/opt/gcp-credentials.json
ENV FLICKR_CACHE=/opt/flickr_app/.flickr

ENTRYPOINT [ "uwsgi", "--http", ":8080", "--module", "flickr_app.label_flickr_app:app" ]