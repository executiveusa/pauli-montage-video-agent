# STAGING BUILD HARNESS ONLY - packages the 22bd2758 studio-web source unchanged.
# Lives only on branch staging-images-22bd2758; NOT part of PR #64 and carries no app code.
FROM node:22-bookworm-slim AS build
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY package.json ./
COPY apps/studio-web/package.json apps/studio-web/package.json
RUN npm install --omit=optional
COPY apps/studio-web apps/studio-web
RUN npm run build:studio

FROM node:22-bookworm-slim AS runtime
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY --from=build /app /app
EXPOSE 3000
CMD ["npm", "run", "start", "--workspace=@yappyverse/studio-web"]
