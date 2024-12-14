FROM python:3.13.0-slim as base

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

# only for new macs, see https://docs.pola.rs/user-guide/installation/
RUN if [ "$(uname -m)" != "x86_64" ]; then apt-get update && apt-get install -y sed && sed -i "s/^polars=/polars-lts-cpu=/" requirements.txt; fi

RUN python -m venv /venv && . /venv/bin/activate && pip install -r requirements.txt

FROM base as final

COPY . .

COPY --from=builder /venv /venv

EXPOSE 8000

ENTRYPOINT ["/venv/bin/uvicorn"]
CMD ["--factory", "src.main:create_server", "--host", "0.0.0.0", "--use-colors"]
# CMD ["--bind", "0.0.0.0:8000", "-w", "4", "main:create_server()", "--reload", "--reload-extra-file", "config.json"]
# CMD ["main:create_server()"]

