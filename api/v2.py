"""
ANIXCRAFT Skin API v4.0.0
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from supabase import create_client, Client
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BUCKET = "skins"
VALID_SIZE = 1024
MAX_SIZE = 1024 * 1024

app = FastAPI(title="ANIXCRAFT Skin API", version="4.0.0")


@app.get("/")
def root():
    skins = []
    if supabase:
        try:
            files = supabase.storage.from_(BUCKET).list()
            skins = [f["name"].replace(".png", "") for f in files if f["name"].endswith(".png")]
        except Exception:
            pass
    return {
        "status": "ok",
        "api": "ANIXCRAFT Skin API",
        "version": "4.0.0",
        "storage": "Supabase Storage" if supabase else "NOT CONFIGURED",
        "skins_count": len(skins),
        "skins": skins[:50],
    }


@app.post("/set-skin/{username}")
async def save_skin_v2(username: str, file: UploadFile = File(...)):
    if not supabase:
        raise HTTPException(500, "Supabase не настроен")
    username = username.strip()
    if not username or len(username) > 32:
        raise HTTPException(400, "Неверный никнейм")
    content = await file.read()
    if len(content) < VALID_SIZE:
        raise HTTPException(400, "Маленький файл")
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "Большой файл")
    if not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(400, "Не PNG")
    target_name = f"{username}.png"

    try:
        supabase.storage.from_(BUCKET).remove([target_name])
    except Exception:
        pass

    try:
        result = supabase.storage.from_(BUCKET).upload(
            path=target_name,
            file=content,
            file_options={"content-type": "image/png"},
        )
        if hasattr(result, "error") and result.error:
            raise Exception(str(result.error))
    except Exception as e:
        raise HTTPException(500, f"Ошибка: {type(e).__name__}: {e}")

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
    if not supabase:
        raise HTTPException(500, "Supabase не настроен")
    username = username.strip()
    try:
        content = supabase.storage.from_(BUCKET).download(f"{username}.png")
    except Exception:
        raise HTTPException(404, f"Не найден: {username}")
    return Response(content=content, media_type="image/png")


@app.delete("/skin/{username}")
async def delete_skin(username: str):
    if not supabase:
        raise HTTPException(500, "Supabase не настроен")
    try:
        supabase.storage.from_(BUCKET).remove([f"{username}.png"])
    except Exception:
        raise HTTPException(404, "Не найден")
    return {"status": "ok", "deleted": username}
