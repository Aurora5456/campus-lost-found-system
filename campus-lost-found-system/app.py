import os
from functools import wraps
from uuid import uuid4

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import or_, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from config import Config
from models import Admin, Message, Post, Student, db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    register_routes(app)
    register_errors(app)
    return app


def current_student():
    student_id = session.get("student_id")
    if not student_id:
        return None
    return db.session.get(Student, student_id)


def current_admin():
    admin_id = session.get("admin_id")
    if not admin_id:
        return None
    return db.session.get(Admin, admin_id)


def student_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("student_id"):
            flash("请先登录学生账号。", "warning")
            return redirect(url_for("student_login"))
        return view(*args, **kwargs)

    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            flash("请先登录管理员账号。", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapper


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def save_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        raise ValueError("图片格式不正确，只允许 jpg、jpeg、png、gif。")

    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid4().hex}.{ext}"
    save_path = os.path.join(Config.UPLOAD_FOLDER, unique_name)
    file_storage.save(save_path)
    return f"uploads/{unique_name}"


def build_post_query(keyword=None):
    query = Post.query.join(Student).order_by(Post.created_at.desc())
    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                Post.title.like(like),
                Post.item_name.like(like),
                Post.description.like(like),
                Post.location.like(like),
            )
        )
    return query


def fill_post_from_form(post, form):
    post.title = form.get("title", "").strip()
    post.item_name = form.get("item_name", "").strip()
    post.post_type = form.get("post_type", "lost")
    post.description = form.get("description", "").strip()
    post.location = form.get("location", "").strip()
    post.contact_note = form.get("contact_note", "").strip()


def validate_post_form(form):
    required = ["title", "item_name", "description", "location", "contact_note"]
    if any(not form.get(field, "").strip() for field in required):
        return "请完整填写标题、物品名称、描述、地点和联系说明。"
    if form.get("post_type") not in {"lost", "found"}:
        return "帖子类型不正确。"
    return None


def register_routes(app):
    @app.context_processor
    def inject_user():
        return {
            "current_student": current_student(),
            "current_admin": current_admin(),
        }

    @app.route("/")
    def index():
        if session.get("admin_id"):
            return redirect(url_for("admin_posts"))
        return redirect(url_for("student_home"))

    @app.route("/health")
    def health():
        db.session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}

    @app.route("/student/login", methods=["GET", "POST"])
    def student_login():
        if request.method == "POST":
            student_no = request.form.get("student_no", "").strip()
            password = request.form.get("password", "")
            student = Student.query.filter_by(student_no=student_no).first()
            if student and check_password_hash(student.password_hash, password):
                session.clear()
                session["student_id"] = student.id
                flash("登录成功，欢迎回来。", "success")
                return redirect(url_for("student_home"))
            flash("学号或密码错误。", "danger")
        return render_template("student_login.html")

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            admin = Admin.query.filter_by(username=username).first()
            if admin and check_password_hash(admin.password_hash, password):
                session.clear()
                session["admin_id"] = admin.id
                flash("管理员登录成功。", "success")
                return redirect(url_for("admin_posts"))
            flash("管理员账号或密码错误。", "danger")
        return render_template("admin_login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("已退出登录。", "info")
        return redirect(url_for("student_login"))

    @app.route("/posts")
    @student_required
    def student_home():
        keyword = request.args.get("q", "").strip()
        posts = build_post_query(keyword).all()
        student_id = session["student_id"]
        stats = {
            "total": Post.query.count(),
            "lost": Post.query.filter_by(post_type="lost").count(),
            "found": Post.query.filter_by(post_type="found").count(),
            "mine": Post.query.filter_by(student_id=student_id).count(),
            "unread": Message.query.filter_by(receiver_id=student_id, is_read=False).count(),
        }
        latest_found = Post.query.filter_by(post_type="found").order_by(Post.created_at.desc()).limit(3).all()
        return render_template(
            "student_home.html",
            posts=posts,
            keyword=keyword,
            stats=stats,
            latest_found=latest_found,
        )

    @app.route("/posts/<int:post_id>")
    @student_required
    def post_detail(post_id):
        post = Post.query.get_or_404(post_id)
        return render_template("post_detail.html", post=post)

    @app.route("/posts/new", methods=["GET", "POST"])
    @student_required
    def create_post():
        if request.method == "POST":
            error = validate_post_form(request.form)
            if error:
                flash(error, "danger")
                return render_template("post_form.html", post=None, action="create")

            post = Post(student_id=session["student_id"])
            fill_post_from_form(post, request.form)
            try:
                post.image_path = save_image(request.files.get("image"))
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("post_form.html", post=post, action="create")

            db.session.add(post)
            db.session.commit()
            flash("帖子发布成功。", "success")
            return redirect(url_for("post_detail", post_id=post.id))
        return render_template("post_form.html", post=None, action="create")

    @app.route("/posts/<int:post_id>/edit", methods=["GET", "POST"])
    @student_required
    def edit_post(post_id):
        post = Post.query.get_or_404(post_id)
        if post.student_id != session["student_id"]:
            abort(403)

        if request.method == "POST":
            error = validate_post_form(request.form)
            if error:
                flash(error, "danger")
                return render_template("post_form.html", post=post, action="edit")

            fill_post_from_form(post, request.form)
            try:
                image_path = save_image(request.files.get("image"))
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("post_form.html", post=post, action="edit")
            if image_path:
                post.image_path = image_path

            db.session.commit()
            flash("帖子已更新。", "success")
            return redirect(url_for("post_detail", post_id=post.id))
        return render_template("post_form.html", post=post, action="edit")

    @app.route("/posts/<int:post_id>/delete", methods=["POST"])
    @student_required
    def delete_post(post_id):
        post = Post.query.get_or_404(post_id)
        if post.student_id != session["student_id"]:
            abort(403)
        db.session.delete(post)
        db.session.commit()
        flash("帖子已删除，相关私信记录已同步清理。", "success")
        return redirect(url_for("my_posts"))

    @app.route("/my-posts")
    @student_required
    def my_posts():
        posts = Post.query.filter_by(student_id=session["student_id"]).order_by(Post.created_at.desc()).all()
        return render_template("my_posts.html", posts=posts)

    @app.route("/messages")
    @student_required
    def messages():
        student_id = session["student_id"]
        rows = (
            Message.query.filter(or_(Message.sender_id == student_id, Message.receiver_id == student_id))
            .order_by(Message.created_at.desc())
            .all()
        )
        threads = {}
        for msg in rows:
            other_id = msg.receiver_id if msg.sender_id == student_id else msg.sender_id
            key = (msg.post_id, other_id)
            if key not in threads:
                other = msg.receiver if msg.sender_id == student_id else msg.sender
                threads[key] = {"message": msg, "other": other, "post": msg.post}
        return render_template("messages.html", threads=list(threads.values()))

    @app.route("/chat/<int:post_id>/<int:other_id>", methods=["GET", "POST"])
    @student_required
    def chat(post_id, other_id):
        student_id = session["student_id"]
        post = Post.query.get_or_404(post_id)
        other = Student.query.get_or_404(other_id)
        if student_id == other_id:
            flash("不能和自己发起私聊。", "warning")
            return redirect(url_for("post_detail", post_id=post.id))
        if post.student_id not in {student_id, other_id}:
            abort(403)

        if request.method == "POST":
            content = request.form.get("content", "").strip()
            if not content:
                flash("消息内容不能为空。", "danger")
            else:
                db.session.add(
                    Message(
                        sender_id=student_id,
                        receiver_id=other_id,
                        post_id=post.id,
                        content=content,
                    )
                )
                db.session.commit()
                flash("消息已发送。", "success")
                return redirect(url_for("chat", post_id=post.id, other_id=other.id))

        Message.query.filter_by(
            post_id=post.id,
            sender_id=other.id,
            receiver_id=student_id,
            is_read=False,
        ).update({"is_read": True})
        db.session.commit()

        chat_messages = (
            Message.query.filter(
                Message.post_id == post.id,
                or_(
                    (Message.sender_id == student_id) & (Message.receiver_id == other.id),
                    (Message.sender_id == other.id) & (Message.receiver_id == student_id),
                ),
            )
            .order_by(Message.created_at.asc())
            .all()
        )
        return render_template("chat.html", post=post, other=other, chat_messages=chat_messages)

    @app.route("/contact/<int:post_id>")
    @student_required
    def contact_publisher(post_id):
        post = Post.query.get_or_404(post_id)
        if post.student_id == session["student_id"]:
            flash("这是你自己的帖子，无需联系自己。", "info")
            return redirect(url_for("post_detail", post_id=post.id))
        return redirect(url_for("chat", post_id=post.id, other_id=post.student_id))

    @app.route("/admin/posts")
    @admin_required
    def admin_posts():
        keyword = request.args.get("q", "").strip()
        posts = build_post_query(keyword).all()
        stats = {
            "total": Post.query.count(),
            "lost": Post.query.filter_by(post_type="lost").count(),
            "found": Post.query.filter_by(post_type="found").count(),
            "students": Student.query.count(),
        }
        return render_template("admin_posts.html", posts=posts, keyword=keyword, stats=stats)

    @app.route("/admin/posts/<int:post_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_edit_post(post_id):
        post = Post.query.get_or_404(post_id)
        if request.method == "POST":
            error = validate_post_form(request.form)
            if error:
                flash(error, "danger")
                return render_template("admin_edit_post.html", post=post)
            fill_post_from_form(post, request.form)
            try:
                image_path = save_image(request.files.get("image"))
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("admin_edit_post.html", post=post)
            if image_path:
                post.image_path = image_path
            db.session.commit()
            flash("管理员已更新帖子。", "success")
            return redirect(url_for("admin_posts"))
        return render_template("admin_edit_post.html", post=post)

    @app.route("/admin/posts/<int:post_id>/delete", methods=["POST"])
    @admin_required
    def admin_delete_post(post_id):
        post = Post.query.get_or_404(post_id)
        db.session.delete(post)
        db.session.commit()
        flash("管理员已删除帖子，相关私信记录已同步清理。", "success")
        return redirect(url_for("admin_posts"))


def register_errors(app):
    @app.errorhandler(403)
    def forbidden(error):
        return render_template("error.html", code=403, message="没有权限访问该页面。"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, message="页面不存在。"), 404

    @app.errorhandler(OperationalError)
    def database_error(error):
        db.session.rollback()
        return (
            render_template(
                "error.html",
                code=500,
                message="MySQL 连接失败，请检查数据库是否启动，以及 config.py 中的账号、密码、库名是否正确。",
            ),
            500,
        )

    @app.errorhandler(SQLAlchemyError)
    def sqlalchemy_error(error):
        db.session.rollback()
        return render_template("error.html", code=500, message="数据库操作失败，请稍后重试。"), 500


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
