# Dockerfile for Vue 3
FROM node:18

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制项目文件
COPY . .

# 构建项目
RUN npm run build

# 启动开发服务器
CMD ["npm", "run", "serve", "--", "--host", "0.0.0.0"]
