from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib
from itsdangerous import URLSafeSerializer, BadSignature
from urllib.parse import urlparse, urlencode

from app.core.dependencies import get_db
from app.core.security import create_access_token, verify_password, decode_access_token
from app.core.config import settings
from app.db.models import KnowledgeItem, User
from app.services.ingest.pipeline import ingest_text, ingest_url, ingest_file
from app.ui.i18n import LANG_COOKIE, SUPPORTED_LANGS, normalize_lang, get_translator

ui_router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
_ui_serializer = URLSafeSerializer(settings.jwt_secret, salt="ui-session")

def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _parse_tags(tags: str | None) -> list[str]:
    return [t.strip() for t in tags.split(',') if t.strip()] if tags else []


def _parse_force(force: str | None) -> bool:
    return (force or "").lower() in {"1", "true", "on", "yes"}


def _resolve_lang(request: Request) -> str:
    query_lang = request.query_params.get("lang")
    cookie_lang = request.cookies.get(LANG_COOKIE)
    return normalize_lang(query_lang or cookie_lang)


def _current_path(request: Request) -> str:
    params = dict(request.query_params)
    params.pop("lang", None)
    if params:
        return f"{request.url.path}?{urlencode(params)}"
    return request.url.path


def _lang_switch(lang: str) -> tuple[str, str]:
    if lang == "zh":
        return "en", "English"
    return "zh", "中文"


def _set_lang_cookie(response: Response, lang: str) -> None:
    response.set_cookie(LANG_COOKIE, lang, httponly=False, samesite="lax", path="/")


def _template_response(request: Request, template_name: str, context: dict, lang: str | None = None):
    lang = normalize_lang(lang or _resolve_lang(request))
    switch_to, switch_label = _lang_switch(lang)
    base_context = {
        "request": request,
        "t": get_translator(lang),
        "lang": lang,
        "lang_switch_to": switch_to,
        "lang_switch_label": switch_label,
        "lang_next": _current_path(request),
    }
    base_context.update(context)
    response = templates.TemplateResponse(template_name, base_context)
    query_lang = request.query_params.get("lang")
    if query_lang in SUPPORTED_LANGS:
        _set_lang_cookie(response, lang)
    return response


async def _get_ui_user(request: Request, db: AsyncSession) -> User | None:
    session_token = request.cookies.get("ui_session")
    if session_token:
        try:
            data = _ui_serializer.loads(session_token)
            user_id = data.get("user_id")
            if user_id is not None:
                result = await db.execute(select(User).where(User.id == int(user_id)))
                return result.scalars().first()
        except (BadSignature, ValueError, TypeError):
            pass
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_access_token(token.strip())
    if not payload or "sub" not in payload:
        return None
    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


def _safe_next(path: str | None) -> str:
    if not path:
        return "/ui/items"
    parsed = urlparse(path)
    if parsed.scheme or parsed.netloc:
        return "/ui/items"
    if not path.startswith("/"):
        return "/ui/items"
    return path


def _set_session_cookie(response: RedirectResponse, user_id: int) -> None:
    token = _ui_serializer.dumps({"user_id": user_id})
    response.set_cookie("ui_session", token, httponly=True, samesite="lax", path="/")


def _translate_error(detail: str, lang: str) -> str:
    mapping = {
        "Duplicate content": "error_duplicate",
        "Only PDF or DOCX files are supported": "error_file_type",
    }
    key = mapping.get(detail)
    if not key:
        return detail
    return get_translator(lang)(key)


@ui_router.get('/login')
async def login_page(request: Request):
    next_path = _safe_next(request.query_params.get("next"))
    return _template_response(request, "login.html", {"error": None, "next": next_path})


@ui_router.post('/login')
async def login_action(request: Request, db: AsyncSession = Depends(get_db)):
    username = None
    password = None
    form_lang = None
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            data = await request.json()
            username = data.get("username")
            password = data.get("password")
            form_lang = data.get("lang")
        except Exception:
            pass
    if username is None or password is None:
        try:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
            form_lang = form.get("lang")
        except Exception:
            pass
    lang = normalize_lang(form_lang or _resolve_lang(request))
    next_path = None
    try:
        next_path = (await request.form()).get("next")
    except Exception:
        next_path = request.query_params.get("next")
    next_path = _safe_next(next_path)
    if not username or not password:
        response = _template_response(
            request,
            "login.html",
            {
                "error": get_translator(lang)("error_missing_credentials"),
                "next": next_path,
                "lang_next": f"/ui/login?next={next_path}",
            },
            lang=lang,
        )
        _set_lang_cookie(response, lang)
        return response
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user or not verify_password(password, user.password_hash):
        response = _template_response(
            request,
            "login.html",
            {
                "error": get_translator(lang)("error_invalid_credentials"),
                "next": next_path,
                "lang_next": f"/ui/login?next={next_path}",
            },
            lang=lang,
        )
        _set_lang_cookie(response, lang)
        return response
    token = create_access_token({"sub": user.id})
    response = RedirectResponse(url=next_path or "/ui/items", status_code=302)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", path="/")
    _set_session_cookie(response, user.id)
    _set_lang_cookie(response, lang)
    return response


@ui_router.get('/items')
async def items_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.is_deleted == False).order_by(KnowledgeItem.created_at.desc()))
    items = result.scalars().all()
    return _template_response(request, "items.html", {"items": items})


@ui_router.get('/lang')
async def switch_language(request: Request):
    lang = normalize_lang(request.query_params.get("lang"))
    next_path = _safe_next(request.query_params.get("next"))
    response = RedirectResponse(url=next_path, status_code=302)
    _set_lang_cookie(response, lang)
    return response


@ui_router.get('/ingest')
async def ingest_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _get_ui_user(request, db)
    if not user:
        lang = _resolve_lang(request)
        return RedirectResponse(url=f"/ui/login?next=/ui/ingest&lang={lang}", status_code=302)
    return _template_response(request, "ingest.html", {"error": None, "next": "/ui/ingest"})


@ui_router.post('/ingest/text')
async def ingest_text_action(
    request: Request,
    title: str = Form(...),
    content_text: str = Form(...),
    tags: str | None = Form(None),
    force: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_ui_user(request, db)
    if not user:
        lang = _resolve_lang(request)
        return RedirectResponse(url=f"/ui/login?next=/ui/ingest&lang={lang}", status_code=302)
    if not _parse_force(force):
        existing = await db.execute(
            select(KnowledgeItem).where(
                KnowledgeItem.owner_id == user.id,
                KnowledgeItem.content_hash == _compute_hash(content_text),
            )
        )
        if existing.scalars().first():
            lang = _resolve_lang(request)
            return _template_response(request, "ingest.html", {"error": get_translator(lang)("error_duplicate")}, lang=lang)
    try:
        item = await ingest_text(db, user, title, content_text, _parse_tags(tags))
    except Exception as exc:
        lang = _resolve_lang(request)
        return _template_response(request, "ingest.html", {"error": str(exc)}, lang=lang)
    return RedirectResponse(url=f"/ui/items/{item.id}", status_code=302)


@ui_router.post('/ingest/url')
async def ingest_url_action(
    request: Request,
    url: str = Form(...),
    title: str | None = Form(None),
    tags: str | None = Form(None),
    force: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_ui_user(request, db)
    if not user:
        lang = _resolve_lang(request)
        return RedirectResponse(url=f"/ui/login?next=/ui/ingest&lang={lang}", status_code=302)
    try:
        item = await ingest_url(db, user, url, title, _parse_tags(tags), force=_parse_force(force))
    except HTTPException as exc:
        lang = _resolve_lang(request)
        return _template_response(request, "ingest.html", {"error": _translate_error(str(exc.detail), lang)}, lang=lang)
    except Exception as exc:
        lang = _resolve_lang(request)
        return _template_response(request, "ingest.html", {"error": str(exc)}, lang=lang)
    return RedirectResponse(url=f"/ui/items/{item.id}", status_code=302)


@ui_router.post('/ingest/file')
async def ingest_file_action(
    request: Request,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    tags: str | None = Form(None),
    force: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_ui_user(request, db)
    if not user:
        lang = _resolve_lang(request)
        return RedirectResponse(url=f"/ui/login?next=/ui/ingest&lang={lang}", status_code=302)
    filename = (file.filename or "").lower()
    if not (filename.endswith(".pdf") or filename.endswith(".docx")):
        lang = _resolve_lang(request)
        return _template_response(request, "ingest.html", {"error": get_translator(lang)("error_file_type")}, lang=lang)
    try:
        item = await ingest_file(db, user, file, title, _parse_tags(tags), force=_parse_force(force))
    except HTTPException as exc:
        lang = _resolve_lang(request)
        return _template_response(request, "ingest.html", {"error": _translate_error(str(exc.detail), lang)}, lang=lang)
    except Exception as exc:
        lang = _resolve_lang(request)
        return _template_response(request, "ingest.html", {"error": str(exc)}, lang=lang)
    return RedirectResponse(url=f"/ui/items/{item.id}", status_code=302)


@ui_router.get('/items/{item_id}')
async def item_detail(item_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return _template_response(request, "item_detail.html", {"item": item})


@ui_router.get('/items/{item_id}/edit')
async def item_edit(item_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return _template_response(request, "item_edit.html", {"item": item})


@ui_router.post('/items/{item_id}/delete')
async def item_delete(item_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id))
    item = result.scalars().first()
    if item:
        await db.delete(item)
        await db.commit()
    return RedirectResponse(url="/ui/items", status_code=302)
