FROM python:3.13-slim

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN addgroup --system app && adduser --system --ingroup app --home /app app

WORKDIR /app/scripts

COPY --chown=app:app scripts/ /app/scripts/
COPY --chown=app:app frontend/ /app/frontend/

ENV FRONTEND_DIR=/app/frontend
ENV BAZI_PUBLIC=true

EXPOSE 7860

USER app

CMD ["python", "-m", "uvicorn", "bazi_engine.api:app", "--host", "0.0.0.0", "--port", "7860"]
