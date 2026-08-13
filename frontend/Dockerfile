# =============================================================================
# IU Digital · Analítica Académica — Frontend (React CRA + Nginx)
# Multi-stage build para Google Cloud Run (contenedor sirviendo estáticos)
# =============================================================================

# ---------- Stage 1: Build React ----------
FROM node:20-alpine AS builder
WORKDIR /app

# Instalar dependencias (yarn.lock cacheado)
COPY package.json yarn.lock ./
RUN corepack enable && yarn install --frozen-lockfile

# Build args — inyectados por Cloud Build o al hacer docker build --build-arg
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

# Copiar código y compilar
COPY . .
RUN yarn build

# ---------- Stage 2: Nginx runtime ----------
FROM nginx:1.27-alpine AS runtime

# Copiar config nginx (SPA routing + gzip + no-cache index.html)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar bundle
COPY --from=builder /app/build /usr/share/nginx/html

# Cloud Run inyecta PORT. Debemos escuchar en $PORT (no en 80).
ENV PORT=8080
EXPOSE 8080

# Reemplazar puerto en la config al iniciar y arrancar nginx en foreground
CMD ["/bin/sh", "-c", "sed -i \"s/listen 8080;/listen ${PORT};/\" /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
