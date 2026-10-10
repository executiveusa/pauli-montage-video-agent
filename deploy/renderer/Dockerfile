# Isolated Code Animator render service. Build from the repo root:
#   docker build -f deploy/renderer/Dockerfile -t montage-renderer .
# Holds the package code only. No API env, no database client config, no secrets, no user data.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg chromium fonts-liberation ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin render
WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt "playwright>=1.45,<2"
COPY yappy_clipz /app/yappy_clipz
COPY scripts/verify_renderer_isolation.sh /app/scripts/verify_renderer_isolation.sh
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 YAPPY_RENDER_WORK=/work YAPPY_ANIMATOR_SCRATCH=/work/.scratch \
    YAPPY_ANIMATOR_CHROMIUM=/usr/bin/chromium
USER 10001
EXPOSE 8780
CMD ["python", "-m", "yappy_clipz.code_animator.render_service"]
