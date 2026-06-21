# 校园失物招领系统

基于 Python **Flask** 的校园失物招领平台,分**学生端**与**管理员端**。学生可注册登录、发布失物/招领帖、多图上传、站内私信联系、查看智能匹配推荐、找回/修改密码;管理员拥有完整后台(数据看板、用户管理、全站公告、私信监管、批量操作、任意帖子状态管理)。

数据由环境变量 `DATABASE_URL` 决定后端,支持 **MySQL / SQLite / PostgreSQL**,应用首次启动会自动建表并写入种子数据(幂等)。

## 线上演示

已部署到 Render,长期在线,任何人可直接访问(无需本地运行):

- 网址:<https://campus-lost-found-f02g.onrender.com>
- 学生账号:学号 `20230001` ~ `20230010`,密码均 `123456`
- 管理员账号:`admin` / `admin123`

> 免费版闲置约 15 分钟会休眠,首次打开需等约 30–50 秒冷启动。线上数据存于 Render PostgreSQL,**重启/重新部署不会丢失**(种子数据仅在库为空时写入)。

## 快速开始(SQLite,推荐,免装数据库)

最省事的本地运行方式,零外部依赖:

```bash
# 1. 安装依赖(建议 Python 3.10+)
pip install -r requirements.txt

# 2. 指向一个 SQLite 文件(文件会自动落到 instance/ 目录并自动创建)
#    PowerShell:
$env:DATABASE_URL = "sqlite:///dev.db"
#    CMD:
set DATABASE_URL=sqlite:///dev.db

# 3. 初始化数据库(建表 + 写入测试账号与示例数据)
python init_db.py

# 4. 启动
python app.py
```

浏览器访问 <http://127.0.0.1:5000>。

> 注意:SQLite 连接串请用 `sqlite:///dev.db`(不要写成 `sqlite:///instance/dev.db`)。Flask-SQLAlchemy 会把相对路径的 SQLite 文件放到应用的 `instance/` 目录下,多写一层 `instance/` 反而会报 `unable to open database file`。删除生成的 `instance/dev.db` 后重新 `python init_db.py` 即可重置数据。

## 用 MySQL 运行(可选)

不设置 `DATABASE_URL` 时,默认使用 `config.py` 中的 MySQL 配置:

```text
主机 localhost  端口 3306  库名 lost_found_system  用户 root  密码 123456
```

若本机 MySQL 账号不同,改 `config.py` 的 `DB_USER`/`DB_PASSWORD`,或设置环境变量 `DB_USER`、`DB_PASSWORD`、`DB_HOST`、`DB_PORT`、`DB_NAME`。然后:

```bash
# 先在 MySQL 里建库(或执行项目自带的 database.sql)
CREATE DATABASE lost_found_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

python init_db.py   # 建表 + 种子数据
python app.py
```

Windows 下也可直接双击 `init_db.bat`(初始化)、`start.bat`(后台启动并打开浏览器)、`stop.bat`(停止)。这些脚本走默认 MySQL 方式;用 SQLite 请按上面的「快速开始」手动设环境变量后运行。

## 邮件通知(可选)

系统在「有人发来私信」或「学生找回密码」时可发邮件。支持两条通道,**都没配置时自动降级**(私信只走站内未读提醒、找回密码直接在页面给出重置链接),不会报错:

1. **Brevo HTTP API(推荐,主通道)** —— 走 HTTPS 443 端口,免费托管平台(如 Render 免费版)通常放行。设置:

   ```text
   BREVO_API_KEY        Brevo 后台生成的 xkeysib- 开头的 key
   BREVO_SENDER_EMAIL   发件人邮箱(须在 Brevo「Senders」里验证通过)
   BREVO_SENDER_NAME    发件人显示名(可选,默认「校园失物招领系统」)
   ```

2. **SMTP(备用通道)** —— 部分免费托管平台会屏蔽出站 SMTP 端口,此时请改用 Brevo:

   ```text
   SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_USE_TLS / MAIL_FROM
   ```

另外用 `SITE_BASE_URL` 配置站点外链地址(默认 `http://127.0.0.1:5000`),邮件里的重置/私信链接会基于它拼接。`send_email` 会优先尝试 Brevo,失败再退回 SMTP。

> 线上为何用 Brevo:Render 免费版封锁了对外 SMTP 端口,直连 QQ/Gmail SMTP 会 `Network is unreachable`,因此改用 Brevo 的 HTTP API 绕过端口限制。
>
> 短信通知需接第三方服务商(阿里云短信、Twilio 等),`notifications.py` 预留了 `send_sms` 接口,按需实现。

## 测试账号与示例数据

学生账号(密码均 `123456`):

| 学号 | 姓名 | 学号 | 姓名 |
| --- | --- | --- | --- |
| 20230001 | 张三 | 20230006 | 周八 |
| 20230002 | 李四 | 20230007 | 吴九 |
| 20230003 | 王五 | 20230008 | 郑十 |
| 20230004 | 赵六 | 20230009 | 钱多多 |
| 20230005 | 孙七 | 20230010 | 林晓 |

管理员:`admin` / `admin123`。

初始化还会写入:**16 条帖子**(失物/招领各 8,覆盖证件/电子/钥匙/书籍/钱包/衣物/生活用品等分类,含多组可互相匹配的「丢失↔捡到」对子)、**6 条示例私信**、**2 条公告**。

## 功能清单

### 学生端
- **账号**:注册、登录、退出;找回密码(绑定邮箱发重置链接,token 30 分钟过期且一次性);**登录后在设置页修改密码**(校验当前密码 + 新密码≥6 位 + 两次一致 + 新≠旧);设置通知邮箱与私信邮件通知开关。
- **帖子**:发布失物/招领帖,**标题自动识别物品名与地点**(前端启发式,可手动改);多图上传(Pillow 自动压缩 + 生成缩略图,单帖最多 6 张);列表分页 + 按类型/分类/状态/关键词筛选搜索;帖子详情(图片相册 + 物品信息 + 匹配推荐);仅本人可编辑/删除自己的帖子;**状态机**:寻找中/招领中 ↔ 已找回/已归还。
- **分类**:证件卡片 / 电子产品 / 钥匙 / 书籍资料 / 衣物饰品 / 钱包现金 / 生活用品 / 其他。
- **私信与匹配**:站内私信 + 导航栏**未读角标**;失物↔招领**智能匹配**,按物品名(40%)+ 地点(25%)+ 标题描述(20%)+ 分类(15%)加权,折算成 **0–100% 匹配度**。
- **公告**:首页只显示**最新 1 条**横幅(可点 × 关闭,浏览器记住),独立 `/announcements` 页查看全部,其它页面不再堆叠公告。

### 管理员端
- 管理员登录;**数据看板**(帖子总量、已解决率、近 14 天新增趋势、类型/分类图表,Chart.js)。
- **帖子管理**:查看/搜索/筛选/编辑/删除所有帖子;一键修改任意帖子状态;**批量操作**(多选后批量删除 / 标记已解决 / 重新打开)。
- **用户管理**:学生列表(发帖数/状态/搜索)、封禁/解封(被封禁者无法登录)、重置密码、删除账号。
- **全站公告**:发布 / 上下线 / 删除。
- **私信监管**:按内容搜索、查看收发件人与关联帖子、删除不当私信。

### 工程与安全
- 密码用 **Werkzeug** 加盐哈希保存(明文不入库);后端路由按学生/管理员身份做权限校验。
- 删除帖子时同步清理关联私信与图片文件。
- 密钥、数据库串、邮件凭据全部走环境变量,不写死在代码里。

## 技术栈

- Python **Flask** + **Jinja2**(服务端渲染,无前端框架)
- **Flask-SQLAlchemy** ORM
- 数据库:MySQL + PyMySQL(本地默认)/ SQLite(零配置)/ PostgreSQL + psycopg2(线上持久化)
- **Pillow**:图片压缩与缩略图
- **Chart.js**:管理员数据看板图表
- **Werkzeug**:密码哈希
- 邮件:**Brevo HTTP API**(主)+ **smtplib**(SMTP 备用)
- 部署:**Gunicorn** + **Render**

## 项目结构

代码位于仓库根目录(`git clone` 后直接可见,无多层嵌套):

```text
app.py            应用与全部路由(create_app 工厂)
wsgi.py           生产入口(gunicorn wsgi:app),首次启动自动建表 + 种子数据
config.py         配置(DATABASE_URL、上传、邮件、站点外链)
models.py         数据模型(Student/Admin/Post/PostImage/Message/Announcement/PasswordResetToken)
constants.py      分类、状态等常量与中文标签
init_db.py        初始化脚本(建表 + 写入测试账号与示例数据)
notifications.py  邮件通知(Brevo HTTP API + SMTP,未配置自动降级)
matching.py       失物↔招领智能匹配打分
imaging.py        图片保存、压缩、缩略图
database.sql      MySQL 建库建表脚本(可选)
templates/        Jinja2 模板    static/  CSS/JS/上传图片
render.yaml       Render 一键部署蓝图(含 free 计划 PostgreSQL)
*.bat / start.ps1 Windows 本地初始化/启动/停止脚本(默认 MySQL)
```

## 部署(Render / 任意 WSGI 平台)

生产用 `wsgi.py` 作入口,Gunicorn 运行:

```bash
gunicorn wsgi:app
```

仓库内 `render.yaml` 是 Render 一键部署蓝图(free 计划),并声明了一个 free 计划 **PostgreSQL**,连接串通过 `DATABASE_URL` 自动注入,数据跨重启/重新部署不丢失。推送到部署分支(`main`)后 Render 自动重新构建上线。

> 提醒:Render 免费 PostgreSQL 有有效期(约 90 天),到期前需在 Render 后台续期或升级付费,否则数据库会被删除。

## 答辩演示流程

1. 打开站点,用 `20230001 / 123456` 登录(或点「注册」新建账号)。
2. 首页演示卡片式列表、分页,以及按类型/分类/状态筛选 + 关键词搜索;顶部展示最新公告横幅(可关闭)。
3. 「发布帖子」:输入标题(如「文达楼112 白色耳机」),演示自动填充物品/地点;上传多张图片,自动压缩 + 缩略图。
4. 帖子详情:图片相册、状态标签、「可能匹配的招领/失物线索」智能推荐(带匹配度百分比)。
5. 在自己帖子上「标记为已找回/已归还」,演示状态流转;「我的帖子」里编辑/删图/追加图。
6. 「设置」里改通知邮箱、开启邮件通知,并演示「修改密码」(当前密码 + 新密码)。
7. 换 `20230002 / 123456` 登录,打开对方帖子「联系发布人」发私信;切回演示未读角标与聊天记录。
8. 演示「忘记密码」:学号 + 绑定邮箱申请重置链接并设新密码。
9. 用 `admin / admin123` 登录后台:筛选/编辑/批量操作帖子;数据看板;用户管理(封禁/重置/删除);发布公告;私信监管。

## 可继续优化的方向

- 帖子图片接对象存储(如 S3),避免免费平台临时磁盘重启丢图
- 接入真实短信通道(阿里云短信 / Twilio)
- 增加自动化测试(pytest)与 CSRF 保护
- 帖子举报与内容审核;多语言 / 移动端进一步适配
