"""Card photo files on disk: what may be uploaded, and removing files when their photos go away.

Photo rows disappear with their collection entry (database cascade), but the files do not, so every
path that deletes entries or photos collects the file paths first and calls remove_files() once the
database change is committed.
"""
import logging
import os

from sqlalchemy.orm import Session

import models

logger = logging.getLogger(__name__)

SUPPORTED_TYPES = "JPEG, PNG or WebP"


def photos_dir() -> str:
    return os.path.realpath(os.path.join(os.environ.get("UPLOADS_PATH", "/data/uploads"), "card_photos"))


def image_extension(head: bytes) -> str | None:
    """The file extension for a JPEG, PNG or WebP image judged by its first bytes, else None.
    The uploaded file name and content type are not trusted."""
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return None


def entry_photo_paths(entry: models.CollectionEntry) -> list[str]:
    return [photo.file_path for photo in entry.photos]


def user_photo_paths(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(models.CardPhoto.file_path)
        .join(models.CollectionEntry, models.CardPhoto.collection_entry_id == models.CollectionEntry.id)
        .filter(models.CollectionEntry.user_id == user_id)
        .all()
    )
    return [path for (path,) in rows]


def remove_files(paths) -> None:
    """Delete photo files; call only after the database change is committed.

    Never touches anything outside the photo directory, ignores files that are already gone, and
    logs instead of raising: a leftover file must not fail the request that removed its photo."""
    base = photos_dir()
    for path in paths:
        real = os.path.realpath(path)
        if not real.startswith(base + os.sep):
            logger.warning("Not deleting photo file outside %s: %s", base, path)
            continue
        try:
            os.remove(real)
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.warning("Could not delete photo file %s: %s", path, exc)
