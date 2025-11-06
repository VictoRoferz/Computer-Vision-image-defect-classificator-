from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import hashlib, os, shutil
from pathlib import Path
import threading
from labelstudio_integration import start_watcher

IMAGES_ROOT = Path(os.getenv("IMAGES_ROOT", "/data/images"))
IMAGES_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI()

def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def shard_path(root: Path, sha256_hex: str, filename: str) -> Path:
    # content-addressed Pfad: /data/images/ab/cd/<sha...>/raw.jpg
    sub1, sub2 = sha256_hex[:2], sha256_hex[2:4]
    return root / sub1 / sub2 / sha256_hex / filename

@app.on_event("startup")
def startup_event():
    threading.Thread(target=start_watcher, daemon=True).start()
@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    # nur einfache Prüfung der Endung
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".bmp"]:
        ext = ".jpg"  # notfalls standardisieren

    # Temporär speichern
    tmp = IMAGES_ROOT / "__incoming__"
    tmp.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp / file.filename if file.filename else tmp / "upload.bin"
    with tmp_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    # Hash berechnen & an Ziel verschieben (idempotent)
    digest = sha256_of_file(tmp_path)
    dst = shard_path(IMAGES_ROOT, digest, file.filename or f"upload{ext}")
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists():
        tmp_path.unlink(missing_ok=True)
        return JSONResponse({"status": "already_stored", "sha256": digest, "path": str(dst)}, status_code=200)

    # atomarer Move
    tmp_path.replace(dst)
    return {"status": "stored", "sha256": digest, "path": str(dst)}
