from datetime import datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from werkzeug.security import generate_password_hash

from app import create_app
from config import Config
from models import Admin, Announcement, Message, Post, Student, db


def ensure_database_exists():
    # 非 MySQL（例如本地用 SQLite 演示）无需预创建数据库
    if not Config.SQLALCHEMY_DATABASE_URI.startswith("mysql"):
        return
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
        ("20230001", "123456", "张三", "zhangsan@example.com"),
        ("20230002", "123456", "李四", "lisi@example.com"),
        ("20230003", "123456", "王五", "wangwu@example.com"),
        ("20230004", "123456", "赵六", "zhaoliu@example.com"),
        ("20230005", "123456", "孙七", "sunqi@example.com"),
        ("20230006", "123456", "周八", "zhouba@example.com"),
        ("20230007", "123456", "吴九", "wujiu@example.com"),
        ("20230008", "123456", "郑十", "zhengshi@example.com"),
        ("20230009", "123456", "钱多多", "qianduoduo@example.com"),
        ("20230010", "123456", "林晓", "linxiao@example.com"),
    ]
    for student_no, password, name, email in students:
        student = Student.query.filter_by(student_no=student_no).first()
        if not student:
            db.session.add(
                Student(
                    student_no=student_no,
                    password_hash=generate_password_hash(password),
                    name=name,
                    email=email,
                )
            )


def seed_admins():
    if not Admin.query.filter_by(username="admin").first():
        db.session.add(Admin(username="admin", password_hash=generate_password_hash("admin123")))


def seed_announcements():
    if Announcement.query.count() > 0:
        return
    announcements = [
        Announcement(
            title="欢迎使用校园失物招领系统",
            body="发布帖子时标题会自动识别物品和地点；捡到/丢失物品请如实填写，文明使用站内私信。",
        ),
        Announcement(
            title="期末失物集中认领通知",
            body="图书馆与各教学楼遗留物品已统一登记，请同学们尽快到失物招领处或在本平台认领，逾期物品将统一处理。",
        ),
    ]
    db.session.add_all(announcements)


def seed_posts():
    if Post.query.count() > 0:
        return

    students = {s.student_no: s for s in Student.query.all()}
    now = datetime.utcnow()

    # (标题, 物品, 类型, 分类, 状态, 描述, 地点, 联系备注, 学号, 距今天数)
    rows = [
        ("图书馆二楼遗失黑色保温杯", "黑色保温杯", "lost", "daily", "open",
         "杯身有校园纪念贴纸，周一下午自习后发现不见。", "图书馆二楼靠窗自习区",
         "请通过站内私信联系我，感谢。", "20230001", 1),
        ("图书馆捡到一个黑色水杯", "黑色保温杯", "found", "daily", "open",
         "在图书馆二楼自习区捡到黑色保温杯，杯身有贴纸。", "图书馆二楼",
         "描述贴纸图案后即可领取。", "20230003", 1),
        ("拾到一张校园卡", "校园卡", "found", "card", "open",
         "卡面姓名被磨损，卡号末尾为 0928。", "第一食堂门口",
         "请说明卡号信息后领取。", "20230002", 2),
        ("操场看台捡到蓝牙耳机盒", "蓝牙耳机盒", "found", "electronics", "resolved",
         "白色耳机盒，外壳有轻微划痕，失主已认领。", "东区操场看台第三排",
         "晚上 7 点后可私信约地点。", "20230003", 8),
        ("文达楼112遗失白色耳机", "白色耳机", "lost", "electronics", "open",
         "上午上课后落在座位附近，白色入耳式，带充电仓。", "文达楼112",
         "捡到请尽快私信我，必有酬谢。", "20230004", 1),
        ("文达楼112捡到白色耳机", "白色耳机", "found", "electronics", "open",
         "在文达楼112讲台旁捡到一副白色耳机，已交由我保管。", "文达楼112",
         "请说明耳机型号和外观特征后领取。", "20230005", 1),
        ("第二食堂丢失校园卡", "校园卡", "lost", "card", "open",
         "卡号末尾 0928，姓名周八，午餐后发现不见。", "第二食堂二楼",
         "捡到请私信，谢谢。", "20230006", 2),
        ("一号宿舍楼丢失钥匙串", "钥匙串", "lost", "key", "open",
         "三把钥匙带蓝色卡通挂件，含宿舍和自行车钥匙。", "一号宿舍楼下",
         "捡到请联系，非常着急。", "20230007", 3),
        ("三号教学楼捡到钥匙串", "钥匙串", "found", "key", "open",
         "在三号教学楼楼梯口捡到一串钥匙，带卡通挂件。", "三号教学楼楼梯口",
         "描述挂件样式后领取。", "20230008", 3),
        ("图书馆遗失高等数学课本", "高等数学课本", "lost", "book", "open",
         "同济版高数（上），扉页有名字，夹了几张笔记。", "图书馆三楼",
         "捡到请私信，谢谢好心人。", "20230009", 4),
        ("第一食堂丢失棕色钱包", "棕色钱包", "lost", "wallet", "open",
         "棕色短款钱包，内有少量现金和银行卡。", "第一食堂",
         "捡到请私信，现金可作酬谢。", "20230010", 2),
        ("第一食堂捡到棕色钱包", "棕色钱包", "found", "wallet", "open",
         "在第一食堂餐桌上捡到棕色钱包，已上交保管。", "第一食堂二楼",
         "请说明钱包内物品后领取。", "20230001", 2),
        ("体育馆遗失蓝色外套", "蓝色外套", "lost", "clothing", "resolved",
         "打球时落在场边，深蓝色连帽外套，已找回，感谢平台。", "体育馆篮球场",
         "已联系到，谢谢大家。", "20230002", 9),
        ("教学楼捡到黑色雨伞", "黑色雨伞", "found", "daily", "open",
         "长柄黑色雨伞，放在四号教学楼一楼伞架旁。", "四号教学楼一楼",
         "如是你的可直接来取。", "20230003", 5),
        ("文逸楼遗失iPad", "iPad", "lost", "electronics", "open",
         "深空灰 iPad，带黑色保护套，锁屏是校园风景照。", "文逸楼报告厅",
         "重要资料较多，捡到必重谢。", "20230004", 1),
        ("文逸楼捡到一台iPad", "iPad", "found", "electronics", "open",
         "在文逸楼报告厅座位下捡到一台平板，带黑色套。", "文逸楼报告厅",
         "请说明锁屏壁纸内容后领取。", "20230005", 1),
    ]

    posts = []
    for (title, item, ptype, cat, status, desc, loc, note, sno, days_ago) in rows:
        student = students.get(sno)
        if not student:
            continue
        created = now - timedelta(days=days_ago, hours=len(posts))
        posts.append(
            Post(
                title=title,
                item_name=item,
                post_type=ptype,
                category=cat,
                status=status,
                description=desc,
                location=loc,
                contact_note=note,
                student_id=student.id,
                created_at=created,
                updated_at=created,
            )
        )
    db.session.add_all(posts)


def seed_messages():
    if Message.query.count() > 0:
        return

    students = {s.student_no: s for s in Student.query.all()}
    posts = {p.title: p for p in Post.query.all()}
    now = datetime.utcnow()

    # (帖子标题, 发件人学号, 收件人学号, 内容, 距今小时, 是否已读)
    rows = [
        ("文达楼112捡到白色耳机", "20230004", "20230005",
         "你好，文达楼112捡到的白色耳机是不是我的？充电仓上有个小划痕。", 20, True),
        ("文达楼112捡到白色耳机", "20230005", "20230004",
         "应该是的，型号方便说一下吗？对上就还给你。", 19, True),
        ("文达楼112捡到白色耳机", "20230004", "20230005",
         "是华为 FreeBuds，明天上午我来文达楼找你可以吗？", 18, False),
        ("三号教学楼捡到钥匙串", "20230007", "20230008",
         "那串带蓝色卡通挂件的钥匙应该是我的，挂件是哆啦A梦。", 10, True),
        ("三号教学楼捡到钥匙串", "20230008", "20230007",
         "对得上，你什么时候方便来三号教学楼门口拿？", 9, False),
        ("第一食堂捡到棕色钱包", "20230010", "20230001",
         "棕色钱包是我的，里面有一张工商银行卡和两张饭票。", 6, False),
    ]

    messages = []
    for (post_title, sender_no, receiver_no, content, hours_ago, is_read) in rows:
        post = posts.get(post_title)
        sender = students.get(sender_no)
        receiver = students.get(receiver_no)
        if not (post and sender and receiver):
            continue
        messages.append(
            Message(
                sender_id=sender.id,
                receiver_id=receiver.id,
                post_id=post.id,
                content=content,
                is_read=is_read,
                created_at=now - timedelta(hours=hours_ago),
            )
        )
    db.session.add_all(messages)


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
        seed_announcements()
        db.session.commit()
        seed_messages()
        db.session.commit()
        print("数据库初始化完成：已创建表、测试账号、示例帖子和私信。")


if __name__ == "__main__":
    main()
