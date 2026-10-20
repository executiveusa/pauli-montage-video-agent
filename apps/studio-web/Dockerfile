# Build from the repository root: docker build -f apps/studio-web/Dockerfile .
FROM node:22-bookworm-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
COPY apps/studio-web/package.json apps/studio-web/package.json
RUN npm ci --workspace=@yappyverse/studio-web --include-workspace-root
COPY apps/studio-web apps/studio-web
RUN npm run build:studio

FROM node:22-bookworm-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/package.json ./package.json
COPY --from=build --chown=node:node /app/apps/studio-web/package.json ./apps/studio-web/package.json
COPY --from=build --chown=node:node /app/apps/studio-web/next.config.ts ./apps/studio-web/next.config.ts
COPY --from=build --chown=node:node /app/apps/studio-web/.next ./apps/studio-web/.next
COPY --from=build --chown=node:node /app/apps/studio-web/public ./apps/studio-web/public
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD node -e "fetch('http://127.0.0.1:3000/sign-in').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["npm", "run", "start", "--workspace=@yappyverse/studio-web"]
