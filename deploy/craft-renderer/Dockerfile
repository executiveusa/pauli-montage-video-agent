# Isolated craft render service (document/image family). Built by CI (montage-images workflow), never on the box:
#   docker build -f deploy/craft-renderer/Dockerfile --target runtime -t montage-craft-renderer .
# Carries only yappy_clipz/__init__.py (lazy exports) and yappy_clipz/crafts/, plus the pinned engine
# binaries. No repository, service, contracts or API modules, no API env, no database config, no secrets.
# Engine binaries are pinned by release tag AND sha256; the build fails if the download does not match.
# Re-pinning is a change to the two ARGs below, reviewed like any other CI change.
ARG PDFCRAFT_VERSION=0.5.0
ARG PDFCRAFT_SHA256=9fe5d1ef82924667184d68dc6aea2f23c98bdcd4d3802327c8cf17cc5d9da72b

FROM debian:bookworm-slim AS fetch
ARG PDFCRAFT_VERSION
ARG PDFCRAFT_SHA256
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL -o /tmp/pdfcraft.tar.gz "https://github.com/storytold/pdfcraft/releases/download/v${PDFCRAFT_VERSION}/pdfcraft-cli-${PDFCRAFT_VERSION}-linux-x86_64.tar.gz" \
    && echo "${PDFCRAFT_SHA256}  /tmp/pdfcraft.tar.gz" | sha256sum -c - \
    && mkdir -p /opt/pdfcraft && tar -xzf /tmp/pdfcraft.tar.gz -C /opt/pdfcraft --strip-components=1 \
    && test -x /opt/pdfcraft/pdfcraft-cli

FROM python:3.12-slim AS runtime
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin craft \
    && mkdir -p /work && chown 10001:10001 /work
COPY --from=fetch /opt/pdfcraft /opt/pdfcraft
WORKDIR /app
COPY yappy_clipz/__init__.py /app/yappy_clipz/__init__.py
COPY yappy_clipz/crafts /app/yappy_clipz/crafts
COPY scripts/verify_renderer_isolation.sh /app/scripts/verify_renderer_isolation.sh
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 YAPPY_RENDER_WORK=/work YAPPY_PDFCRAFT_BIN=/opt/pdfcraft/pdfcraft-cli
USER 10001
EXPOSE 8790
CMD ["python", "-m", "yappy_clipz.crafts.service"]

# CI runs the craft tests (spec, runner, HTTP service with the real pinned binary) inside the built image.
FROM runtime AS test
USER root
RUN pip install --no-cache-dir pytest
COPY tests/__init__.py /app/tests/__init__.py
COPY tests/studio/pdf_fixtures.py tests/studio/test_pdfcraft_core.py /app/tests/studio/
RUN chown -R 10001:10001 /app/tests
USER 10001
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "/app/tests/studio/test_pdfcraft_core.py"]
