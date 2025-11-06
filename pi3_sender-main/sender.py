#todo (Victor): pip install opencv-python requests
import os, sys, time, shutil
import requests
from pathlib import Path
from datetime import datetime

USE_CAMERA = os.getenv("USE_CAMERA", "1") == "1"
CAM_INDEX = int(os.getenv("CAM_INDEX", "0"))
FALLBACK_IMAGE = os.getenv("FALLBACK_IMAGE", "sample.jpg")
UPLOAD_URL = os.getenv("UPLOAD_URL", "http://localhost:8000/upload")
OUT_DIR = Path("out"); OUT_DIR.mkdir(exist_ok=True)

def capture_with_opencv():
    try:
        import cv2
    except Exception as e:
        print("[WARN] OpenCV nicht verfügbar:", e)
        return None, None
    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        print("[WARN] Kamera konnte nicht geöffnet werden.")
        return None, None
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("[WARN] Kein Frame erhalten.")
        return None, None
    # als JPEG speichern
    ts = datetime.now().strftime("%d%m%Y_%H-%M-%S")
    out_path = OUT_DIR / f"{ts}.jpg"
    cv2.imwrite(str(out_path), frame)
    return out_path, "image/jpeg"

capture_func = capture_with_opencv() if USE_CAMERA else None

def load_fallback():
    p = Path(FALLBACK_IMAGE)
    if not p.exists():
        # kleine Dummy-Datei erzeugen
        p.write_bytes(b"\xff\xd8\xff\xe0" + b"FAKEJPG")
    return p, "image/jpeg"

def send_image(path: Path, mime: str):
    files = {"file": (path.name, path.open("rb"), mime)}
    r = requests.post(UPLOAD_URL, files=files, timeout=15)
    print("Antwort:", r.status_code, r.text)

def main():

    img_path, mime = (capture_with_opencv() if USE_CAMERA else (None, None))
    if img_path is None:
        print("[INFO] Nutze Fallback-Datei statt Kamera.")
        img_path, mime = load_fallback()

    print(f"[INFO] sende {img_path} and {UPLOAD_URL}")
    send_image(img_path, mime)
    print("[INFO] Image sent.")
    shutil.rmtree(OUT_DIR);OUT_DIR.mkdir(exist_ok=True)
    print("[INFO] Cleaned up.")
    print("------- DONE --------")

if __name__ == "__main__":
    main()