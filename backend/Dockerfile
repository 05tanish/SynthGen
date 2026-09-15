FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for:
# - psycopg2-binary (libpq-dev)
# - scipy / numpy / scikit-learn (build-essential, gfortran, libopenblas-dev)
# - sdv / ctgan (requires C++ compiler + BLAS)
# - general compilation (gcc, g++)
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

# Upgrade pip first to avoid legacy resolver issues
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
