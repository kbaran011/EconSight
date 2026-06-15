# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf.template
EXPOSE 80
CMD ["/bin/sh", "-c", "NS=$(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf); case \"$NS\" in *:*) NGINX_RESOLVER=\"[$NS]\";; *) NGINX_RESOLVER=\"$NS\";; esac; export NGINX_RESOLVER && envsubst '${BACKEND_URL} ${PORT} ${NGINX_RESOLVER}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
