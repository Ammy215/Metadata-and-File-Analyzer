# Build stage - the app is Vite/React, not Next.js (no NEXT_PUBLIC_API_URL,
# no server-side rendering) - it builds to static files served by nginx.
# node:22 (Active LTS) - node:18's LTS window ended April 2025 (no more
# security patches); this stage is build-time only and never ships in the
# final image, so the bump carries no runtime risk to the served app.
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Serve stage - the built app makes relative /api/... calls, proxied by
# the outer reverse-proxy nginx (see ../nginx.conf) straight through to
# the backend container, so no build-time API URL needs baking in here.
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
# Replaces the base image's default server block with one that has an
# SPA try_files fallback - see nginx.conf for why this is required.
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
