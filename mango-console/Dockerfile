# 构建阶段
FROM node:18.20.5-alpine3.21 AS build-stage
WORKDIR /app

# 设置 npm 镜像源
RUN npm config set registry https://mirrors.huaweicloud.com/repository/npm/

# 复制 package.json 和 package-lock.json
COPY package*.json ./

# 安装依赖（分步安装以减少内存占用）
RUN npm install --omit=dev && \
    npm cache clean --force

# 复制项目文件
COPY . .

# 设置构建环境变量
ARG VUE_ENV
ENV VUE_ENV=${VUE_ENV}
ENV NODE_OPTIONS=--max-old-space-size=1536  # 设置 Node.js 内存限制为 1.5GB

# 运行构建命令
RUN npm run build:${VUE_ENV}

# 生产阶段
FROM nginx:stable-alpine3.20-perl AS production-stage
WORKDIR /usr/share/nginx/html

# 从构建阶段复制构建结果
COPY --from=build-stage /app/dist /usr/share/nginx/html

# 暴露端口
EXPOSE 80

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]