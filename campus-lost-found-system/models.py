from datetime import datetime, timedelta
from secrets import token_urlsafe

from flask_sqlalchemy import SQLAlchemy

from constants import STATUS_OPEN, category_label, status_label

db = SQLAlchemy()


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    student_no = db.Column(db.String(32), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=True, index=True)
    notify_email = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    posts = db.relationship("Post", back_populates="student", cascade="all, delete-orphan")
    reset_tokens = db.relationship(
        "PasswordResetToken", back_populates="student", cascade="all, delete-orphan"
    )


class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    item_name = db.Column(db.String(120), nullable=False)
    post_type = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(40), nullable=False, default="other", index=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_OPEN, index=True)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(160), nullable=False)
    contact_note = db.Column(db.String(255), nullable=False)
    image_path = db.Column(db.String(255))
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    student = db.relationship("Student", back_populates="posts")
    messages = db.relationship("Message", back_populates="post", cascade="all, delete-orphan")
    images = db.relationship(
        "PostImage",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="PostImage.sort_order",
    )

    @property
    def type_label(self):
        return "失物" if self.post_type == "lost" else "招领"

    @property
    def status_label(self):
        return status_label(self.post_type, self.status)

    @property
    def category_label(self):
        return category_label(self.category)

    @property
    def is_resolved(self):
        return self.status != STATUS_OPEN

    @property
    def cover(self):
        if self.images:
            return self.images[0].image_path
        return self.image_path

    @property
    def cover_thumb(self):
        if self.images:
            return self.images[0].thumb_path or self.images[0].image_path
        return self.image_path


class PostImage(db.Model):
    __tablename__ = "post_images"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False, index=True)
    image_path = db.Column(db.String(255), nullable=False)
    thumb_path = db.Column(db.String(255))
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    post = db.relationship("Post", back_populates="images")


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, nullable=False, default=False)

    sender = db.relationship("Student", foreign_keys=[sender_id])
    receiver = db.relationship("Student", foreign_keys=[receiver_id])
    post = db.relationship("Post", back_populates="messages")


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    student = db.relationship("Student", back_populates="reset_tokens")

    @staticmethod
    def issue(student, valid_minutes=30):
        token = token_urlsafe(32)
        return PasswordResetToken(
            student_id=student.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(minutes=valid_minutes),
        )

    @property
    def is_valid(self):
        return not self.used and self.expires_at > datetime.utcnow()
