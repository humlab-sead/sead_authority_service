FROM python:3.13-slim-bookworm

LABEL maintainer="Roger Mähler <roger dot mahler at umu dot se>"

ENV APP_USER=sead_authority_service_user
ENV APP_UID=1022
ENV APP_GID=1022
ARG APP_PORT=${APP_PORT:-8392}

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

USER root

RUN mkdir -p /app

WORKDIR /app

COPY --chown=${APP_USER}:${APP_USER} main.py .
COPY --chown=${APP_USER}:${APP_USER} entrypoint.sh .
COPY --chown=${APP_USER}:${APP_USER} config ./config/
COPY --chown=${APP_USER}:${APP_USER} dist/*.whl /dist/

RUN set -ex; \
    pip install --no-cache-dir /dist/*.whl; \
    chmod +x entrypoint.sh; \
    rm -rf /dist /wheels

USER ${APP_USER}

ENV SHELL=/bin/bash
ENV HOME=/app
ENV APP_PORT=${APP_PORT:-8392}

ENTRYPOINT ["./entrypoint.sh"]