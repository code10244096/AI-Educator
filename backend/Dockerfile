FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    # 数据、上传文件、日志都在宿主机数据卷上（见 docker-compose.yml），镜像里不含任何数据或密钥
    DATABASE_URL=sqlite+aiosqlite:////app/data/teaching_assistant.db \
    UPLOAD_DIR=/app/uploads \
    API_OUTPUT_ROOT=/app/logs/api_runs

# 复制依赖文件并安装（bcrypt / pymupdf 均有预编译 wheel，无需编译工具）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码（.dockerignore 已排除 config.json、.env、*.db、uploads/、api_runs/、venv/、tests/ 等）
COPY . .

# 数据目录（运行时由数据卷覆盖）
RUN mkdir -p /app/data /app/uploads /app/logs

EXPOSE 8000

# 单进程运行：批改队列与登录限流都在进程内
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
