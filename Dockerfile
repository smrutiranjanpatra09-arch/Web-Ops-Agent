# Single image used for all four services (mock site, agent API, dashboard,
# scheduler) - they share the same codebase, so the compose file just varies
# the command. Based on the official Playwright image because Chromium needs a
# long list of system libraries that are painful to install by hand.
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# install deps first so code changes don't invalidate the dependency layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# the base image ships browsers, but make sure the chromium build this
# playwright version expects is present
RUN playwright install chromium

COPY . .

# writable dirs for sqlite, screenshots, and logs
RUN mkdir -p data/sample_snapshots logs

EXPOSE 5050 8000 8501

# default to the dashboard; docker-compose overrides this per service
CMD ["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
