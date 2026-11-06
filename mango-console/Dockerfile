ARG NODE_IMAGE=node:20.20.1
ARG NGINX_IMAGE=nginx:1.27-alpine
FROM ${NODE_IMAGE} AS build-stage
WORKDIR /app
# 本 Dockerfile 必须以仓库根目录作为构建上下文，项目 Skill 才能进入前端产物。
COPY mango-console/package*.json ./
ARG NPM_REGISTRY=https://registry.npmmirror.com
RUN npm config set registry ${NPM_REGISTRY}
RUN npm install
COPY mango-console/ ./
# SkillCenterDrawer 的 import.meta.glob 从项目根目录 skill/ 读取文件；
# 构建阶段复制到对应的绝对位置，Vite 会将 Skill 文档及附件编译进静态资源。
COPY skill/ /skill/
ARG VUE_ENV
ENV VUE_ENV=${VUE_ENV}
# 给 Docker Runtime 与 Rollup 原生缓冲区预留内存，避免容器在构建末段被 OOM
# killer 直接终止（exit 137）。Vite 配置已同步减少 chunk 渲染峰值。
ARG NODE_HEAP_MB=2560
ENV NODE_OPTIONS=--max-old-space-size=${NODE_HEAP_MB}
RUN npm run build:${VUE_ENV}

FROM ${NGINX_IMAGE} AS production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY mango-console/nginx/default.conf /etc/nginx/conf.d/default.conf
RUN nginx -t
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
