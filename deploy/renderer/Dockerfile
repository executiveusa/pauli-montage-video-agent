# Isolated Code Animator render service. Built by CI (montage-images workflow), never on the box:
#   docker build -f deploy/renderer/Dockerfile --target runtime -t montage-renderer .
# Carries only yappy_clipz/__init__.py (lazy exports) and yappy_clipz/code_animator/. No repository,
# service, contracts or API modules, no API env, no database config, no secrets, no user data.
FROM python:3.12-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg chromium fonts-liberation ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin render \
    && mkdir -p /work && chown 10001:10001 /work
RUN pip install --no-cache-dir "playwright>=1.45,<2"
WORKDIR /app
COPY yappy_clipz/__init__.py /app/yappy_clipz/__init__.py
COPY yappy_clipz/code_animator /app/yappy_clipz/code_animator
COPY scripts/verify_renderer_isolation.sh /app/scripts/verify_renderer_isolation.sh
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 YAPPY_RENDER_WORK=/work YAPPY_ANIMATOR_SCRATCH=/work/.scratch \
    YAPPY_ANIMATOR_CHROMIUM=/usr/bin/chromium
USER 10001
EXPOSE 8780
CMD ["python", "-m", "yappy_clipz.code_animator.render_service"]

# CI runs the renderer-only tests (including the real-chromium ones) inside the built image.
FROM runtime AS test
USER root
RUN pip install --no-cache-dir pytest
COPY tests/studio/test_code_animator_core.py tests/studio/test_code_animator_isolation.py tests/studio/test_code_animator_smoke.py /app/tests/
RUN chown -R 10001:10001 /app/tests
USER 10001
ENV YAPPY_ANIMATOR_SCRATCH=/tmp/scratch
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "/app/tests"]
