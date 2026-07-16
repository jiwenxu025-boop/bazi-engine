FROM python:3.13-slim

COPY requirements-lock.txt /app/requirements-lock.txt
RUN pip install --no-cache-dir -r requirements-lock.txt

RUN addgroup --system app && adduser --system --ingroup app --home /app app

WORKDIR /app/scripts

COPY --chown=app:app scripts/ /app/scripts/
COPY --chown=app:app frontend/ /app/frontend/

ENV FRONTEND_DIR=/app/frontend
ENV BAZI_PUBLIC=true

EXPOSE 7860

USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:7860/api/health', timeout=3)"

CMD ["python", "-m", "uvicorn", "bazi_engine.api:app", "--host", "0.0.0.0", "--port", "7860"]
