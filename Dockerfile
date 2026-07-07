# Bazi Engine — Docker 部署
FROM python:3.13-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY scripts/ /app/scripts/
COPY frontend/ /app/frontend/

ENV FRONTEND_DIR=/app/frontend
ENV BAZI_PUBLIC=true

EXPOSE 7860

CMD ["python", "-m", "uvicorn", "scripts.bazi_engine.api:app", "--host", "0.0.0.0", "--port", "8080"]
