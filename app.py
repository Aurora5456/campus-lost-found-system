import os
from functools import wraps
from secrets import token_urlsafe

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
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from constants import (
    CATEGORIES,
    CATEGORY_KEYS,
    STATUS_KEYS,
    STATUS_OPEN,
    STATUS_RESOLVED,
)
from imaging import remove_image_files, save_images
from matching import find_matches
from models import (
    Admin,
    Announcement,
    Message,
    PasswordResetToken,
    Post,
    PostImage,
    Student,
    db,
)
from notifications import email_enabled, notify_new_message, notify_password_reset

PER_PAGE = 9


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
        student = current_student()
        if student is None or not student.is_active:
            session.clear()
            flash("账号不存在或已被封禁，请联系管理员。", "danger")
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


def filtered_post_query(args):
    keyword = args.get("q", "").strip()
    post_type = args.get("type", "").strip()
    category = args.get("category", "").strip()
    status = args.get("status", "").strip()

    query = Post.query.join(Student).order_by(Post.created_at.desc())
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(
                Post.title.like(like),
                Post.item_name.like(like),
                Post.description.like(like),
                Post.location.like(like),
            )
        )
    if post_type in {"lost", "found"}:
        query = query.filter(Post.post_type == post_type)
    if category in CATEGORY_KEYS:
        query = query.filter(Post.category == category)
    if status in STATUS_KEYS:
        query = query.filter(Post.status == status)

    filters = {
        "q": keyword,
        "type": post_type if post_type in {"lost", "found"} else "",
        "category": category if category in CATEGORY_KEYS else "",
        "status": status if status in STATUS_KEYS else "",
    }
    return query, filters


def fill_post_from_form(post, form):
    post.title = form.get("title", "").strip()
    post.item_name = form.get("item_name", "").strip()
    post.post_type = form.get("post_type", "lost")
    category = form.get("category", "other").strip()
    post.category = category if category in CATEGORY_KEYS else "other"
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


def sync_cover(post):
    post.image_path = post.images[0].image_path if post.images else None


def apply_image_changes(post, form, files):
    """删除被勾选的旧图片，追加新上传的图片，并维护封面图。"""
    delete_ids = {int(x) for x in form.getlist("delete_images") if x.isdigit()}
    if delete_ids:
        for image in list(post.images):
            if image.id in delete_ids:
                remove_image_files(image.image_path, image.thumb_path)
                post.images.remove(image)

    remaining = Config.MAX_IMAGES_PER_POST - len(post.images)
    if remaining > 0:
        saved = save_images(files, limit=remaining)
        start = len(post.images)
        for offset, (image_path, thumb_path) in enumerate(saved):
            post.images.append(
                PostImage(
                    image_path=image_path,
                    thumb_path=thumb_path,
                    sort_order=start + offset,
                )
            )
    sync_cover(post)


def register_routes(app):
    @app.context_processor
    def inject_user():
        student = current_student()
        unread_count = 0
        if student:
            unread_count = Message.query.filter_by(
                receiver_id=student.id, is_read=False
            ).count()
        latest_announcement = None
        if student:
            latest_announcement = (
                Announcement.query.filter_by(is_active=True)
                .order_by(Announcement.created_at.desc())
                .first()
            )
        return {
            "current_student": student,
            "current_admin": current_admin(),
            "unread_count": unread_count,
            "categories": CATEGORIES,
            "latest_announcement": latest_announcement,
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
                if not student.is_active:
                    flash("该账号已被管理员封禁，无法登录。", "danger")
                    return render_template("student_login.html")
                session.clear()
                session["student_id"] = student.id
                flash("登录成功，欢迎回来。", "success")
                return redirect(url_for("student_home"))
            flash("学号或密码错误。", "danger")
        return render_template("student_login.html")

    @app.route("/student/register", methods=["GET", "POST"])
    def student_register():
        form = {}
        if request.method == "POST":
            form = request.form
            student_no = form.get("student_no", "").strip()
            name = form.get("name", "").strip()
            email = form.get("email", "").strip()
            password = form.get("password", "")
            confirm = form.get("confirm", "")

            error = None
            if not student_no or not name or not password:
                error = "请填写学号、姓名和密码。"
            elif len(password) < 6:
                error = "密码至少 6 位。"
            elif password != confirm:
                error = "两次输入的密码不一致。"
            elif Student.query.filter_by(student_no=student_no).first():
                error = "该学号已注册，请直接登录或找回密码。"
            elif email and Student.query.filter_by(email=email).first():
                error = "该邮箱已被使用。"

            if error:
                flash(error, "danger")
                return render_template("student_register.html", form=form)

            student = Student(
                student_no=student_no,
                name=name,
                email=email or None,
                password_hash=generate_password_hash(password),
            )
            db.session.add(student)
            db.session.commit()
            session.clear()
            session["student_id"] = student.id
            flash("注册成功，已自动登录。", "success")
            return redirect(url_for("student_home"))
        return render_template("student_register.html", form=form)

    @app.route("/student/forgot", methods=["GET", "POST"])
    def forgot_password():
        if request.method == "POST":
            student_no = request.form.get("student_no", "").strip()
            email = request.form.get("email", "").strip()
            student = Student.query.filter_by(student_no=student_no).first()

            if not student or (student.email or "") != email or not email:
                flash("学号与邮箱不匹配，或该账号未绑定邮箱。", "danger")
                return render_template("forgot_password.html")

            reset = PasswordResetToken.issue(student)
            db.session.add(reset)
            db.session.commit()

            sent = notify_password_reset(student, reset.token)
            if sent:
                flash("重置链接已发送到你的邮箱，请在 30 分钟内完成重置。", "success")
                return render_template("forgot_password.html")
            # 邮件未启用或发送失败时，直接在页面给出重置链接作为兜底
            reset_link = url_for("reset_password", token=reset.token)
            if email_enabled():
                flash("邮件暂时发送失败，请使用下方链接重置密码（30 分钟内有效）。", "info")
            else:
                flash("邮件服务未启用，请使用下方链接重置密码（30 分钟内有效）。", "info")
            return render_template("forgot_password.html", reset_link=reset_link)
        return render_template("forgot_password.html")

    @app.route("/student/reset/<token>", methods=["GET", "POST"])
    def reset_password(token):
        reset = PasswordResetToken.query.filter_by(token=token).first()
        if not reset or not reset.is_valid:
            flash("重置链接无效或已过期，请重新申请。", "danger")
            return redirect(url_for("forgot_password"))

        if request.method == "POST":
            password = request.form.get("password", "")
            confirm = request.form.get("confirm", "")
            if len(password) < 6:
                flash("密码至少 6 位。", "danger")
            elif password != confirm:
                flash("两次输入的密码不一致。", "danger")
            else:
                reset.student.password_hash = generate_password_hash(password)
                reset.used = True
                db.session.commit()
                flash("密码已重置，请使用新密码登录。", "success")
                return redirect(url_for("student_login"))
        return render_template("reset_password.html", token=token)

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

    @app.route("/settings", methods=["GET", "POST"])
    @student_required
    def settings():
        student = current_student()
        if request.method == "POST":
            email = request.form.get("email", "").strip()
            notify_email = request.form.get("notify_email") == "on"
            if email and Student.query.filter(
                Student.email == email, Student.id != student.id
            ).first():
                flash("该邮箱已被其他账号使用。", "danger")
            else:
                student.email = email or None
                student.notify_email = notify_email
                db.session.commit()
                flash("个人设置已保存。", "success")
            return redirect(url_for("settings"))
        return render_template("settings.html", student=student)

    @app.route("/posts")
    @student_required
    def student_home():
        query, filters = filtered_post_query(request.args)
        page = request.args.get("page", 1, type=int)
        pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)
        student_id = session["student_id"]
        stats = {
            "total": Post.query.count(),
            "lost": Post.query.filter_by(post_type="lost").count(),
            "found": Post.query.filter_by(post_type="found").count(),
            "mine": Post.query.filter_by(student_id=student_id).count(),
            "unread": Message.query.filter_by(
                receiver_id=student_id, is_read=False
            ).count(),
        }
        latest_found = (
            Post.query.filter_by(post_type="found")
            .order_by(Post.created_at.desc())
            .limit(3)
            .all()
        )
        return render_template(
            "student_home.html",
            posts=pagination.items,
            pagination=pagination,
            filters=filters,
            stats=stats,
            latest_found=latest_found,
        )

    @app.route("/announcements")
    @student_required
    def announcements_page():
        items = (
            Announcement.query.filter_by(is_active=True)
            .order_by(Announcement.created_at.desc())
            .all()
        )
        return render_template("announcements.html", announcements=items)

    @app.route("/posts/<int:post_id>")
    @student_required
    def post_detail(post_id):
        post = Post.query.get_or_404(post_id)
        matches = find_matches(post)
        return render_template("post_detail.html", post=post, matches=matches)

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
                apply_image_changes(post, request.form, request.files.getlist("images"))
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
                apply_image_changes(post, request.form, request.files.getlist("images"))
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("post_form.html", post=post, action="edit")

            db.session.commit()
            flash("帖子已更新。", "success")
            return redirect(url_for("post_detail", post_id=post.id))
        return render_template("post_form.html", post=post, action="edit")

    @app.route("/posts/<int:post_id>/status", methods=["POST"])
    @student_required
    def update_status(post_id):
        post = Post.query.get_or_404(post_id)
        if post.student_id != session["student_id"]:
            abort(403)
        new_status = request.form.get("status", "")
        if new_status in STATUS_KEYS:
            post.status = new_status
            db.session.commit()
            flash("帖子状态已更新为「%s」。" % post.status_label, "success")
        else:
            flash("状态值不正确。", "danger")
        return redirect(url_for("post_detail", post_id=post.id))

    @app.route("/posts/<int:post_id>/delete", methods=["POST"])
    @student_required
    def delete_post(post_id):
        post = Post.query.get_or_404(post_id)
        if post.student_id != session["student_id"]:
            abort(403)
        for image in post.images:
            remove_image_files(image.image_path, image.thumb_path)
        db.session.delete(post)
        db.session.commit()
        flash("帖子已删除，相关图片和私信记录已同步清理。", "success")
        return redirect(url_for("my_posts"))

    @app.route("/my-posts")
    @student_required
    def my_posts():
        posts = (
            Post.query.filter_by(student_id=session["student_id"])
            .order_by(Post.created_at.desc())
            .all()
        )
        return render_template("my_posts.html", posts=posts)

    @app.route("/messages")
    @student_required
    def messages():
        student_id = session["student_id"]
        rows = (
            Message.query.filter(
                or_(Message.sender_id == student_id, Message.receiver_id == student_id)
            )
            .order_by(Message.created_at.desc())
            .all()
        )
        threads = {}
        for msg in rows:
            other_id = msg.receiver_id if msg.sender_id == student_id else msg.sender_id
            key = (msg.post_id, other_id)
            if key not in threads:
                other = msg.receiver if msg.sender_id == student_id else msg.sender
                threads[key] = {
                    "message": msg,
                    "other": other,
                    "post": msg.post,
                    "unread": 0,
                }
            if msg.receiver_id == student_id and not msg.is_read:
                threads[key]["unread"] += 1
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
                message = Message(
                    sender_id=student_id,
                    receiver_id=other_id,
                    post_id=post.id,
                    content=content,
                )
                db.session.add(message)
                db.session.commit()
                notify_new_message(
                    message, post, sender=db.session.get(Student, student_id), receiver=other
                )
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
        query, filters = filtered_post_query(request.args)
        page = request.args.get("page", 1, type=int)
        pagination = query.paginate(page=page, per_page=12, error_out=False)
        stats = {
            "total": Post.query.count(),
            "lost": Post.query.filter_by(post_type="lost").count(),
            "found": Post.query.filter_by(post_type="found").count(),
            "students": Student.query.count(),
        }
        return render_template(
            "admin_posts.html",
            posts=pagination.items,
            pagination=pagination,
            filters=filters,
            stats=stats,
        )

    @app.route("/admin/dashboard")
    @admin_required
    def admin_dashboard():
        return render_template("admin_dashboard.html", data=build_dashboard_data())

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
            status = request.form.get("status", post.status)
            if status in STATUS_KEYS:
                post.status = status
            try:
                apply_image_changes(post, request.form, request.files.getlist("images"))
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("admin_edit_post.html", post=post)
            db.session.commit()
            flash("管理员已更新帖子。", "success")
            return redirect(url_for("admin_posts"))
        return render_template("admin_edit_post.html", post=post)

    @app.route("/admin/posts/<int:post_id>/delete", methods=["POST"])
    @admin_required
    def admin_delete_post(post_id):
        post = Post.query.get_or_404(post_id)
        for image in post.images:
            remove_image_files(image.image_path, image.thumb_path)
        db.session.delete(post)
        db.session.commit()
        flash("管理员已删除帖子，相关图片和私信记录已同步清理。", "success")
        return redirect(url_for("admin_posts"))

    @app.route("/admin/posts/<int:post_id>/status", methods=["POST"])
    @admin_required
    def admin_update_status(post_id):
        post = Post.query.get_or_404(post_id)
        new_status = request.form.get("status", "")
        if new_status in STATUS_KEYS:
            post.status = new_status
            db.session.commit()
            flash("已将帖子状态更新为「%s」。" % post.status_label, "success")
        else:
            flash("状态值不正确。", "danger")
        return redirect(request.referrer or url_for("admin_posts"))

    @app.route("/admin/posts/bulk", methods=["POST"])
    @admin_required
    def admin_bulk_posts():
        action = request.form.get("action", "")
        ids = [int(x) for x in request.form.getlist("post_ids") if x.isdigit()]
        if not ids:
            flash("请先勾选要操作的帖子。", "warning")
            return redirect(request.referrer or url_for("admin_posts"))

        posts = Post.query.filter(Post.id.in_(ids)).all()
        if action == "delete":
            for post in posts:
                for image in post.images:
                    remove_image_files(image.image_path, image.thumb_path)
                db.session.delete(post)
            db.session.commit()
            flash("已批量删除 %d 条帖子。" % len(posts), "success")
        elif action in {"resolve", "reopen"}:
            target = STATUS_RESOLVED if action == "resolve" else STATUS_OPEN
            for post in posts:
                post.status = target
            db.session.commit()
            label = "已解决" if action == "resolve" else "未解决"
            flash("已批量将 %d 条帖子标记为「%s」。" % (len(posts), label), "success")
        else:
            flash("未知的批量操作。", "danger")
        return redirect(request.referrer or url_for("admin_posts"))

    @app.route("/admin/students")
    @admin_required
    def admin_students():
        keyword = request.args.get("q", "").strip()
        query = Student.query.order_by(Student.created_at.desc())
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    Student.name.like(like),
                    Student.student_no.like(like),
                    Student.email.like(like),
                )
            )
        page = request.args.get("page", 1, type=int)
        pagination = query.paginate(page=page, per_page=15, error_out=False)
        post_counts = dict(
            db.session.query(Post.student_id, db.func.count(Post.id))
            .group_by(Post.student_id)
            .all()
        )
        return render_template(
            "admin_students.html",
            students=pagination.items,
            pagination=pagination,
            keyword=keyword,
            filters={"q": keyword},
            post_counts=post_counts,
        )

    @app.route("/admin/students/<int:student_id>/toggle-active", methods=["POST"])
    @admin_required
    def admin_toggle_student(student_id):
        student = Student.query.get_or_404(student_id)
        student.is_active = not student.is_active
        db.session.commit()
        state = "解封" if student.is_active else "封禁"
        flash("已%s学生「%s（%s）」。" % (state, student.name, student.student_no), "success")
        return redirect(request.referrer or url_for("admin_students"))

    @app.route("/admin/students/<int:student_id>/reset-password", methods=["POST"])
    @admin_required
    def admin_reset_student_password(student_id):
        student = Student.query.get_or_404(student_id)
        new_password = request.form.get("new_password", "").strip()
        if not new_password:
            new_password = token_urlsafe(6)
        elif len(new_password) < 6:
            flash("新密码至少 6 位。", "danger")
            return redirect(request.referrer or url_for("admin_students"))
        student.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash(
            "已重置「%s（%s）」的密码为：%s（请尽快告知本人并提醒修改）。"
            % (student.name, student.student_no, new_password),
            "success",
        )
        return redirect(request.referrer or url_for("admin_students"))

    @app.route("/admin/students/<int:student_id>/delete", methods=["POST"])
    @admin_required
    def admin_delete_student(student_id):
        student = Student.query.get_or_404(student_id)
        # 删除该学生参与的所有私信（含其作为收件人的会话），避免外键约束失败
        Message.query.filter(
            or_(Message.sender_id == student.id, Message.receiver_id == student.id)
        ).delete(synchronize_session=False)
        for post in list(student.posts):
            for image in post.images:
                remove_image_files(image.image_path, image.thumb_path)
        name, no = student.name, student.student_no
        db.session.delete(student)
        db.session.commit()
        flash("已删除学生「%s（%s）」及其帖子、私信。" % (name, no), "success")
        return redirect(url_for("admin_students"))

    @app.route("/admin/announcements", methods=["GET", "POST"])
    @admin_required
    def admin_announcements():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            body = request.form.get("body", "").strip()
            if not title or not body:
                flash("请填写公告标题和内容。", "danger")
            else:
                db.session.add(Announcement(title=title, body=body))
                db.session.commit()
                flash("公告已发布。", "success")
            return redirect(url_for("admin_announcements"))
        announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
        return render_template("admin_announcements.html", announcements=announcements)

    @app.route("/admin/announcements/<int:ann_id>/toggle", methods=["POST"])
    @admin_required
    def admin_toggle_announcement(ann_id):
        ann = Announcement.query.get_or_404(ann_id)
        ann.is_active = not ann.is_active
        db.session.commit()
        flash("公告已%s。" % ("上线" if ann.is_active else "下线"), "success")
        return redirect(url_for("admin_announcements"))

    @app.route("/admin/announcements/<int:ann_id>/delete", methods=["POST"])
    @admin_required
    def admin_delete_announcement(ann_id):
        ann = Announcement.query.get_or_404(ann_id)
        db.session.delete(ann)
        db.session.commit()
        flash("公告已删除。", "success")
        return redirect(url_for("admin_announcements"))

    @app.route("/admin/messages")
    @admin_required
    def admin_messages():
        keyword = request.args.get("q", "").strip()
        query = Message.query.order_by(Message.created_at.desc())
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(Message.content.like(like))
        page = request.args.get("page", 1, type=int)
        pagination = query.paginate(page=page, per_page=20, error_out=False)
        return render_template(
            "admin_messages.html",
            messages=pagination.items,
            pagination=pagination,
            keyword=keyword,
            filters={"q": keyword},
        )

    @app.route("/admin/messages/<int:message_id>/delete", methods=["POST"])
    @admin_required
    def admin_delete_message(message_id):
        message = Message.query.get_or_404(message_id)
        db.session.delete(message)
        db.session.commit()
        flash("已删除该条私信。", "success")
        return redirect(request.referrer or url_for("admin_messages"))


def build_dashboard_data():
    from collections import Counter
    from datetime import date, timedelta

    posts = Post.query.all()
    type_counter = Counter(p.post_type for p in posts)
    status_counter = Counter(p.status for p in posts)
    category_counter = Counter(p.category for p in posts)

    today = date.today()
    days = [today - timedelta(days=offset) for offset in range(13, -1, -1)]
    day_keys = [d.isoformat() for d in days]
    created_counter = Counter(p.created_at.date().isoformat() for p in posts)
    daily_counts = [created_counter.get(key, 0) for key in day_keys]

    resolved = status_counter.get(STATUS_RESOLVED, 0)
    total = len(posts)
    resolved_rate = round(resolved / total * 100, 1) if total else 0.0

    return {
        "total": total,
        "students": Student.query.count(),
        "messages": Message.query.count(),
        "resolved": resolved,
        "open": status_counter.get(STATUS_OPEN, 0),
        "resolved_rate": resolved_rate,
        "type_counts": {
            "lost": type_counter.get("lost", 0),
            "found": type_counter.get("found", 0),
        },
        "category_labels": [label for _, label in CATEGORIES],
        "category_counts": [category_counter.get(key, 0) for key, _ in CATEGORIES],
        "trend_labels": [key[5:] for key in day_keys],
        "trend_counts": daily_counts,
    }


def register_errors(app):
    @app.errorhandler(403)
    def forbidden(error):
        return render_template("error.html", code=403, message="没有权限访问该页面。"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, message="页面不存在。"), 404

    @app.errorhandler(413)
    def too_large(error):
        return (
            render_template("error.html", code=413, message="上传内容过大，请压缩后重试。"),
            413,
        )

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
