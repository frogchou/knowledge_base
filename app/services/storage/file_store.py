import os
from pathlib import Path
from typing import Dict
from fastapi import UploadFile
from app.core.config import settings


Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)


def save_upload(file: UploadFile) -> Dict[str, str]:
    target = Path(settings.upload_dir) / file.filename
    with open(target, 'wb') as f:
        f.write(file.file.read())
    return {"path": str(target), "filename": file.filename, "mime": file.content_type or "application/octet-stream"}
