# ==========================================
# STAGE 1: Builder
# ==========================================
FROM python:3.13-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ==========================================
# STAGE 2: Runner
# ==========================================
FROM python:3.13-slim AS runner

WORKDIR /app

# Configure non-root user execution
RUN groupadd -g 10001 appgroup && useradd -u 10001 -g appgroup -s /bin/sh appuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local
COPY . /app

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

# K8s liveness healthcheck configuration
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/live || exit 1

CMD ["python", "main.py"]
