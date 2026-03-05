// PCB Dashboard - Frontend Logic

document.addEventListener('DOMContentLoaded', () => {
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

  // ── Capture button ──
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

  // ── Drag & drop / file upload for inference ──
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');
  const inferenceLoading = document.getElementById('inference-loading');
  const inferenceResult = document.getElementById('inference-result');

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

        inferenceResult.innerHTML = `
          <strong>Overall Quality: <span class="${qualityClass}">${data.overall_quality}</span></strong><br>
          <small>${data.detection_count} detection(s) in ${data.inference_time_ms}ms</small>
          <br><br>
          ${detectionsHtml}
        `;
      } else {
        inferenceResult.innerHTML = `<strong style="color:var(--danger)">Error:</strong> ${data.detail || JSON.stringify(data)}`;
      }
    } catch (e) {
      inferenceLoading.classList.add('hidden');
      inferenceResult.classList.remove('hidden');
      inferenceResult.innerHTML = `<strong style="color:var(--danger)">Error:</strong> ${e.message}`;
    }
  }

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
