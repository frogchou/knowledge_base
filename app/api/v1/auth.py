from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_db, get_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.models import User

router = APIRouter()


@router.post('/register')
async def register(username: str, password: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(username=username, password_hash=get_password_hash(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"success": True, "data": {"id": user.id, "username": user.username}}


@router.post('/login')
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    token = create_access_token({"sub": user.id})
    return {"success": True, "data": {"access_token": token, "token_type": "bearer"}}


@router.get('/me')
async def me(current_user: User = Depends(get_current_user)):
    return {"success": True, "data": {"id": current_user.id, "username": current_user.username}}
