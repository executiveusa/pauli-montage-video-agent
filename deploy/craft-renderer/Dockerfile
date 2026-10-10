# Isolated craft render service (document/image family). Built by CI (montage-images workflow), never on the box:
#   docker build -f deploy/craft-renderer/Dockerfile --target runtime -t montage-craft-renderer .
# Carries only yappy_clipz/__init__.py (lazy exports) and yappy_clipz/crafts/, plus the pinned engine
# binaries. No repository, service, contracts or API modules, no API env, no database config, no secrets.
# Engine binaries are pinned by release tag AND sha256; the build fails if the download does not match.
# Re-pinning is a change to the ARG pairs below (tag + sha256 per engine), reviewed like any other CI change.
ARG VECTORCRAFT_VERSION=0.8.0
ARG VECTORCRAFT_SHA256=48b8e671a415f5dde912a049f82cda05b66f7e6fd79a81b458816ff9186882cf
ARG PDFCRAFT_VERSION=0.5.0
ARG PDFCRAFT_SHA256=9fe5d1ef82924667184d68dc6aea2f23c98bdcd4d3802327c8cf17cc5d9da72b
ARG PHOTOCRAFT_VERSION=0.6.0
ARG PHOTOCRAFT_SHA256=b65fd701b6360d3ba0b05900474bf92d9926c76802fefa7be996690fcbc396c6
ARG LIGHTCRAFT_VERSION=0.5.0
ARG LIGHTCRAFT_SHA256=164170bb3745b94cffc1e05d59b20778eb51698558224f846e9e1f5424da3265

FROM debian:bookworm-slim AS fetch
ARG VECTORCRAFT_VERSION
ARG VECTORCRAFT_SHA256
ARG PDFCRAFT_VERSION
ARG PDFCRAFT_SHA256
ARG PHOTOCRAFT_VERSION
ARG PHOTOCRAFT_SHA256
ARG LIGHTCRAFT_VERSION
ARG LIGHTCRAFT_SHA256
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL -o /tmp/pdfcraft.tar.gz "https://github.com/storytold/pdfcraft/releases/download/v${PDFCRAFT_VERSION}/pdfcraft-cli-${PDFCRAFT_VERSION}-linux-x86_64.tar.gz" \
    && echo "${PDFCRAFT_SHA256}  /tmp/pdfcraft.tar.gz" | sha256sum -c - \
    && mkdir -p /opt/pdfcraft && tar -xzf /tmp/pdfcraft.tar.gz -C /opt/pdfcraft --strip-components=1 \
    && test -x /opt/pdfcraft/pdfcraft-cli
# Image engines: only the headless CLI is shipped (no GUI, no mcp/serve use; the service never passes those subcommands).
RUN curl -fsSL -o /tmp/photocraft.tar.gz "https://github.com/storytold/photocraft/releases/download/v${PHOTOCRAFT_VERSION}/photocraft-${PHOTOCRAFT_VERSION}-linux-x86_64.tar.gz" \
    && echo "${PHOTOCRAFT_SHA256}  /tmp/photocraft.tar.gz" | sha256sum -c - \
    && mkdir -p /tmp/ph /opt/photocraft/bin && tar -xzf /tmp/photocraft.tar.gz -C /tmp/ph --strip-components=1 \
    && cp /tmp/ph/bin/photocraft-cli /opt/photocraft/bin/photocraft-cli && test -x /opt/photocraft/bin/photocraft-cli
RUN curl -fsSL -o /tmp/lightcraft.tar.gz "https://github.com/storytold/lightcraft/releases/download/v${LIGHTCRAFT_VERSION}/lightcraft-${LIGHTCRAFT_VERSION}-linux-x86_64.tar.gz" \
    && echo "${LIGHTCRAFT_SHA256}  /tmp/lightcraft.tar.gz" | sha256sum -c - \
    && mkdir -p /tmp/lc /opt/lightcraft/bin && tar -xzf /tmp/lightcraft.tar.gz -C /tmp/lc --strip-components=1 \
    && cp /tmp/lc/bin/lightcraft-cli /opt/lightcraft/bin/lightcraft-cli && test -x /opt/lightcraft/bin/lightcraft-cli

RUN curl -fsSL -o /tmp/vectorcraft.tar.gz "https://github.com/storytold/vectorcraft/releases/download/v${VECTORCRAFT_VERSION}/vectorcraft-${VECTORCRAFT_VERSION}-linux-x86_64.tar.gz" \
    && echo "${VECTORCRAFT_SHA256}  /tmp/vectorcraft.tar.gz" | sha256sum -c - \
    && mkdir -p /tmp/vc /opt/vectorcraft/bin && tar -xzf /tmp/vectorcraft.tar.gz -C /tmp/vc --strip-components=1 \
    && cp /tmp/vc/bin/vectorcraft-cli /opt/vectorcraft/bin/vectorcraft-cli && test -x /opt/vectorcraft/bin/vectorcraft-cli

FROM python:3.12-slim AS runtime
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin craft \
    && mkdir -p /work && chown 10001:10001 /work
COPY --from=fetch /opt/pdfcraft /opt/pdfcraft
COPY --from=fetch /opt/photocraft /opt/photocraft
COPY --from=fetch /opt/lightcraft /opt/lightcraft
COPY --from=fetch /opt/vectorcraft /opt/vectorcraft
WORKDIR /app
COPY yappy_clipz/__init__.py /app/yappy_clipz/__init__.py
COPY yappy_clipz/crafts /app/yappy_clipz/crafts
COPY scripts/verify_renderer_isolation.sh /app/scripts/verify_renderer_isolation.sh
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 YAPPY_RENDER_WORK=/work YAPPY_PDFCRAFT_BIN=/opt/pdfcraft/pdfcraft-cli YAPPY_PHOTOCRAFT_BIN=/opt/photocraft/bin/photocraft-cli YAPPY_LIGHTCRAFT_BIN=/opt/lightcraft/bin/lightcraft-cli YAPPY_VECTORCRAFT_BIN=/opt/vectorcraft/bin/vectorcraft-cli
USER 10001
EXPOSE 8790
CMD ["python", "-m", "yappy_clipz.crafts.service"]

# CI runs the craft tests (spec, runner, HTTP service with the real pinned binary) inside the built image.
FROM runtime AS test
USER root
RUN pip install --no-cache-dir pytest pillow
COPY tests/__init__.py /app/tests/__init__.py
COPY tests/studio/pdf_fixtures.py tests/studio/test_pdfcraft_core.py tests/studio/image_fixtures.py tests/studio/test_imagecraft_core.py tests/studio/vector_fixtures.py tests/studio/test_vectorcraft_core.py /app/tests/studio/
RUN chown -R 10001:10001 /app/tests
USER 10001
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "/app/tests/studio/test_pdfcraft_core.py", "/app/tests/studio/test_imagecraft_core.py", "/app/tests/studio/test_vectorcraft_core.py"]
