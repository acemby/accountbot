FROM ghcr.io/linuxserver/baseimage-alpine:3.16

ARG BUILD_DATE
ARG VERSION=0.1
ARG APP_RELEASE_VER
ARG APP_NAME=embybot # change it here !!

LABEL build_version="acemby containers version:- ${VERSION} Build-date:- ${BUILD_DATE}"
LABEL maintainer="acemby"

# install dependencies
COPY /root /
COPY /src/* /app/
ENV PYTHONUNBUFFERED=true
RUN \
  apk add --update --no-cache curl git py3-pip libc6-compat gcompat  && \
  pip3 install -r /app/requirements.txt
