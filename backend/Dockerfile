# Pin the exact patch so the air-gapped image matches the build host.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Deps first for layer caching. All wheels baked into the image at build time
# on the internet PC — nothing is fetched at runtime on the air-gapped host.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
