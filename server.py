"""
ANIXCRAFT Skin API v2.0
Принимает скины от лаунчера, хранит в Supabase Storage.
"""

import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from supabase import create_client, Client

# ============ SUPABASE ============
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️  ВНИМАНИЕ: SUPABASE_URL или SUPABASE_KEY не заданы!")
    print("Без них API не сможет сохранять скины.")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"✅ Supabase подключён: {SUPABASE_URL}")

BUCKET = "skins"
# ====================================

app = FastAPI(title="ANIXCRAFT Skin API", version="2.0.0")

VALID_SIZE = 1024  # минимум 1 КБ (реальный PNG 64×64 = 1-3 КБ)
MAX_SIZE = 1024 * 1024  # максимум 1 МБ


@app.get("/")
def root():
    """Тестовая страница."""
    skins = []
    if supabase:
        try:
            files = supabase.storage.from_(BUCKET).list()
            skins = [f["name"].replace(".png", "") for f in files if f["name"].endswith(".png")]
        except Exception as e:
            print(f"Ошибка чтения списка: {e}")

    return {
        "status": "ok",
        "api": "ANIXCRAFT Skin API",
        "version": "2.0.0",
        "storage": "Supabase Storage" if supabase else "NOT CONFIGURED",
        "skins_count": len(skins),
        "skins": skins[:50],
    }


@app.post("/skin/{username}")
async def upload_skin(username: str, file: UploadFile = File(...)):
    """Принимает PNG, загружает в Supabase Storage."""
    if not supabase:
        raise HTTPException(500, "Supabase не настроен")

    username = username.strip()
    if not username or len(username) > 32:
        raise HTTPException(400, "Неверный никнейм")
    for ch in username:
        if not (ch.isalnum() or ch == "_"):
            raise HTTPException(400, "Никнейм: только буквы, цифры и _")

    content = await file.read()
    if len(content) < VALID_SIZE:
        raise HTTPException(400, "Файл слишком маленький (не PNG 64×64)")
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "Файл слишком большой (макс 1 МБ)")

    if not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(400, "Файл не является PNG")

    target_name = f"{username}.png"

    # Удаляем старый скин (если есть) — чтобы перезаписать
    try:
        supabase.storage.from_(BUCKET).remove([target_name])
    except Exception:
        pass

    # Загружаем новый
    try:
        supabase.storage.from_(BUCKET).upload(
            path=target_name,
            file=content,
            file_options={"content-type": "image/png"},
        )
    except Exception as e:
        raise HTTPException(500, f"Ошибка загрузки: {e}")

    # Публичный URL
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
    """Отдаёт PNG из Supabase Storage."""
    if not supabase:
        raise HTTPException(500, "Supabase не настроен")

    username = username.strip()
    target_name = f"{username}.png"

    try:
        content = supabase.storage.from_(BUCKET).download(target_name)
    except Exception as e:
        raise HTTPException(404, f"Скин не найден: {username} ({e})")

    return Response(content=content, media_type="image/png")


@app.delete("/skin/{username}")
async def delete_skin(username: str):
    """Удаляет скин из Supabase."""
    if not supabase:
        raise HTTPException(500, "Supabase не настроен")

    username = username.strip()
    target_name = f"{username}.png"

    try:
        supabase.storage.from_(BUCKET).remove([target_name])
    except Exception as e:
        raise HTTPException(404, f"Скин не найден: {e}")

    return {"status": "ok", "deleted": username}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
