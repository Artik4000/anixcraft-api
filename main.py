"""
ANIXCRAFT Skin API v7.0.0 — прямой HTTP к Supabase
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
import os
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

BUCKET = "skins"
VALID_SIZE = 1024
MAX_SIZE = 1024 * 1024

app = FastAPI(title="ANIXCRAFT Skin API", version="7.0.0")


def _headers(content_type=None):
    h = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
    }
    if content_type:
        h["Content-Type"] = content_type
    return h


@app.get("/")
def root():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {
            "status": "ok", "api": "ANIXCRAFT Skin API", "version": "7.0.0",
            "storage": "NOT CONFIGURED", "skins_count": 0, "skins": [],
        }
    skins = []
    try:
        url = f"{SUPABASE_URL}/storage/v1/object/list/{BUCKET}"
        r = requests.post(
            url,
            headers=_headers("application/json"),
            json={"prefix": "", "limit": 100},
            timeout=10,
        )
        if r.status_code == 200:
            for item in r.json():
                name = item.get("name", "")
                if name.endswith(".png"):
                    skins.append(name[:-4])
    except Exception as e:
        print(f"list error: {type(e).__name__}: {e}")

    return {
        "status": "ok",
        "api": "ANIXCRAFT Skin API",
        "version": "7.0.0",
        "storage": "Supabase Storage",
        "skins_count": len(skins),
        "skins": skins[:50],
    }


@app.post("/skin/{username}")
async def upload_skin(username: str, file: UploadFile = File(...)):
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(500, "Supabase не настроен")

    username = username.strip()
    if not username or len(username) > 32:
        raise HTTPException(400, "Неверный ник")

    content = await file.read()
    if len(content) < VALID_SIZE:
        raise HTTPException(400, "Маленький файл")
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "Большой файл")
    if not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(400, "Не PNG")

    target_name = f"{username}.png"

    # Удалить старый (игнорируем ошибку, если нет)
    try:
        requests.delete(
            f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{target_name}",
            headers=_headers(),
            timeout=10,
        )
    except Exception:
        pass

    # Загрузить новый
    try:
        r = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{target_name}",
            headers=_headers("image/png"),
            data=content,
            timeout=15,
        )
        if r.status_code not in (200, 201):
            raise Exception(f"{r.status_code}: {r.text[:200]}")
    except Exception as e:
        raise HTTPException(500, f"Ошибка загрузки: {type(e).__name__}: {e}")

    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{target_name}"
    return {
        "status": "ok",
        "username": username,
        "size": len(content),
        "url": f"/skin/{username}",
        "public_url": public_url,
    }


@app.get("/skin/{username}")
async def get_skin(username: str):
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(500, "Supabase не настроен")

    username = username.strip()
    try:
        r = requests.get(
            f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{username}.png",
            headers=_headers(),
            timeout=10,
        )
        if r.status_code != 200:
            raise Exception()
    except Exception:
        raise HTTPException(404, f"Не найден: {username}")
    return Response(content=r.content, media_type="image/png")


@app.delete("/skin/{username}")
async def delete_skin(username: str):
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(500, "Supabase не настроен")
    try:
        requests.delete(
            f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{username}.png",
            headers=_headers(),
            timeout=10,
        )
    except Exception:
        raise HTTPException(404, "Не найден")
    return {"status": "ok", "deleted": username}
