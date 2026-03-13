FROM node:21.7.1-alpine
WORKDIR /app
COPY package*.json ./
RUN npm config set registry https://registry.npmmirror.com && \
    npm install --legacy-peer-deps && \
    npm install ajv@^6.12.6 ajv-keywords@^3.5.2 --legacy-peer-deps
COPY . ./
ENV NODE_OPTIONS=--openssl-legacy-provider
RUN npm run build
RUN npm install --global http-server
CMD ["npx", "-y", "http-server", "-p", "8000", "/app/build"]
