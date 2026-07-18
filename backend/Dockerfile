# 后端服务镜像
# 构建上下文应为项目根目录，以便同时包含 backend/ 与 crawler/

FROM python:3.12-slim

WORKDIR /app/backend

# 安装系统依赖（Playwright 等可能需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖清单以利用构建缓存
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制完整项目代码
COPY . /app

# 让 backend 与 crawler 都能被导入
ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite:////app/backend/data/sentiment.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
