from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_db, get_current_user, get_optional_user
from app.core.security import create_access_token, verify_password
from app.db.models import KnowledgeItem, User

ui_router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@ui_router.get('/login')
async def login_page(request: Request):
    return templates.TemplateResponse('login.html', {"request": request, "error": None})


@ui_router.post('/login')
async def login_action(request: Request, username: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse('login.html', {"request": request, "error": "Invalid credentials"})
    token = create_access_token({"sub": user.id})
    response = RedirectResponse(url="/ui/items", status_code=302)
    response.set_cookie("access_token", token, httponly=True)
    return response


@ui_router.get('/items')
async def items_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.is_deleted == False).order_by(KnowledgeItem.created_at.desc()))
    items = result.scalars().all()
    return templates.TemplateResponse('items.html', {"request": request, "items": items})


@ui_router.get('/items/{item_id}')
async def item_detail(item_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return templates.TemplateResponse('item_detail.html', {"request": request, "item": item})


@ui_router.get('/items/{item_id}/edit')
async def item_edit(item_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return templates.TemplateResponse('item_edit.html', {"request": request, "item": item})


@ui_router.post('/items/{item_id}/delete')
async def item_delete(item_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id))
    item = result.scalars().first()
    if item:
        await db.delete(item)
        await db.commit()
    return RedirectResponse(url="/ui/items", status_code=302)
