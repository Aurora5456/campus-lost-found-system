"""集中管理帖子分类、状态等可选项，供模型、表单和模板复用。"""

CATEGORIES = [
    ("card", "证件卡片"),
    ("electronics", "电子产品"),
    ("key", "钥匙"),
    ("book", "书籍资料"),
    ("clothing", "衣物饰品"),
    ("wallet", "钱包现金"),
    ("daily", "生活用品"),
    ("other", "其他"),
]

CATEGORY_KEYS = {key for key, _ in CATEGORIES}
CATEGORY_LABELS = dict(CATEGORIES)

# 帖子处理状态
STATUS_OPEN = "open"
STATUS_RESOLVED = "resolved"
STATUS_KEYS = {STATUS_OPEN, STATUS_RESOLVED}

# 不同类型帖子在不同状态下展示的中文标签
STATUS_LABELS = {
    ("lost", STATUS_OPEN): "寻找中",
    ("lost", STATUS_RESOLVED): "已找回",
    ("found", STATUS_OPEN): "招领中",
    ("found", STATUS_RESOLVED): "已归还",
}


def category_label(key):
    return CATEGORY_LABELS.get(key, "其他")


def status_label(post_type, status):
    return STATUS_LABELS.get((post_type, status), "寻找中")
