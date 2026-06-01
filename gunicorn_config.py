"""
Gunicorn configuration for production deployment.
"""

import os
import multiprocessing

# Server socket
bind = f"{os.environ.get('HOST', '0.0.0.0')}:{os.environ.get('PORT', 5000)}"
backlog = 2048

# Worker processes
workers = os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1)
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"

# Process naming
proc_name = "vampiro-recorrencia"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = os.environ.get("SSL_KEY_FILE", None)
certfile = os.environ.get("SSL_CERT_FILE", None)
ssl_version = "TLSv1_2"
