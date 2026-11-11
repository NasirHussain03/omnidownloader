import os
import multiprocessing

# Port binding
port = os.getenv("PORT", "7860")
bind = f"0.0.0.0:{port}"

# Multi-process concurrency:
# Defaults to (2 * CPU cores + 1) or overridden by WEB_CONCURRENCY
default_workers = max(multiprocessing.cpu_count() * 2 + 1, 2)
workers = int(os.getenv("WEB_CONCURRENCY", default_workers))

# High-performance async Uvicorn worker
worker_class = "uvicorn.workers.UvicornWorker"

# Worker lifecycle & memory recycling (prevents memory bloat under heavy load)
max_requests = 1000
max_requests_jitter = 50
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
loglevel = os.getenv("LOG_LEVEL", "info")
accesslog = "-"
errorlog = "-"
