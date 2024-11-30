FROM python:3.11.3-slim as base

ARG geocode_key
ARG secret


ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    GEOCODING_KEY=$geocode_key \
    SECRET_KEY=$secret

WORKDIR /app


FROM base as builder


ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .

RUN python -m venv /venv && . /venv/bin/activate && pip install -r requirements.txt

FROM base as final

COPY . .

COPY --from=builder /venv /venv

EXPOSE 8000

ENTRYPOINT ["/venv/bin/uvicorn"]
CMD ["--factory", "src.main:create_server", "--host", "0.0.0.0", "--use-colors"]
# CMD ["--bind", "0.0.0.0:8000", "-w", "4", "main:create_server()", "--reload", "--reload-extra-file", "config.json"]
# CMD ["main:create_server()"]

