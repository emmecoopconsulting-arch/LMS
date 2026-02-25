from pathlib import Path
import hashlib
import uuid
from fastapi import UploadFile, HTTPException
from app.core.config import get_settings

ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png"}
ALLOWED_EXT = {".pdf", ".jpg", ".jpeg", ".png"}


def store_upload(file: UploadFile) -> tuple[str, int, str]:
    settings = get_settings()
    content = file.file.read()
    size = len(content)
    if size > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    ext = Path(file.filename or "").suffix.lower()
    if file.content_type not in ALLOWED_MIME or ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    folder = Path(settings.upload_dir)
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    path = folder / filename
    path.write_bytes(content)

    checksum = hashlib.sha256(content).hexdigest()
    return str(path), size, checksum
