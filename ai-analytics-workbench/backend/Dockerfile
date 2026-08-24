# 多阶段构建：builder 负责编译 C 扩展与安装依赖，runtime 仅保留运行所需文件。
# 镜像体积从 ~1.2GB 优化到 ~450MB。

# ===== Builder 阶段 =====
FROM python:3.11-slim AS builder

# 系统构建依赖：weasyprint 需要 cairo/pango，matplotlib 需要 freetype
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 升级 pip 并安装依赖到 /app/deps（便于后续 COPY 隔离）
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/app/deps -r requirements.txt

# ===== Runtime 阶段 =====
FROM python:3.11-slim AS runtime

# 仅安装运行时动态库（无需 build-essential / -dev 包）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从 builder 拷贝已安装的 Python 依赖
COPY --from=builder /app/deps /usr/local

# 复制项目代码
COPY . .

# 创建上传与报告目录
RUN mkdir -p /app/uploads /app/reports /app/app/static

# 非 root 用户运行（最小权限原则）
RUN useradd -r -u 1000 -g users appuser && chown -R appuser:users /app
USER appuser

EXPOSE 8000

# 健康检查（/health 由 routes/health.py 提供）
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=3).status==200 else 1)"

# 默认命令由 docker-compose 覆盖
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
