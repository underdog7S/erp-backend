"""
Gunicorn Configuration for Production
Usage: gunicorn erp.wsgi:application --config gunicorn_config.py
"""
import multiprocessing
import os

# Server socket
bind = os.getenv('GUNICORN_BIND', "127.0.0.1:8000")
backlog = 2048

# Worker processes
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'sync')
worker_connections = 1000
timeout = int(os.getenv('GUNICORN_TIMEOUT', 120))
keepalive = 5

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = os.getenv('GUNICORN_ACCESS_LOG', '-')  # '-' means stdout
errorlog = os.getenv('GUNICORN_ERROR_LOG', '-')     # '-' means stderr
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')

# Process naming
proc_name = 'zenitherp'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if running Gunicorn with SSL directly, usually Nginx handles SSL)
keyfile = None
certfile = None

