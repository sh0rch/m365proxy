FROM python:3.11-slim

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source
COPY . /app
WORKDIR /app

# Default environment variable for config path
ENV CONFIG_PATH=/config/config.json

# Create directory for mail queue
RUN mkdir -p /app/queue

# Entrypoint with default config path
ENTRYPOINT ["python", "-m", "m365proxy"]
