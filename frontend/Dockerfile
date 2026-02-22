# ════════════════════════════════════════════════════════════════
# AlphaTheta v2 — 前端 Dockerfile (Nginx 静态文件服务)
#
# 使用 nginx:alpine 精简镜像 (~40MB)
# 非 root 运行 (nginx 官方镜像 1.25+ 支持 NGINX_ENTRYPOINT_WORKER_PROCESSES_AUTOTUNE)
# ════════════════════════════════════════════════════════════════

FROM nginx:1.25-alpine

# 清理默认页面
RUN rm -rf /usr/share/nginx/html/*

# 复制前端静态文件
COPY index.html /usr/share/nginx/html/
COPY app.js /usr/share/nginx/html/
COPY style.css /usr/share/nginx/html/
COPY renderCharts.js /usr/share/nginx/html/

# 复制 ESM 模块目录
COPY js/ /usr/share/nginx/html/js/

# 复制图片资源 (二维码等)
COPY img/ /usr/share/nginx/html/img/

# 复制 nginx 配置 — SPA fallback + API 反向代理
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1
