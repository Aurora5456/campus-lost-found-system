"""图片保存、压缩与缩略图生成。"""

import os
from uuid import uuid4

from PIL import Image, ImageOps
from werkzeug.utils import secure_filename

from config import Config


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    )


def _normalized_ext(filename):
    ext = filename.rsplit(".", 1)[1].lower()
    return "jpg" if ext == "jpeg" else ext


def save_image(file_storage):
    """保存单张图片，压缩原图并生成缩略图。

    返回 (image_path, thumb_path)，路径相对于 static 目录。
    若 file_storage 为空返回 (None, None)；格式非法抛出 ValueError。
    """
    if not file_storage or not file_storage.filename:
        return None, None
    if not allowed_file(file_storage.filename):
        raise ValueError("图片格式不正确，只允许 jpg、jpeg、png、gif。")

    secure_filename(file_storage.filename)  # 校验文件名安全性
    ext = _normalized_ext(file_storage.filename)
    base = uuid4().hex
    full_name = f"{base}.{ext}"
    thumb_name = f"{base}_thumb.{ext}"
    full_path = os.path.join(Config.UPLOAD_FOLDER, full_name)
    thumb_path = os.path.join(Config.UPLOAD_FOLDER, thumb_name)

    try:
        image = Image.open(file_storage.stream)
        image = ImageOps.exif_transpose(image)
    except Exception as exc:  # noqa: BLE001 - 任何解码失败都视为非法图片
        raise ValueError("图片无法识别，请更换图片后重试。") from exc

    save_kwargs = {}
    if ext in {"jpg", "jpeg"}:
        image = image.convert("RGB")
        save_kwargs = {"quality": 82, "optimize": True}
    elif ext == "gif":
        # 动图保持原始内容，仅做尺寸压缩可能丢帧，这里直接保存
        save_kwargs = {}

    full_image = image.copy()
    full_image.thumbnail(Config.IMAGE_MAX_SIZE)
    full_image.save(full_path, **save_kwargs)

    thumb_image = image.copy()
    thumb_image.thumbnail(Config.THUMB_MAX_SIZE)
    if ext == "gif":
        thumb_image = thumb_image.convert("RGB")
        thumb_image.save(thumb_path, format="JPEG", quality=82)
        thumb_name = f"{base}_thumb.jpg"
        thumb_path = os.path.join(Config.UPLOAD_FOLDER, thumb_name)
        thumb_image.save(thumb_path, format="JPEG", quality=82)
    else:
        thumb_image.save(thumb_path, **save_kwargs)

    return f"uploads/{full_name}", f"uploads/{thumb_name}"


def save_images(file_storages, limit=None):
    """批量保存图片，返回 [(image_path, thumb_path), ...]。"""
    limit = limit or Config.MAX_IMAGES_PER_POST
    saved = []
    for file_storage in file_storages:
        if not file_storage or not file_storage.filename:
            continue
        if len(saved) >= limit:
            break
        saved.append(save_image(file_storage))
    return saved


def remove_image_files(*relative_paths):
    """删除 static 下的图片文件，忽略不存在的文件。"""
    for relative_path in relative_paths:
        if not relative_path:
            continue
        absolute = os.path.join(Config.BASE_DIR, "static", *relative_path.split("/"))
        try:
            if os.path.isfile(absolute):
                os.remove(absolute)
        except OSError:
            pass
