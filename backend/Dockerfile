FROM python:3.11-slim

WORKDIR /app

# Install system dependencies in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    gfortran \
    libpq-dev \
    libopenblas-dev \
    liblapack-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel for faster builds
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Copy requirements first for better caching
COPY requirements.txt .

# Install lightweight packages first (quick wins)
RUN pip install --no-cache-dir \
    python-dotenv \
    python-dateutil \
    email-validator

# Install PyTorch CPU version explicitly (prevents 3GB+ CUDA download)
RUN pip install --no-cache-dir \
    torch==2.0.1+cpu \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Install remaining requirements (will skip torch as it's already installed)
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

ENV PYTHONPATH=/app

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
