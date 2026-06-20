"""Deployment entrypoint.

Wraps the existing Flask app as an ASGI app (for uvicorn) and makes the
project self-contained on a fresh container:

- Stores the SQLite database and uploaded images under a persistent data
  directory (a mounted volume at /data when available) so user data survives
  restarts and redeploys.
- Creates tables and seeds demo accounts/posts on first boot (idempotent).

The original Flask entrypoint (app.py / _run.py) and the MySQL defaults are
left untouched for local development.
"""

import os
import shutil

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
LOCAL_DATA_DIR = os.path.join(BASE_DIR, ".data")
DATA_DIR = os.environ.get("DATA_DIR") or ("/data" if os.path.isdir("/data") else LOCAL_DATA_DIR)

DB_DIR = os.path.join(DATA_DIR, "db")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Persist SQLite on the data directory unless an explicit DB URL is provided.
os.environ.setdefault("DATABASE_URL", f"sqlite:///{os.path.join(DB_DIR, 'app.db')}")

# Persist uploaded images: point static/uploads at the data directory so the
# existing url_for('static', filename='uploads/..') links keep working.
STATIC_UPLOADS = os.path.join(BASE_DIR, "static", "uploads")
if DATA_DIR != LOCAL_DATA_DIR:
    try:
        if not os.path.islink(STATIC_UPLOADS) and os.path.isdir(STATIC_UPLOADS):
            for name in os.listdir(STATIC_UPLOADS):
                src = os.path.join(STATIC_UPLOADS, name)
                dst = os.path.join(UPLOADS_DIR, name)
                if not os.path.exists(dst):
                    shutil.move(src, dst)
            shutil.rmtree(STATIC_UPLOADS)
        os.makedirs(os.path.dirname(STATIC_UPLOADS), exist_ok=True)
        if not os.path.exists(STATIC_UPLOADS):
            os.symlink(UPLOADS_DIR, STATIC_UPLOADS)
    except OSError:
        pass

from app import app as flask_app  # noqa: E402
from init_db import seed_admins, seed_posts, seed_students  # noqa: E402
from models import db  # noqa: E402

with flask_app.app_context():
    db.create_all()
    seed_students()
    seed_admins()
    db.session.commit()
    seed_posts()
    db.session.commit()

from a2wsgi import WSGIMiddleware  # noqa: E402
from fastapi import FastAPI  # noqa: E402

app = FastAPI()
app.mount("/", WSGIMiddleware(flask_app))
