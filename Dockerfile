# Stage 1: Build React
FROM node:22-alpine AS builder

WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Runtime
FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx supervisor && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Python deps in their own layer
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend source
COPY backend/ .

# Built React static files
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx: remove default site, install combined config
RUN rm -f /etc/nginx/sites-enabled/default
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Client address handling. entrypoint.sh rewrites both from TRUSTED_PROXIES at every start;
# these defaults (trust no reverse proxy) apply if it does not run.
RUN mkdir -p /etc/nginx/openmtg && \
    echo "# TRUSTED_PROXIES not applied: X-Forwarded-For is ignored." > /etc/nginx/openmtg/real_ip.conf
ENV FORWARDED_ALLOW_IPS=127.0.0.1

# Process supervisor config
COPY supervisord.conf /etc/supervisord.conf

# Entrypoint: run migrations then start processes
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

CMD ["/entrypoint.sh"]
