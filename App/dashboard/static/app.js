// PCB Dashboard - Frontend Logic

document.addEventListener('DOMContentLoaded', () => {
  // ── Input mode state ──
  let inputMode = 'camera'; // 'camera' or 'upload'
  let galleryMode = 'unlabeled'; // 'unlabeled' or 'labeled'

  // ── Mode selector ──
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      inputMode = btn.dataset.mode;
      updateModeUI();
    });
  });

  function updateModeUI() {
    const hint = document.getElementById('mode-hint');
    const cameraActions = document.getElementById('camera-actions');
    const uploadSeparator = document.getElementById('upload-separator');

    if (inputMode === 'camera') {
      hint.innerHTML = 'Using camera via Server 1. On MacBook set <code>USE_CAMERA=true</code> in .env.';
      cameraActions.classList.remove('hidden');
      uploadSeparator.textContent = 'Or upload an image manually:';
    } else {
      hint.innerHTML = 'Upload images manually. Useful for testing without a camera connected.';
      cameraActions.classList.add('hidden');
      uploadSeparator.textContent = 'Upload an image:';
    }
  }

  // ── Tab switching ──
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    });
  });

  // ── Gallery tab switching ──
  document.querySelectorAll('.gallery-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.gallery-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      galleryMode = tab.dataset.gallery;
    });
  });

  // ── Service status ──
  async function checkServices() {
    try {
      const r = await fetch('/api/services/status');
      const data = await r.json();
      const bar = document.getElementById('service-status');
      bar.innerHTML = Object.entries(data).map(([name, info]) => {
        const ok = info.healthy;
        return `<span><span class="status-dot ${ok ? 'ok' : 'err'}"></span>${name}</span>`;
      }).join('');
    } catch {
      document.getElementById('service-status').textContent = 'Failed to check services';
    }
  }
  checkServices();
  setInterval(checkServices, 15000);

  // ── Capture button (Label Mode) ──
  const captureBtn = document.getElementById('btn-capture');
  const captureResult = document.getElementById('capture-result');

  captureBtn.addEventListener('click', async () => {
    captureBtn.disabled = true;
    captureBtn.textContent = 'Capturing...';
    captureResult.classList.add('hidden');

    try {
      const r = await fetch('/api/capture', { method: 'POST' });
      const data = await r.json();
      captureResult.classList.remove('hidden');

      if (r.ok) {
        captureResult.innerHTML = `
          <strong>Capture successful!</strong><br>
          Image: ${data.image_name || 'N/A'}<br>
          Status: ${data.server2_response?.status || data.status || 'uploaded'}<br>
          <small>Image is now available in Label Studio for labeling.</small>
        `;
      } else {
        captureResult.innerHTML = `<strong style="color:var(--danger)">Error:</strong> ${data.detail || JSON.stringify(data)}`;
      }
    } catch (e) {
      captureResult.classList.remove('hidden');
      captureResult.innerHTML = `<strong style="color:var(--danger)">Error:</strong> ${e.message}`;
    }

    captureBtn.disabled = false;
    captureBtn.textContent = 'Capture Image';
    loadStats();
  });

  // ── Capture & Predict (Inference Mode) ──
  const capPredictBtn = document.getElementById('btn-capture-predict');
  const capLabelPredictBtn = document.getElementById('btn-capture-label-predict');
  const inferenceLoading = document.getElementById('inference-loading');
  const inferenceResult = document.getElementById('inference-result');

  capPredictBtn.addEventListener('click', async () => {
    capPredictBtn.disabled = true;
    capPredictBtn.textContent = 'Capturing & Predicting...';
    inferenceResult.classList.add('hidden');
    inferenceLoading.classList.remove('hidden');

    try {
      const r = await fetch('/api/capture-and-predict', { method: 'POST' });
      const data = await r.json();
      inferenceLoading.classList.add('hidden');
      inferenceResult.classList.remove('hidden');

      if (r.ok) {
        renderPredictionResult(data);
      } else {
        inferenceResult.innerHTML = `<strong style="color:var(--danger)">Error:</strong> ${data.detail || JSON.stringify(data)}`;
      }
    } catch (e) {
      inferenceLoading.classList.add('hidden');
      inferenceResult.classList.remove('hidden');
      inferenceResult.innerHTML = `<strong style="color:var(--danger)">Error:</strong> ${e.message}`;
    }

    capPredictBtn.disabled = false;
    capPredictBtn.textContent = 'Capture & Predict';
  });

  capLabelPredictBtn.addEventListener('click', async () => {
    capLabelPredictBtn.disabled = true;
    capLabelPredictBtn.textContent = 'Processing...';
    inferenceResult.classList.add('hidden');
    inferenceLoading.classList.remove('hidden');

    try {
      const r = await fetch('/api/capture-label-and-predict', { method: 'POST' });
      const data = await r.json();
      inferenceLoading.classList.add('hidden');
      inferenceResult.classList.remove('hidden');

      if (r.ok) {
        renderPredictionResult(data);
        if (data.also_uploaded_to_labelstudio) {
          const note = document.createElement('p');
          note.style.cssText = 'color:var(--success); font-size:0.85rem; margin-top:8px;';
          note.textContent = 'Image also uploaded to Label Studio for labeling.';
          inferenceResult.appendChild(note);
        }
      } else {
        inferenceResult.innerHTML = `<strong style="color:var(--danger)">Error:</strong> ${data.detail || JSON.stringify(data)}`;
      }
    } catch (e) {
      inferenceLoading.classList.add('hidden');
      inferenceResult.classList.remove('hidden');
      inferenceResult.innerHTML = `<strong style="color:var(--danger)">Error:</strong> ${e.message}`;
    }

    capLabelPredictBtn.disabled = false;
    capLabelPredictBtn.textContent = 'Capture, Label & Predict';
    loadStats();
  });

  // ── Shared prediction result renderer (with image + bounding boxes) ──
  function renderPredictionResult(data) {
    const qualityClass = data.overall_quality === 'Pass' ? 'quality-pass'
      : data.overall_quality === 'Fail' ? 'quality-fail' : 'quality-review';

    const sourceLabels = {
      camera_capture: '(from camera)',
      button_capture: '(from GPIO button)',
      upload: '(uploaded)',
    };
    const sourceLabel = sourceLabels[data.source] || `(${data.source || 'unknown'})`;

    // Build detections HTML
    let detectionsHtml = '';
    if (data.detections && data.detections.length > 0) {
      detectionsHtml = '<ul class="det-list">' + data.detections.map((d, i) => {
        const pct = Math.round(d.confidence * 100);
        const color = getDetectionColor(i);
        return `<li>
          <span class="det-color-dot" style="background:${color}"></span>
          <strong>${d.class}</strong> (${pct}%)
          <span class="conf-bar" style="width:${pct}px; background:${color}"></span>
        </li>`;
      }).join('') + '</ul>';
    } else {
      detectionsHtml = '<p>No defects detected.</p>';
    }

    // Build image with overlay
    let imageHtml = '';
    if (data.image_base64) {
      imageHtml = `
        <div class="inference-image-container">
          <canvas id="inference-canvas" class="inference-canvas"></canvas>
        </div>
      `;
    }

    inferenceResult.innerHTML = `
      <div class="inference-summary">
        <strong>Overall Quality: <span class="${qualityClass}">${data.overall_quality}</span></strong>
        <small class="source-label">${sourceLabel}</small><br>
        <small>${data.detection_count} detection(s) in ${data.inference_time_ms}ms</small>
        ${data.image_name ? `<br><small>Image: ${data.image_name}</small>` : ''}
      </div>
      ${imageHtml}
      <div class="inference-detections">
        <strong>Detections:</strong>
        ${detectionsHtml}
      </div>
    `;

    // Draw image with bounding boxes on canvas
    if (data.image_base64) {
      drawDetectionsOnCanvas(data.image_base64, data.detections || [], data.image_size);
    }
  }

  // Color palette for detection bounding boxes
  const DETECTION_COLORS = [
    '#ef4444', '#f97316', '#eab308', '#22c55e',
    '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899',
  ];

  function getDetectionColor(index) {
    return DETECTION_COLORS[index % DETECTION_COLORS.length];
  }

  function drawDetectionsOnCanvas(base64, detections, imageSize) {
    const canvas = document.getElementById('inference-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = () => {
      // Set canvas size to fit within container while preserving aspect ratio
      const maxWidth = canvas.parentElement.clientWidth;
      const scale = Math.min(maxWidth / img.width, 600 / img.height, 1);
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;

      // Draw image
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      // Scale factors for bounding boxes
      const scaleX = canvas.width / (imageSize?.width || img.width);
      const scaleY = canvas.height / (imageSize?.height || img.height);

      // Draw each detection
      detections.forEach((det, i) => {
        const color = getDetectionColor(i);
        const bbox = det.bbox;
        if (!bbox) return;

        const x1 = bbox.x1 * scaleX;
        const y1 = bbox.y1 * scaleY;
        const x2 = bbox.x2 * scaleX;
        const y2 = bbox.y2 * scaleY;
        const w = x2 - x1;
        const h = y2 - y1;

        // Draw rectangle
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x1, y1, w, h);

        // Draw label background
        const label = `${det.class} ${Math.round(det.confidence * 100)}%`;
        ctx.font = 'bold 12px sans-serif';
        const textWidth = ctx.measureText(label).width;
        const labelHeight = 18;
        const labelY = y1 > labelHeight ? y1 - labelHeight : y1;

        ctx.fillStyle = color;
        ctx.fillRect(x1, labelY, textWidth + 8, labelHeight);

        // Draw label text
        ctx.fillStyle = '#ffffff';
        ctx.fillText(label, x1 + 4, labelY + 13);
      });
    };

    img.src = 'data:image/jpeg;base64,' + base64;
  }

  // ── Drag & drop / file upload for inference ──
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');

  dropZone.addEventListener('click', () => fileInput.click());

  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
      runInference(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length) {
      runInference(fileInput.files[0]);
    }
  });

  async function runInference(file) {
    inferenceResult.classList.add('hidden');
    inferenceLoading.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const r = await fetch('/api/predict', { method: 'POST', body: formData });
      const data = await r.json();
      inferenceLoading.classList.add('hidden');
      inferenceResult.classList.remove('hidden');

      if (r.ok) {
        data.source = 'upload';
        renderPredictionResult(data);
      } else {
        inferenceResult.innerHTML = `<strong style="color:var(--danger)">Error:</strong> ${data.detail || JSON.stringify(data)}`;
      }
    } catch (e) {
      inferenceLoading.classList.add('hidden');
      inferenceResult.classList.remove('hidden');
      inferenceResult.innerHTML = `<strong style="color:var(--danger)">Error:</strong> ${e.message}`;
    }
  }

  // ── Storage stats ──
  async function loadStats() {
    try {
      const r = await fetch('/api/stats');
      const data = await r.json();
      document.getElementById('storage-stats').innerHTML = `
        <div class="stats-grid">
          <div class="stat-box">
            <div class="number">${data.unlabeled?.count ?? '?'}</div>
            <div class="label">Unlabeled</div>
          </div>
          <div class="stat-box">
            <div class="number">${data.labeled?.count ?? '?'}</div>
            <div class="label">Labeled</div>
          </div>
          <div class="stat-box">
            <div class="number">${data.total?.size_mb ?? '?'} MB</div>
            <div class="label">Total Size</div>
          </div>
        </div>
      `;
    } catch {
      document.getElementById('storage-stats').textContent = 'Failed to load stats';
    }
  }
  loadStats();

  // ── Labeling progress ──
  async function loadLabelingProgress() {
    try {
      const r = await fetch('/api/labelstudio/stats');
      const data = await r.json();

      if (data.error) {
        const html = `<p style="color:var(--muted)">${data.error}</p>`;
        document.getElementById('labeling-progress').innerHTML = html;
        document.getElementById('training-labeling-progress').innerHTML = html;
        return;
      }

      const total = data.total_tasks || 0;
      const completed = data.completed_tasks || 0;
      const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

      const html = `
        <div class="stats-grid">
          <div class="stat-box">
            <div class="number">${total}</div>
            <div class="label">Total Tasks</div>
          </div>
          <div class="stat-box">
            <div class="number">${completed}</div>
            <div class="label">Completed</div>
          </div>
          <div class="stat-box">
            <div class="number">${data.total_annotations || 0}</div>
            <div class="label">Annotations</div>
          </div>
          <div class="stat-box">
            <div class="number">${pct}%</div>
            <div class="label">Progress</div>
          </div>
        </div>
        <div class="progress-bar-container">
          <div class="progress-bar" style="width: ${pct}%"></div>
        </div>
      `;

      document.getElementById('labeling-progress').innerHTML = html;
      document.getElementById('training-labeling-progress').innerHTML = html;
    } catch {
      const msg = 'Label Studio not connected yet. Set API key in .env';
      document.getElementById('labeling-progress').textContent = msg;
      document.getElementById('training-labeling-progress').textContent = msg;
    }
  }
  loadLabelingProgress();

  // ── Image Gallery ──
  const refreshGalleryBtn = document.getElementById('btn-refresh-gallery');
  const galleryGrid = document.getElementById('gallery-grid');

  refreshGalleryBtn.addEventListener('click', loadGallery);

  async function loadGallery() {
    refreshGalleryBtn.disabled = true;
    refreshGalleryBtn.textContent = 'Loading...';
    galleryGrid.innerHTML = '<div class="spinner"></div><p>Loading images...</p>';

    const endpoint = galleryMode === 'labeled' ? '/api/images/labeled' : '/api/images/unlabeled';

    try {
      const r = await fetch(endpoint);
      const data = await r.json();
      const images = data.images || data;

      if (!Array.isArray(images) || images.length === 0) {
        galleryGrid.innerHTML = `<p style="color:var(--muted)">No ${galleryMode} images found.</p>`;
        refreshGalleryBtn.disabled = false;
        refreshGalleryBtn.textContent = 'Refresh';
        return;
      }

      galleryGrid.innerHTML = `<p style="color:var(--muted); margin-bottom:12px;">${images.length} ${galleryMode} image(s)</p>`;

      const grid = document.createElement('div');
      grid.className = 'image-grid';

      images.forEach(img => {
        const card = document.createElement('div');
        card.className = 'image-card';

        // Build the image URL from the stored path
        // Path is like /data/unlabeled/ab/cd/.../file.jpg or /data/labeled/file.jpg
        const storedPath = img.path || img.image_path || '';
        const relativePath = storedPath.replace(/^\/data\//, '');
        const imageUrl = `/api/images/serve/${relativePath}`;

        const filename = img.filename || storedPath.split('/').pop() || 'unknown';
        const sizeKb = img.size_bytes ? (img.size_bytes / 1024).toFixed(1) : '?';
        const hasAnnotation = img.has_annotation ? '<span class="badge badge-success">Labeled</span>' : '';

        card.innerHTML = `
          <div class="image-thumb" style="background-image: url('${imageUrl}')"></div>
          <div class="image-card-info">
            <span class="image-card-name" title="${filename}">${filename}</span>
            <span class="image-card-meta">${sizeKb} KB ${hasAnnotation}</span>
          </div>
        `;

        card.addEventListener('click', () => openLightbox(imageUrl, filename, img));
        grid.appendChild(card);
      });

      galleryGrid.appendChild(grid);
    } catch (e) {
      galleryGrid.innerHTML = `<strong style="color:var(--danger)">Error:</strong> ${e.message}`;
    }

    refreshGalleryBtn.disabled = false;
    refreshGalleryBtn.textContent = 'Refresh';
  }

  // ── Lightbox ──
  function openLightbox(imageUrl, filename, imgData) {
    const lightbox = document.getElementById('lightbox');
    const lightboxImg = document.getElementById('lightbox-img');
    const lightboxInfo = document.getElementById('lightbox-info');

    lightboxImg.src = imageUrl;

    const sizeKb = imgData.size_bytes ? (imgData.size_bytes / 1024).toFixed(1) : '?';
    const path = imgData.path || imgData.image_path || '';
    const annotation = imgData.has_annotation ? 'Yes' : 'No';

    lightboxInfo.innerHTML = `
      <strong>${filename}</strong><br>
      <small>Size: ${sizeKb} KB</small><br>
      <small>Path: ${path}</small><br>
      <small>Has annotation: ${annotation}</small>
    `;

    lightbox.classList.remove('hidden');
  }

  // ── Labeled images list (Training tab) ──
  const refreshLabeledBtn = document.getElementById('btn-refresh-labeled');
  const labeledList = document.getElementById('labeled-images-list');

  refreshLabeledBtn.addEventListener('click', async () => {
    refreshLabeledBtn.disabled = true;
    refreshLabeledBtn.textContent = 'Loading...';

    try {
      const r = await fetch('/api/labeled-images');
      const data = await r.json();

      if (r.ok) {
        const images = data.images || data;
        if (Array.isArray(images) && images.length > 0) {
          labeledList.innerHTML = `
            <strong>${images.length} labeled image(s) available for training:</strong>
            <ul class="det-list" style="margin-top:8px;">
              ${images.map(img => {
                const name = typeof img === 'string' ? img : (img.filename || img.name || img.path || JSON.stringify(img));
                return `<li>${name}</li>`;
              }).join('')}
            </ul>
            <p style="margin-top:12px; color:var(--muted); font-size:0.8rem;">
              These images are stored in the server2 <code>/data/labeled</code> volume.<br>
              Access via: <code>docker compose exec server2 ls /data/labeled</code>
            </p>
          `;
        } else {
          labeledList.innerHTML = '<p>No labeled images yet. Capture images and label them in Label Studio first.</p>';
        }
      } else {
        labeledList.innerHTML = `<strong style="color:var(--danger)">Error:</strong> ${data.detail || JSON.stringify(data)}`;
      }
    } catch (e) {
      labeledList.innerHTML = `<strong style="color:var(--danger)">Error:</strong> ${e.message}`;
    }

    refreshLabeledBtn.disabled = false;
    refreshLabeledBtn.textContent = 'Refresh List';
  });

  // ── Model info ──
  async function loadModelInfo() {
    try {
      const r = await fetch('/api/inference/status');
      const data = await r.json();
      const m = data.model || {};
      document.getElementById('model-info').innerHTML = `
        <div class="stats-grid">
          <div class="stat-box">
            <div class="number">${m.model_loaded ? 'Ready' : 'Loading'}</div>
            <div class="label">Status</div>
          </div>
          <div class="stat-box">
            <div class="number">${m.model_info?.class_count ?? '?'}</div>
            <div class="label">Classes</div>
          </div>
          <div class="stat-box">
            <div class="number">${m.confidence_threshold ?? '?'}</div>
            <div class="label">Conf. Threshold</div>
          </div>
        </div>
      `;
    } catch {
      document.getElementById('model-info').textContent = 'Failed to load model info';
    }
  }
  loadModelInfo();
});
