FROM node:22-bookworm-slim AS remotion
WORKDIR /app/remotion-composer
COPY remotion-composer/package*.json ./
RUN npm ci --omit=dev && npx remotion browser ensure
COPY remotion-composer ./

FROM python:3.11-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 YAPPY_PROJECT_ROOT=/data/projects
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl ca-certificates chromium && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt requirements-studio.txt ./
RUN pip install --no-cache-dir -r requirements-studio.txt
COPY . .
COPY --from=remotion /app/remotion-composer/node_modules /app/remotion-composer/node_modules
RUN useradd --create-home --uid 10001 app && mkdir -p /data/projects /app/output && chown -R app:app /data /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1
CMD ["uvicorn", "yappy_clipz.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
