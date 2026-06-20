import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "campus-lost-found-dev-secret")

    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "123456")
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_NAME = os.environ.get("DB_NAME", "lost_found_system")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4",
    )
    # Render/Heroku 给的连接串是 postgres://，SQLAlchemy 只认 postgresql://
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    if SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "connect_args": {"check_same_thread": False},
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_recycle": 280,
        }

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    MAX_IMAGES_PER_POST = 6
    THUMB_MAX_SIZE = (480, 480)
    IMAGE_MAX_SIZE = (1280, 1280)

    # 站点外链地址，用于在邮件里拼接找回密码、私信等链接
    SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "http://127.0.0.1:5000")

    # 邮件通知（SMTP）。未配置 SMTP_HOST 时自动降级为站内通知，不会报错。
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
    MAIL_FROM = os.environ.get("MAIL_FROM", "校园失物招领系统 <no-reply@campus.local>")
