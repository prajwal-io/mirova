FROM python:3.12-slim
WORKDIR /srv
COPY backend/requirements-lock.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && useradd --create-home app && mkdir -p /srv/.data && chown app:app /srv/.data
COPY --chown=app:app backend/app ./backend/app
ENV APP_ENV=production PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER app
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
