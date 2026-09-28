"""
ANIXCRAFT Skin API
Принимает скины от лаунчера, отдаёт их SkinRestorer.
"""

import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

app = FastAPI(title="ANIXCRAFT Skin API", version="1.0.0")

API_DIR = Path(__file__).parent.resolve()
SKINS_DIR = API_DIR / "skins"
SKINS_DIR.mkdir(exist_ok=True)

VALID_SIZE = 1024  # минимальный размер PNG (1 КБ)


@app.get("/")
def root():
    """Тестовая страница."""
    skins = [f.stem for f in SKINS_DIR.glob("*.png")]
    return {
        "status": "ok",
        "api": "ANIXCRAFT Skin API",
        "version": "1.0.0",
        "skins_count": len(skins),
        "skins": skins[:50],
    }


@app.post("/skin/{username}")
async def upload_skin(username: str, file: UploadFile = File(...)):
    """Принимает PNG от лаунчера, сохраняет."""
    # Очищаем ник
    username = username.strip()
    if not username or len(username) > 32:
        raise HTTPException(400, "Неверный никнейм")
    for ch in username:
        if not (ch.isalnum() or ch == "_"):
            raise HTTPException(400, "Никнейм может содержать только буквы, цифры и _")

    # Проверяем размер
    content = await file.read()
    if len(content) < VALID_SIZE:
        raise HTTPException(400, "Файл слишком маленький (не PNG 64×64)")
    if len(content) > 1024 * 1024:  # 1 MB
        raise HTTPException(400, "Файл слишком большой")

    # Проверяем PNG-сигнатуру
    if not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(400, "Файл не является PNG")

    target = SKINS_DIR / f"{username}.png"
    target.write_bytes(content)

    return {
        "status": "ok",
        "username": username,
        "size": len(content),
        "url": f"/skin/{username}",
    }


@app.get("/skin/{username}")
async def get_skin(username: str):
    """Отдаёт PNG с правильным Content-Type."""
    username = username.strip()
    target = SKINS_DIR / f"{username}.png"

    if not target.exists():
        raise HTTPException(404, f"Скин не найден: {username}")

    return FileResponse(
        target,
        media_type="image/png",
        filename=f"{username}.png",
    )


@app.delete("/skin/{username}")
async def delete_skin(username: str):
    """Удаляет скин (для админа)."""
    username = username.strip()
    target = SKINS_DIR / f"{username}.png"

    if not target.exists():
        raise HTTPException(404, "Скин не найден")

    target.unlink()
    return {"status": "ok", "deleted": username}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)