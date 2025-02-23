FROM node:18.20.5-alpine3.21 as build-stage
WORKDIR /app

RUN npm config set registry https://mirrors.huaweicloud.com/repository/npm/

COPY package*.json ./

RUN npm install --omit=dev && \
    npm cache clean --force

COPY . .

ARG VUE_ENV
ENV VUE_ENV=${VUE_ENV}
ENV NODE_OPTIONS=--max-old-space-size=1536  # 设置 Node.js 内存限制为 1.5GB

RUN npm run build:${VUE_ENV}

FROM nginx:stable-alpine3.20-perl as production-stage
WORKDIR /usr/share/nginx/html

COPY --from=build-stage /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]