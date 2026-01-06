from pathlib import Path
from typing import Dict
from fastapi import UploadFile
import hashlib

from app.core.config import settings


Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)


def save_upload(file: UploadFile) -> Dict[str, str]:
    target = Path(settings.upload_dir) / file.filename
    with open(target, 'wb') as f:
        f.write(file.file.read())
    return {"path": str(target), "filename": file.filename, "mime": file.content_type or "application/octet-stream"}


def save_html(content: str) -> Dict[str, str]:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    target_dir = Path(settings.upload_dir) / "html"
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"url_{digest}.html"
    target = target_dir / filename
    with open(target, 'w', encoding='utf-8') as f:
        f.write(content)
    return {"path": str(target), "filename": filename, "mime": "text/html"}
