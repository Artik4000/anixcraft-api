"""
ANIXCRAFT Skin API v2.2.0
"""
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"Supabase OK: {SUPABASE_URL}")

BUCKET = "skins"
VALID_SIZE = 1024
MAX_SIZE = 1024 * 1024

app = FastAPI(title="ANIXCRAFT Skin API", version="2.2.0")


@app.get("/")
def root():
    skins = []
    if supabase:
        try:
            files = supabase.storage.from_(BUCKET).list()
            skins = [f["name"].replace(".png", "") for f in files if f["name"].endswith(".png")]
        except Exception as e:
            print(f"list error: {e}")
    return {
        "status": "ok",
        "api": "ANIXCRAFT Skin API",
        "version": "2.2.0",
        "storage": "Supabase Storage" if supabase else "NOT CONFIGURED",
        "skins_count": len(skins),
        "skins": skins[:50],
    }


@app.post("/skin/{username}")
async def upload_skin(username: str, file: UploadFile = File(...)):
    if not supabase:
        raise HTTPException(500, "Supabase not configured")
    username = username.strip()
    if not username or len(username) > 32:
        raise HTTPException(400, "Bad username")
    for ch in username:
        if not (ch.isalnum() or ch == "_"):
            raise HTTPException(400, "Bad username chars")

    content = await file.read()
    if len(content) < VALID_SIZE:
        raise HTTPException(400, "Too small")
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "Too big")
    if not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(400, "Not PNG")

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
        raise HTTPException(500, f"upload error: {type(e).__name__}: {e}")

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
        raise HTTPException(500, "Supabase not configured")
    username = username.strip()
    target_name = f"{username}.png"
    try:
        content = supabase.storage.from_(BUCKET).download(target_name)
    except Exception:
        raise HTTPException(404, f"Not found: {username}")
    return Response(content=content, media_type="image/png")


@app.delete("/skin/{username}")
async def delete_skin(username: str):
    if not supabase:
        raise HTTPException(500, "Supabase not configured")
    username = username.strip()
    target_name = f"{username}.png"
    try:
        supabase.storage.from_(BUCKET).remove([target_name])
    except Exception:
        raise HTTPException(404, "Not found")
    return {"status": "ok", "deleted": username}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)