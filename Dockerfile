# Use a slim version of Python for a smaller image size
FROM python:3.12-slim

# Set environment variables to prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for PostgreSQL (needed for the drivers)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8000 (FastAPI default)
EXPOSE 8000

# Start the application
# We use 0.0.0.0 so it can be reached from outside the container (like an AWS Load Balancer)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]