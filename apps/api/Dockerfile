FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (git for cloning, patch for patching)
RUN apt-get update && apt-get install -y git patch && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY apps/api/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY packages ./packages
COPY apps/api ./apps/api
COPY demo ./demo
COPY data ./data

# Create necessary directories
RUN mkdir -p data/runs data/workspaces

# Expose API port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
