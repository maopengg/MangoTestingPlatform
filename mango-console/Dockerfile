FROM node:18.20.5-alpine3.21 AS build-stage
WORKDIR /app
COPY package*.json ./
RUN npm config set registry https://mirrors.huaweicloud.com/repository/npm/
RUN npm install
COPY . .
ARG VUE_ENV
ENV VUE_ENV=${VUE_ENV}
ENV NODE_OPTIONS=--max-old-space-size=4096
RUN npm run build:${VUE_ENV}

FROM nginx:stable-alpine3.20-perl AS production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]