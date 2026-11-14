import os
import multiprocessing

# Port binding
port = os.getenv("PORT", "7860")
bind = f"0.0.0.0:{port}"

# Multi-process concurrency:
# 2 async Uvicorn workers are optimal for free-tier cloud containers (512MB RAM) to prevent OOM
default_workers = 2
workers = int(os.getenv("WEB_CONCURRENCY", default_workers))

# High-performance async Uvicorn worker
worker_class = "uvicorn.workers.UvicornWorker"

# Worker lifecycle & memory recycling (prevents memory bloat under heavy load)
max_requests = 500
max_requests_jitter = 50
timeout = 60
graceful_timeout = 20
keepalive = 5

# Logging
loglevel = os.getenv("LOG_LEVEL", "info")
accesslog = "-"
errorlog = "-"
