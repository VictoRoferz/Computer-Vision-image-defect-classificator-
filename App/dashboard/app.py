"""
Dashboard Web UI for PCB Defect Classification System.
Provides a single-page interface for both Label and Inference workflows.
"""
import io
import os
import requests
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Service URLs (internal Docker network)
SERVER1_URL = os.getenv("SERVER1_URL", "http://pcb-server1-camera:8001")
SERVER2_URL = os.getenv("SERVER2_URL", "http://pcb-server2-labelstudio:8002")
INFERENCE_URL = os.getenv("INFERENCE_URL", "http://pcb-inference:8003")
LABELSTUDIO_URL = os.getenv("LABELSTUDIO_URL", "http://labelstudio:8080")

# External URLs (for links the browser follows)
LABELSTUDIO_EXTERNAL_URL = os.getenv("LABELSTUDIO_EXTERNAL_URL", "http://localhost:8080")

app = FastAPI(title="PCB Dashboard", docs_url="/api/docs")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main dashboard page."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "labelstudio_url": LABELSTUDIO_EXTERNAL_URL,
    })


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "dashboard"}


# ── Proxy endpoints (browser → dashboard → internal services) ──


@app.get("/api/services/status")
async def services_status():
    """Aggregate health from all services."""
    statuses = {}
    for name, url in [
        ("camera", SERVER1_URL),
        ("storage", SERVER2_URL),
        ("inference", INFERENCE_URL),
        ("labelstudio", LABELSTUDIO_URL),
    ]:
        try:
            health_path = "/api/v1/health" if name != "labelstudio" else "/health"
            r = requests.get(f"{url}{health_path}", timeout=3)
            statuses[name] = {"healthy": r.ok, "status_code": r.status_code}
        except Exception as e:
            statuses[name] = {"healthy": False, "error": str(e)}

    return statuses


@app.post("/api/capture")
async def proxy_capture():
    """Trigger camera capture → upload pipeline."""
    try:
        r = requests.post(f"{SERVER1_URL}/api/v1/capture", timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Camera service error: {e}")


@app.post("/api/predict")
async def proxy_predict(file: UploadFile = File(...)):
    """Forward image to inference service for prediction."""
    try:
        files = {"file": (file.filename, await file.read(), file.content_type)}
        r = requests.post(f"{INFERENCE_URL}/api/v1/predict", files=files, timeout=60)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Inference service error: {e}")


@app.get("/api/stats")
async def proxy_stats():
    """Get storage stats from server2."""
    try:
        r = requests.get(f"{SERVER2_URL}/api/v1/stats", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Storage service error: {e}")


@app.get("/api/images/labeled")
async def proxy_labeled_images():
    """List labeled images."""
    try:
        r = requests.get(f"{SERVER2_URL}/api/v1/images/labeled", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Storage service error: {e}")


@app.get("/api/inference/status")
async def proxy_inference_status():
    """Get inference model status."""
    try:
        r = requests.get(f"{INFERENCE_URL}/api/v1/status", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Inference service error: {e}")


@app.post("/api/capture-and-predict")
async def capture_and_predict():
    """
    Capture image from camera and run inference.
    Flow: Dashboard → Server 1 (capture) → Server 3 (predict) → Dashboard (results)
    """
    try:
        # Step 1: Capture image from camera service
        cap_r = requests.post(f"{SERVER1_URL}/api/v1/capture-image", timeout=30)
        cap_r.raise_for_status()

        image_bytes = cap_r.content
        filename = cap_r.headers.get("X-Image-Filename", "capture.jpg")

        # Step 2: Send captured image to inference service
        files = {"file": (filename, io.BytesIO(image_bytes), "image/jpeg")}
        pred_r = requests.post(f"{INFERENCE_URL}/api/v1/predict", files=files, timeout=60)
        pred_r.raise_for_status()

        result = pred_r.json()
        result["source"] = "camera_capture"
        result["image_name"] = filename
        return result

    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Capture-and-predict failed: {e}")


@app.post("/api/capture-label-and-predict")
async def capture_label_and_predict():
    """
    Full flow: capture image → upload to storage (for labeling) → run inference.
    Used when you want to both label AND get a prediction for the same image.
    """
    try:
        # Step 1: Capture and upload to server2 (label flow)
        cap_r = requests.post(f"{SERVER1_URL}/api/v1/capture", timeout=30)
        cap_r.raise_for_status()
        capture_data = cap_r.json()

        # Step 2: Also capture a fresh image for inference
        cap_img_r = requests.post(f"{SERVER1_URL}/api/v1/capture-image", timeout=30)
        cap_img_r.raise_for_status()

        image_bytes = cap_img_r.content
        filename = cap_img_r.headers.get("X-Image-Filename", "capture.jpg")

        # Step 3: Run inference
        files = {"file": (filename, io.BytesIO(image_bytes), "image/jpeg")}
        pred_r = requests.post(f"{INFERENCE_URL}/api/v1/predict", files=files, timeout=60)
        pred_r.raise_for_status()

        result = pred_r.json()
        result["source"] = "camera_capture"
        result["also_uploaded_to_labelstudio"] = True
        result["capture_info"] = capture_data
        return result

    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Capture-label-predict failed: {e}")


@app.get("/api/labeled-images")
async def list_labeled_images():
    """List all labeled images available for training."""
    try:
        r = requests.get(f"{SERVER2_URL}/api/v1/images/labeled", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Storage service error: {e}")


@app.get("/api/labelstudio/stats")
async def proxy_labelstudio_stats():
    """Get Label Studio project statistics (labeling progress)."""
    try:
        r = requests.get(f"{SERVER2_URL}/api/v1/labelstudio/stats", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Storage service error: {e}")
