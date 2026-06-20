from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    student_no = db.Column(db.String(32), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    posts = db.relationship("Post", back_populates="student", cascade="all, delete-orphan")


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

    @property
    def type_label(self):
        return "失物" if self.post_type == "lost" else "招领"


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
