# Этап 1: Сборка приложения
FROM node:23-slim AS builder

COPY package.json package.json
RUN npm install
COPY . .
RUN npm run build

# Этап 2: Использование Nginx для обслуживания приложения
FROM nginx:alpine

# Копирование файлов из этапа сборки (builder)
COPY --from=builder /dist /usr/share/nginx/html
COPY --from=builder /nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]