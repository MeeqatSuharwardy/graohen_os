"""Gunicorn configuration for production deployment"""

import os

# Server socket
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")

# Worker processes
workers = int(os.environ.get("GUNICORN_WORKERS", "4"))
worker_class = "uvicorn.workers.UvicornWorker"

# Timeouts
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()

# Process naming
proc_name = "flashdash"

# Preload=False: each worker loads app and runs init_db in its own process.
# Preload=True breaks async DB (connections don't survive fork).
preload = False
