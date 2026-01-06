import hashlib
from typing import List
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import KnowledgeItem, SourceType, User
from app.services.extractors.text_extractor import extract_text
from app.services.extractors.url_extractor import extract_from_url
from app.services.extractors.file_extractor import extract_from_file
from app.services.indexing.qdrant_store import QdrantStore
from app.llm.providers.base import get_provider
from app.services.storage.file_store import save_upload


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def enrich_and_save(db: AsyncSession, user: User, title: str, content_text: str, source_type: SourceType, tags: List[str] | None = None, source_url: str | None = None, file_meta: dict | None = None, existing: KnowledgeItem | None = None) -> KnowledgeItem:
    provider = get_provider()
    summary = provider.summarize(content_text)
    keywords = provider.extract_keywords(content_text)
    model_tags = provider.generate_tags(content_text)
    merged_tags = sorted(set((tags or []) + model_tags))
    embedding = provider.embed(content_text)

    item = existing or KnowledgeItem(owner_id=user.id)
    item.title = title
    item.source_type = source_type
    item.source_url = source_url
    item.content_text = content_text
    item.summary = summary
    item.keywords = keywords
    item.tags = merged_tags
    item.content_hash = compute_hash(content_text)

    if file_meta:
        item.original_filename = file_meta.get("filename")
        item.file_path = file_meta.get("path")
        item.mime_type = file_meta.get("mime")

    db.add(item)
    await db.commit()
    await db.refresh(item)

    store = QdrantStore()
    await store.upsert_item(item.id, embedding, {
        "title": item.title,
        "tags": item.tags,
        "keywords": item.keywords,
        "owner_id": item.owner_id,
        "created_at": item.created_at.isoformat(),
    })
    return item


async def ingest_text(db: AsyncSession, user: User, title: str, content_text: str, tags: List[str] | None = None, existing: KnowledgeItem | None = None) -> KnowledgeItem:
    return await enrich_and_save(db, user, title, content_text, SourceType.text, tags=tags, existing=existing)


async def ingest_url(db: AsyncSession, user: User, url: str, title: str | None, tags: List[str] | None = None, force: bool = False) -> KnowledgeItem:
    content_text, raw_html = extract_from_url(url)
    title = title or url
    if not force:
        existing = await db.execute(
            select(KnowledgeItem).where(KnowledgeItem.owner_id == user.id, KnowledgeItem.content_hash == compute_hash(content_text))
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="Duplicate content")
    return await enrich_and_save(db, user, title, content_text, SourceType.url, tags=tags, source_url=url)


async def ingest_file(db: AsyncSession, user: User, file: UploadFile, title: str | None, tags: List[str] | None = None, force: bool = False) -> KnowledgeItem:
    saved = save_upload(file)
    content_text = extract_from_file(saved["path"], saved["mime"])
    title = title or (file.filename or "uploaded file")
    if not force:
        existing = await db.execute(
            select(KnowledgeItem).where(KnowledgeItem.owner_id == user.id, KnowledgeItem.content_hash == compute_hash(content_text))
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="Duplicate content")
    return await enrich_and_save(db, user, title, content_text, SourceType.file, tags=tags, file_meta=saved)
