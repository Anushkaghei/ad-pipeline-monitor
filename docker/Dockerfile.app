FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY ingestion/ /app/ingestion/
COPY monitoring/ /app/monitoring/
COPY api/ /app/api/
COPY scripts/ /app/scripts/
COPY data/ /app/data/
COPY lambda/ /app/lambda/

# Default: run the scheduler
CMD ["python", "-m", "scripts.run_pipeline"]
