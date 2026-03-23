# ── Stage 1: Build ─────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build
# Produces /app/dist — a folder of static HTML/JS/CSS

# ── Stage 2: Serve ─────────────────────────────────────────────
FROM nginx:alpine

# Copy the built static files into nginx's serve directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy our SPA nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
