# Montage studio web (Next.js) for self-hosting. Build context: repository root.
FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/studio-web/package.json apps/studio-web/package.json
RUN npm ci --omit=optional && npm install --no-save @next/swc-linux-x64-gnu@16.3.3
COPY apps/studio-web apps/studio-web
ENV NEXT_TELEMETRY_DISABLED=1 NEXT_OUTPUT=standalone
RUN npm run build:studio

FROM node:22-bookworm-slim AS runtime
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* && useradd --create-home --uid 10001 app
COPY --from=build --chown=app:app /app/apps/studio-web/.next/standalone ./
COPY --from=build --chown=app:app /app/apps/studio-web/.next/static ./apps/studio-web/.next/static
COPY --from=build --chown=app:app /app/apps/studio-web/public ./apps/studio-web/public
USER app
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD curl -fsS http://127.0.0.1:3000/ >/dev/null || exit 1
CMD ["node", "apps/studio-web/server.js"]
