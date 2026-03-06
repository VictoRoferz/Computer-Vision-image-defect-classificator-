"""
Dashboard Web UI for PCB Defect Classification System.
Provides a single-page interface for both Label and Inference workflows.
"""
import base64
import io
import os
import requests
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
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
async def proxy_capture(request: Request):
    """
    Capture image from server1 camera, upload to server2 storage, return image preview.
    Used for: server camera + test image modes.
    Accepts JSON body with optional 'mode' field: 'server' or 'test'.
    """
    try:
        # Read mode from request body (sent by frontend)
        mode = "server"
        try:
            body = await request.json()
            mode = body.get("mode", "server")
        except Exception:
            pass

        # Step 1: Capture raw image bytes from server1
        cap_r = requests.post(
            f"{SERVER1_URL}/api/v1/capture-image",
            params={"mode": mode},
            timeout=30,
        )
        cap_r.raise_for_status()

        image_bytes = cap_r.content
        filename = cap_r.headers.get("X-Image-Filename", "capture.jpg")

        # Step 2: Upload to server2 for Label Studio
        result = {
            "status": "success",
            "message": "Image captured and uploaded successfully",
            "image_name": filename,
            "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
        }

        try:
            files = {"file": (filename, io.BytesIO(image_bytes), "image/jpeg")}
            up_r = requests.post(f"{SERVER2_URL}/api/v1/upload", files=files, timeout=30)

            if up_r.ok:
                result["server2_response"] = up_r.json()
            else:
                result["server2_response"] = {"error": up_r.text}
                result["status"] = "partial"
                result["message"] = "Image captured but upload to storage failed"
        except requests.RequestException as e:
            result["server2_response"] = {"error": str(e)}
            result["status"] = "partial"
            result["message"] = f"Image captured but storage service unreachable: {e}"

        return result

    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Camera service error: {e}")


@app.post("/api/upload-to-storage")
async def upload_browser_image(file: UploadFile = File(...)):
    """
    Upload a browser-captured image to server2 storage for labeling.
    Used for: browser webcam capture → Label Studio.
    Returns upload status + image as base64 for preview.
    Always returns image_base64 so the captured photo card can display.
    """
    try:
        image_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {e}")

    # Always include image_base64 so the frontend can show the captured photo
    result = {
        "image_name": file.filename,
        "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
    }

    try:
        files = {"file": (file.filename, io.BytesIO(image_bytes), file.content_type or "image/jpeg")}
        r = requests.post(f"{SERVER2_URL}/api/v1/upload", files=files, timeout=30)

        if r.ok:
            result["status"] = "success"
            result["server2_response"] = r.json()
            result["message"] = "Image uploaded to storage and Label Studio"
        else:
            result["status"] = "partial"
            result["server2_response"] = {"error": r.text}
            result["message"] = "Image captured but upload to storage failed"
    except requests.RequestException as e:
        result["status"] = "partial"
        result["server2_response"] = {"error": str(e)}
        result["message"] = f"Image captured but storage service unreachable: {e}"

    return result


@app.post("/api/predict")
async def proxy_predict(file: UploadFile = File(...)):
    """Forward image to inference service for prediction. Returns prediction + base64 image."""
    try:
        image_bytes = await file.read()
        files = {"file": (file.filename, io.BytesIO(image_bytes), file.content_type)}
        r = requests.post(f"{INFERENCE_URL}/api/v1/predict", files=files, timeout=60)
        r.raise_for_status()

        result = r.json()
        result["image_base64"] = base64.b64encode(image_bytes).decode("utf-8")
        return result
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


@app.get("/api/images/unlabeled")
async def proxy_unlabeled_images():
    """List unlabeled images."""
    try:
        r = requests.get(f"{SERVER2_URL}/api/v1/images/unlabeled", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Storage service error: {e}")


@app.get("/api/images/serve/{category:path}")
async def proxy_serve_image(category: str):
    """Proxy image file from server2 storage to the browser."""
    try:
        r = requests.get(f"{SERVER2_URL}/api/v1/images/serve/{category}", timeout=10)
        r.raise_for_status()
        return Response(
            content=r.content,
            media_type=r.headers.get("content-type", "image/jpeg"),
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Image serving error: {e}")


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
async def capture_and_predict(request: Request):
    """
    Capture image from server1 camera and run inference.
    Returns prediction results + base64-encoded captured image.
    """
    try:
        mode = "server"
        try:
            body = await request.json()
            mode = body.get("mode", "server")
        except Exception:
            pass

        # Step 1: Capture image from camera service
        cap_r = requests.post(
            f"{SERVER1_URL}/api/v1/capture-image",
            params={"mode": mode},
            timeout=30,
        )
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
        result["image_base64"] = base64.b64encode(image_bytes).decode("utf-8")
        return result

    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Capture-and-predict failed: {e}")


@app.post("/api/capture-label-and-predict")
async def capture_label_and_predict(request: Request):
    """
    Full flow: capture image → upload to storage (for labeling) → run inference.
    Returns prediction results + base64-encoded captured image.
    """
    try:
        mode = "server"
        try:
            body = await request.json()
            mode = body.get("mode", "server")
        except Exception:
            pass

        # Step 1: Capture raw image from server1
        cap_r = requests.post(
            f"{SERVER1_URL}/api/v1/capture-image",
            params={"mode": mode},
            timeout=30,
        )
        cap_r.raise_for_status()

        image_bytes = cap_r.content
        filename = cap_r.headers.get("X-Image-Filename", "capture.jpg")

        # Step 2: Upload to server2 for labeling
        upload_files = {"file": (filename, io.BytesIO(image_bytes), "image/jpeg")}
        up_r = requests.post(f"{SERVER2_URL}/api/v1/upload", files=upload_files, timeout=30)

        # Step 3: Run inference
        infer_files = {"file": (filename, io.BytesIO(image_bytes), "image/jpeg")}
        pred_r = requests.post(f"{INFERENCE_URL}/api/v1/predict", files=infer_files, timeout=60)
        pred_r.raise_for_status()

        result = pred_r.json()
        result["source"] = "camera_capture"
        result["image_name"] = filename
        result["also_uploaded_to_labelstudio"] = up_r.ok
        if up_r.ok:
            result["capture_info"] = up_r.json()
        result["image_base64"] = base64.b64encode(image_bytes).decode("utf-8")
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
