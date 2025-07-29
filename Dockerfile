# 基于官方 Python 镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制后端代码
COPY backend/ /app/backend/
COPY database/ /app/database/
COPY README.md /app/README.md

# 安装依赖
RUN pip install --upgrade pip \
    && pip install -r /app/backend/requirements.txt

# 设置环境变量（可选）
ENV PYTHONUNBUFFERED=1

# 暴露后端端口
EXPOSE 8000

# 启动 FastAPI 后端
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
