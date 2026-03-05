// PCB Dashboard - Frontend Logic

document.addEventListener('DOMContentLoaded', () => {
  // ── Input mode state ──
  let inputMode = 'camera'; // 'camera' or 'upload'

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
          inferenceResult.innerHTML += `<br><small style="color:var(--success)">Image also uploaded to Label Studio for labeling.</small>`;
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

  // ── Shared prediction result renderer ──
  function renderPredictionResult(data) {
    const qualityClass = data.overall_quality === 'Pass' ? 'quality-pass'
      : data.overall_quality === 'Fail' ? 'quality-fail' : 'quality-review';

    let detectionsHtml = '';
    if (data.detections && data.detections.length > 0) {
      detectionsHtml = '<ul class="det-list">' + data.detections.map(d => {
        const pct = Math.round(d.confidence * 100);
        return `<li>
          <strong>${d.class}</strong> (${pct}%)
          <span class="conf-bar" style="width:${pct}px"></span>
          <br><small>bbox: [${d.bbox.x1}, ${d.bbox.y1}, ${d.bbox.x2}, ${d.bbox.y2}]</small>
        </li>`;
      }).join('') + '</ul>';
    } else {
      detectionsHtml = '<p>No defects detected.</p>';
    }

    const sourceLabels = {
      camera_capture: '(from camera)',
      button_capture: '(from GPIO button)',
      upload: '(uploaded)',
    };
    const sourceLabel = sourceLabels[data.source] || `(${data.source || 'unknown'})`;

    inferenceResult.innerHTML = `
      <strong>Overall Quality: <span class="${qualityClass}">${data.overall_quality}</span></strong>
      <small class="source-label">${sourceLabel}</small><br>
      <small>${data.detection_count} detection(s) in ${data.inference_time_ms}ms</small>
      ${data.image_name ? `<br><small>Image: ${data.image_name}</small>` : ''}
      <br><br>
      ${detectionsHtml}
    `;
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
