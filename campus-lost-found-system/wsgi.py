"""WSGI entrypoint for production hosting (e.g. gunicorn on Render).

Start command:  gunicorn wsgi:app --bind 0.0.0.0:$PORT

Uses SQLite under a data directory and seeds demo data on first boot, so the
app runs with zero external services. Local MySQL development via app.py /
_run.py is unaffected.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.environ.get("DATA_DIR") or ("/data" if os.path.isdir("/data") else os.path.join(BASE_DIR, "var"))
DB_DIR = os.path.join(DATA_DIR, "db")
os.makedirs(DB_DIR, exist_ok=True)

os.environ.setdefault("DATABASE_URL", f"sqlite:///{os.path.join(DB_DIR, 'app.db')}")

from app import app  # noqa: E402
from init_db import seed_admins, seed_posts, seed_students  # noqa: E402
from models import db  # noqa: E402

with app.app_context():
    db.create_all()
    seed_students()
    seed_admins()
    db.session.commit()
    seed_posts()
    db.session.commit()
