# =============================================================================
# DigiPay platform image — serves BOTH services from one build.
#
# The two services stay separate processes with their own ports and their own
# URLs; only the image is shared, because they share requirements.txt and
# because the AI platform reads the legacy routers to document them in its
# Swagger UI. Pick which service a container runs via its command:
#
#   legacy DigiPay API :  uvicorn app.main:app       --host 0.0.0.0 --port 8000
#   AI platform        :  uvicorn main:app --app-dir ai_platform ...  (port 8001)
#
# See docker-compose.yml, which does exactly that.
#
# Note on build context: it MUST be the repository root. requirements.txt lives
# there, and the AI platform imports `app.routers.v1` to generate the legacy
# OpenAPI schema, so both trees have to be present in the image.
# =============================================================================

# ---------------------------------------------------------------- build stage
FROM python:3.13-slim AS builder

WORKDIR /build

RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---------------------------------------------------------------- run stage
FROM python:3.13-slim AS runner

WORKDIR /srv

# curl is needed by the container healthchecks below.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd -g 10001 appgroup \
 && useradd -u 10001 -g appgroup -m -s /bin/sh appuser

COPY --from=builder /root/.local /home/appuser/.local

COPY app/ /srv/app/
COPY ai_platform/ /srv/ai_platform/
COPY requirements.txt /srv/

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    # Both trees importable: the AI platform imports its own modules top-level
    # (core.config, tools.registry) AND the legacy `app` package.
    PYTHONPATH=/srv:/srv/ai_platform

# /srv/ai_platform/data/keys  the AI platform generates its client RSA keypair
#                             here on first start
# /srv/data                   the legacy service's SQLite file when no MySQL is
#                             configured; SQLite needs the directory to exist
# Both are volume-mounted in docker-compose.yml so they survive restarts.
RUN mkdir -p /srv/ai_platform/data/keys /srv/data \
 && chown -R appuser:appgroup /srv

USER appuser

EXPOSE 8000 8001

# Overridden per service in docker-compose.yml.
CMD ["uvicorn", "main:app", "--app-dir", "ai_platform", "--host", "0.0.0.0", "--port", "8001"]
