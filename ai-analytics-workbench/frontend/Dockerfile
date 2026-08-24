# 多阶段构建：dev 用于开发（热更新），prod 用于生产

# ===== 开发阶段 =====
FROM node:20-alpine AS dev
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

# ===== 构建阶段 =====
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# ===== 生产阶段 =====
FROM nginx:alpine AS prod
COPY --from=builder /app/dist /usr/share/nginx/html
RUN echo 'server { \
    listen 80; \
    location / { root /usr/share/nginx/html; try_files $uri $uri/ /index.html; } \
    location /api/ { proxy_pass http://backend:8000; } \
    location /ws/ { proxy_pass http://backend:8000; proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade"; } \
    location /reports/ { proxy_pass http://backend:8000; } \
}' > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
