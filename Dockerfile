# Multi-stage Dockerfile for production execution of RNA-seq API & Runner
FROM python:3.10-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies & R base
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    wget \
    r-base \
    r-base-dev \
    libxml2-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    libgsl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration and setup
COPY pyproject.toml /app/
COPY README.md /app/

RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -e .

COPY . /app

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
