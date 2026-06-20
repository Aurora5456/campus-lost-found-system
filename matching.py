"""失物与招领的智能匹配。

给定一条帖子，在相反类型、仍未解决的帖子里按相似度打分，返回最可能匹配的若干条。
打分维度：分类是否一致、物品名称关键词重合、地点关键词重合、标题/描述关键词重合。
"""

import re

from constants import STATUS_OPEN
from models import Post

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+")
_STOPWORDS = {"的", "了", "在", "和", "我", "一个", "一只", "一张", "一部"}


def _tokens(text):
    if not text:
        return set()
    raw = _TOKEN_RE.findall(text)
    tokens = set()
    for word in raw:
        word = word.strip().lower()
        if len(word) >= 2 and word not in _STOPWORDS:
            tokens.add(word)
        # 中文按 2-gram 补充，便于“保温杯/水杯”等部分匹配
        if re.fullmatch(r"[\u4e00-\u9fff]+", word) and len(word) >= 2:
            for i in range(len(word) - 1):
                tokens.add(word[i : i + 2])
    return tokens


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


# 各维度权重（合计为 1），用于把相似度折算成 0-100% 的匹配度
_W_CATEGORY = 0.15
_W_ITEM = 0.40
_W_LOCATION = 0.25
_W_TEXT = 0.20


def score_match(source, candidate):
    """返回 0-100 的匹配度百分比（各维度相似度按权重相加）。"""
    category_sim = 1.0 if (
        source.category
        and candidate.category
        and source.category == candidate.category
    ) else 0.0

    item_sim = _jaccard(_tokens(source.item_name), _tokens(candidate.item_name))
    loc_sim = _jaccard(_tokens(source.location), _tokens(candidate.location))
    text_sim = _jaccard(
        _tokens(f"{source.title} {source.description}"),
        _tokens(f"{candidate.title} {candidate.description}"),
    )

    raw = (
        _W_CATEGORY * category_sim
        + _W_ITEM * item_sim
        + _W_LOCATION * loc_sim
        + _W_TEXT * text_sim
    )
    percent = round(raw * 100)
    # 有任意正向重合但四舍五入为 0 时，至少显示 1%
    if percent == 0 and raw > 0:
        percent = 1
    return percent


def find_matches(post, limit=5):
    """返回 [(candidate_post, score), ...]，按分数降序，已过滤 0 分。"""
    opposite = "found" if post.post_type == "lost" else "lost"
    candidates = (
        Post.query.filter(
            Post.post_type == opposite,
            Post.status == STATUS_OPEN,
            Post.id != post.id,
        )
        .order_by(Post.created_at.desc())
        .limit(200)
        .all()
    )
    scored = [(c, score_match(post, c)) for c in candidates]
    scored = [item for item in scored if item[1] > 0]
    scored.sort(key=lambda item: (item[1], item[0].created_at), reverse=True)
    return scored[:limit]
