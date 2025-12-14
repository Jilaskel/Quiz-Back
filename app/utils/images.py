import hashlib
import datetime
from typing import Optional, Tuple
import filetype

ALLOWED_MIME = {"image/jpeg","image/png","image/webp","image/avif"}

def read_and_validate(file_bytes: bytes, *, max_mb: int) -> Tuple[str, str, int, str]:
    """
    Retourne (real_mime, ext_with_dot, size_bytes, sha256).
    Lève ValueError si invalide.
    """
    size = len(file_bytes)
    if size == 0 or size > max_mb * 1024 * 1024:
        raise ValueError(f"Taille invalide (max {max_mb} MB)")
    kind = filetype.guess(file_bytes)
    real_mime = kind.mime if kind else "application/octet-stream"
    if real_mime not in ALLOWED_MIME:
        raise ValueError(f"Type non autorisé: {real_mime}")
    ext = "." + (kind.extension if kind else "bin")
    sha = hashlib.sha256(file_bytes).hexdigest()
    return real_mime, ext, size, sha

def build_object_key(owner_id: Optional[int], ext: str) -> str:
    today = datetime.date.today().isoformat()
    from uuid import uuid4
    return f"users/{owner_id or 'anonymous'}/{today}/{uuid4().hex}{ext}"
