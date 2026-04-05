FROM nginx:alpine

# Copy the locally compiled dist folder instead of building it inside Docker
# You must run 'npm install' and 'npm run build' on your host machine first
COPY dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost:5173/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
