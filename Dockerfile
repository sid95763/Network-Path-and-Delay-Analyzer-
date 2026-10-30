FROM python:3.11-slim

# Install traceroute and ping utilities
RUN apt-get update && \
    apt-get install -y --no-install-recommends traceroute iputils-ping dnsutils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY static/ ./static/

# Create data directory for SQLite
RUN mkdir -p data

# Expose port
EXPOSE 8000

# Run the server
# NOTE: Must run with --cap-add=NET_RAW for traceroute to work
# docker run --cap-add=NET_RAW -p 8000:8000 network-analyzer
CMD ["python", "-m", "app.main"]
