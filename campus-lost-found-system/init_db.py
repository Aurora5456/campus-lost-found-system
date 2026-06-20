from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from werkzeug.security import generate_password_hash

from app import create_app
from config import Config
from models import Admin, Post, Student, db


def ensure_database_exists():
    server_uri = (
        f"mysql+pymysql://{Config.DB_USER}:{Config.DB_PASSWORD}"
        f"@{Config.DB_HOST}:{Config.DB_PORT}/?charset=utf8mb4"
    )
    engine = create_engine(server_uri, pool_pre_ping=True)
    with engine.connect() as connection:
        connection.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
        connection.commit()


def seed_students():
    students = [
        ("20230001", "123456", "张三"),
        ("20230002", "123456", "李四"),
        ("20230003", "123456", "王五"),
    ]
    for student_no, password, name in students:
        student = Student.query.filter_by(student_no=student_no).first()
        if not student:
            db.session.add(
                Student(
                    student_no=student_no,
                    password_hash=generate_password_hash(password),
                    name=name,
                )
            )


def seed_admins():
    if not Admin.query.filter_by(username="admin").first():
        db.session.add(Admin(username="admin", password_hash=generate_password_hash("admin123")))


def seed_posts():
    if Post.query.count() > 0:
        return

    zhang = Student.query.filter_by(student_no="20230001").first()
    li = Student.query.filter_by(student_no="20230002").first()
    wang = Student.query.filter_by(student_no="20230003").first()

    posts = [
        Post(
            title="图书馆二楼遗失黑色保温杯",
            item_name="黑色保温杯",
            post_type="lost",
            description="杯身有校园纪念贴纸，周一下午自习后发现不见。",
            location="图书馆二楼靠窗自习区",
            contact_note="请通过站内私信联系我，感谢。",
            student_id=zhang.id,
        ),
        Post(
            title="拾到一张校园卡",
            item_name="校园卡",
            post_type="found",
            description="卡面姓名被磨损，卡号末尾为 0928。",
            location="第一食堂门口",
            contact_note="请说明卡号信息后领取。",
            student_id=li.id,
        ),
        Post(
            title="操场看台捡到蓝牙耳机盒",
            item_name="蓝牙耳机盒",
            post_type="found",
            description="白色耳机盒，外壳有轻微划痕。",
            location="东区操场看台第三排",
            contact_note="晚上 7 点后可私信约地点。",
            student_id=wang.id,
        ),
    ]
    db.session.add_all(posts)


def main():
    try:
        ensure_database_exists()
    except OperationalError as exc:
        print("MySQL 连接失败，无法自动创建数据库。")
        print("请确认 MySQL 服务已启动，并检查 config.py 中的 DB_USER / DB_PASSWORD / DB_HOST / DB_PORT。")
        raise exc

    app = create_app()
    with app.app_context():
        try:
            db.session.execute(text("SELECT 1"))
        except OperationalError as exc:
            print("MySQL 连接失败，请确认数据库已创建并已启动。")
            print("默认数据库：lost_found_system，默认账号：root，默认密码：123456。")
            print("如果你的 MySQL 密码不同，请修改 config.py 或设置环境变量。")
            raise exc

        db.drop_all()
        db.create_all()
        seed_students()
        seed_admins()
        db.session.commit()
        seed_posts()
        db.session.commit()
        print("数据库初始化完成：已创建表、测试账号和示例帖子。")


if __name__ == "__main__":
    main()
