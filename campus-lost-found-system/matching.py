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


def _overlap(a, b):
    if not a or not b:
        return 0
    return len(a & b)


def score_match(source, candidate):
    score = 0
    if source.category and candidate.category and source.category == candidate.category:
        score += 3

    name_tokens_a = _tokens(source.item_name)
    name_tokens_b = _tokens(candidate.item_name)
    score += 2 * _overlap(name_tokens_a, name_tokens_b)

    loc_tokens_a = _tokens(source.location)
    loc_tokens_b = _tokens(candidate.location)
    score += 2 * _overlap(loc_tokens_a, loc_tokens_b)

    text_a = _tokens(f"{source.title} {source.description}")
    text_b = _tokens(f"{candidate.title} {candidate.description}")
    score += _overlap(text_a, text_b)
    return score


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
