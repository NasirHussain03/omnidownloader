# Multi-platform Dockerfile optimized for high-throughput scaling
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies including ffmpeg, ca-certificates, curl, unzip, nodejs
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    curl \
    unzip \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Deno static binary for native YouTube challenge solving
RUN curl -fsSL https://deno.land/install.sh | sh && \
    cp /root/.deno/bin/deno /usr/local/bin/deno && \
    chmod 755 /usr/local/bin/deno

# Hugging Face Spaces runs as user 1000 by default
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install Python dependencies as user
COPY --chown=user:user requirements.txt .
USER user
RUN pip install --no-cache-dir --user --upgrade -r requirements.txt

# Copy application source code
COPY --chown=user:user . .

# Default port: 7860 for Hugging Face Spaces, or overridden by $PORT on Render
EXPOSE 7860

# Launch with production Gunicorn process manager & async Uvicorn workers
CMD ["sh", "-c", "python -m gunicorn -c gunicorn_conf.py app.main:app"]
