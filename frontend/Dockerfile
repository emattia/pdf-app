# syntax=docker/dockerfile:1

FROM node:16.19.0-alpine3.16 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ENV NODE_ENV=production
RUN npm run build
RUN npm ci --prod

FROM node:16.19.0-alpine3.16
USER node:node
WORKDIR /app
COPY --from=builder --chown=node:node /app/build ./build
COPY --from=builder --chown=node:node /app/node_modules ./node_modules
COPY --chown=node:node package.json .
EXPOSE 5173
CMD ["node","build"]