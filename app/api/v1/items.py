import hashlib
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.db.models import KnowledgeItem, SourceType, User
from app.services.ingest.pipeline import ingest_text, ingest_url, ingest_file

router = APIRouter()


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@router.post("/text")
async def create_text_item(title: str = Form(...), content_text: str = Form(...), tags: str | None = Form(None), force: bool = Form(False), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    tags_list = [t.strip() for t in tags.split(',')] if tags else []
    existing = await db.execute(select(KnowledgeItem).where(KnowledgeItem.owner_id == current_user.id, KnowledgeItem.content_hash == compute_hash(content_text)))
    if existing.scalars().first() and not force:
        raise HTTPException(status_code=400, detail="Duplicate content")
    item = await ingest_text(db, current_user, title, content_text, tags_list)
    return {"success": True, "data": {"id": item.id}}


@router.post("/url")
async def create_url_item(url: str = Form(...), title: str | None = Form(None), tags: str | None = Form(None), force: bool = Form(False), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    tags_list = [t.strip() for t in tags.split(',')] if tags else []
    item = await ingest_url(db, current_user, url, title, tags_list, force=force)
    return {"success": True, "data": {"id": item.id}}


@router.post("/file")
async def create_file_item(file: UploadFile = File(...), title: str | None = Form(None), tags: str | None = Form(None), force: bool = Form(False), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    tags_list = [t.strip() for t in tags.split(',')] if tags else []
    item = await ingest_file(db, current_user, file, title, tags_list, force=force)
    return {"success": True, "data": {"id": item.id}}


@router.get("")
async def list_items(db: AsyncSession = Depends(get_db), current_user: User | None = Depends(get_current_user)):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.is_deleted == False).order_by(KnowledgeItem.created_at.desc()))
    items = result.scalars().all()
    return {"success": True, "data": [
        {
            "id": item.id,
            "title": item.title,
            "tags": item.tags,
            "summary": item.summary,
            "created_at": item.created_at,
        }
        for item in items
    ]}


@router.get("/{item_id}")
async def get_item(item_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id, KnowledgeItem.is_deleted == False))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return {"success": True, "data": {
        "id": item.id,
        "title": item.title,
        "summary": item.summary,
        "keywords": item.keywords,
        "tags": item.tags,
        "content_text": item.content_text,
        "source_type": item.source_type.value,
        "source_url": item.source_url,
    }}


@router.put("/{item_id}")
async def update_item(item_id: str, title: str | None = Form(None), summary: str | None = Form(None), keywords: str | None = Form(None), tags: str | None = Form(None), content_text: str | None = Form(None), reindex: bool = Form(False), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id, KnowledgeItem.owner_id == current_user.id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    if title:
        item.title = title
    if summary:
        item.summary = summary
    if keywords is not None:
        item.keywords = [k.strip() for k in keywords.split(',') if k.strip()]
    if tags is not None:
        item.tags = [t.strip() for t in tags.split(',') if t.strip()]
    if content_text:
        item.content_text = content_text
    await db.commit()
    await db.refresh(item)
    if reindex:
        await ingest_text(db, current_user, item.title, item.content_text, item.tags, existing=item)
    return {"success": True, "data": {"id": item.id}}


@router.delete("/{item_id}")
async def delete_item(item_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id, KnowledgeItem.owner_id == current_user.id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)
    await db.commit()
    return {"success": True}
