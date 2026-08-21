/* ───────────────────────────────────────────
   Area Measurement Web App — Client JS
   ─────────────────────────────────────────── */

// ── DOM Elements ───────────────────────────
const video        = document.getElementById('camera-feed');
const canvas       = document.getElementById('snapshot-canvas');
const btnStart     = document.getElementById('btn-start-camera');
const btnCapture   = document.getElementById('btn-capture');
const btnStop      = document.getElementById('btn-stop-camera');
const fileInput    = document.getElementById('file-input');
const uploadArea   = document.getElementById('upload-area');
const spinner      = document.getElementById('spinner');
const resultCard   = document.getElementById('result-card');
const resultImg    = document.getElementById('result-image');
const resultTotal  = document.getElementById('result-total-area');
const resultCount  = document.getElementById('result-object-count');
const resultObjs   = document.getElementById('result-objects');
const historyList  = document.getElementById('history-list');
const emptyState   = document.getElementById('empty-state');

// ── Navigation (SPA-like) ──────────────────
const navLinks   = document.querySelectorAll('.nav-links a');
const pages      = document.querySelectorAll('.page');

function navigate(pageId) {
    pages.forEach(p => p.classList.toggle('active', p.id === pageId));
    navLinks.forEach(a => a.classList.toggle('active', a.dataset.page === pageId));

    if (pageId === 'page-history') loadHistory();

    const path = pageId === 'page-measure' ? '/' : '/history';
    history.pushState(null, '', path);
}

navLinks.forEach(a => a.addEventListener('click', e => {
    e.preventDefault();
    navigate(a.dataset.page);
}));

window.addEventListener('popstate', () => {
    const page = location.pathname === '/history' ? 'page-history' : 'page-measure';
    navigate(page);
});

(function initPage() {
    const page = location.pathname === '/history' ? 'page-history' : 'page-measure';
    navigate(page);
})();


// ── Camera ─────────────────────────────────
let stream = null;

async function startCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 960 } },
            audio: false,
        });
        video.srcObject = stream;
        video.style.display = 'block';
        btnStart.disabled = true;
        btnCapture.disabled = false;
        btnStop.disabled = false;
    } catch (err) {
        alert('Gagal mengakses kamera: ' + err.message);
    }
}

function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(t => t.stop());
        stream = null;
    }
    video.srcObject = null;
    video.style.display = 'none';
    btnStart.disabled = false;
    btnCapture.disabled = true;
    btnStop.disabled = true;
}

function captureFrame() {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    sendBase64(dataUrl);
}

btnStart.addEventListener('click', startCamera);
btnStop.addEventListener('click', stopCamera);
btnCapture.addEventListener('click', captureFrame);


// ── File Upload ────────────────────────────
uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.style.borderColor = 'var(--accent)'; });
uploadArea.addEventListener('dragleave', () => { uploadArea.style.borderColor = 'var(--border)'; });
uploadArea.addEventListener('drop', e => {
    e.preventDefault();
    uploadArea.style.borderColor = 'var(--border)';
    if (e.dataTransfer.files.length) sendFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => {
    if (fileInput.files.length) sendFile(fileInput.files[0]);
});


// ── API Calls ──────────────────────────────
function showLoading(show) {
    spinner.classList.toggle('visible', show);
    if (show) resultCard.classList.remove('visible');
}

async function sendBase64(dataUrl) {
    showLoading(true);
    try {
        const res = await fetch('/api/measure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_base64: dataUrl }),
        });
        const data = await res.json();
        handleResult(data);
    } catch (err) {
        alert('Error: ' + err.message);
    } finally {
        showLoading(false);
    }
}

async function sendFile(file) {
    showLoading(true);
    const form = new FormData();
    form.append('image', file);
    try {
        const res = await fetch('/api/measure', {
            method: 'POST',
            body: form,
        });
        const data = await res.json();
        handleResult(data);
    } catch (err) {
        alert('Error: ' + err.message);
    } finally {
        showLoading(false);
    }
}

function handleResult(data) {
    if (data.success) {
        // Output image
        resultImg.src = data.output_image_base64;
        resultImg.onclick = () => openLightbox(data.output_image_base64);

        // Stats
        resultTotal.textContent = data.total_area_cm2;
        resultCount.textContent = data.object_count;

        // Per-object list
        resultObjs.innerHTML = '<h4>Detail Per Objek</h4>';
        data.objects.forEach(obj => {
            const div = document.createElement('div');
            div.className = 'object-item';
            div.innerHTML = `
                <span class="obj-label">Objek #${obj.index}</span>
                <span class="obj-area">${obj.area_cm2} cm²</span>
            `;
            resultObjs.appendChild(div);
        });

        resultCard.classList.add('visible');

        // Scroll ke result
        resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
        alert('Pengukuran gagal: ' + (data.error || 'Unknown error'));
    }
}


// ── History ────────────────────────────────
async function loadHistory() {
    try {
        const res = await fetch('/api/history');
        const rows = await res.json();
        renderHistory(rows);
    } catch (err) {
        console.error('Failed to load history:', err);
    }
}

function renderHistory(rows) {
    historyList.innerHTML = '';

    if (rows.length === 0) {
        emptyState.style.display = 'block';
        return;
    }
    emptyState.style.display = 'none';

    rows.forEach(r => {
        const card = document.createElement('div');
        card.className = 'history-card';

        const isFailed = r.status === 'failed';
        const areaText = isFailed ? 'Gagal' : `${r.total_area_cm2} cm²`;
        const areaClass = isFailed ? 'hc-area failed' : 'hc-area';
        const badgeClass = isFailed ? 'badge badge-failed' : 'badge badge-success';
        const objCount = r.object_count || 0;

        // ── Header (always visible) ──
        let headerHTML = `
            <div class="history-card-header" onclick="toggleCard(this)">
                <div class="hc-left">
                    <span class="hc-id">#${r.id}</span>
                    <span class="${areaClass}">${areaText}</span>
                </div>
                <div class="hc-meta">
                    ${!isFailed ? `<span class="hc-objects-count">${objCount} objek</span>` : ''}
                    <span class="hc-time">${r.timestamp}</span>
                    <span class="${badgeClass}">${r.status}</span>
                    ${!isFailed ? '<span class="hc-toggle">▼</span>' : ''}
                </div>
            </div>
        `;

        // ── Body (expandable, only for success) ──
        let bodyHTML = '';
        if (!isFailed && r.output_image) {
            const imgUrl = `/static/outputs/${r.output_image}`;
            const objectsDetail = r.areas_detail || [];

            let objectsListHTML = '';
            objectsDetail.forEach(obj => {
                objectsListHTML += `
                    <div class="object-item">
                        <span class="obj-label">Objek #${obj.index}</span>
                        <span class="obj-area">${obj.area_cm2} cm²</span>
                    </div>
                `;
            });

            bodyHTML = `
                <div class="history-card-body">
                    <div class="hc-image-wrapper" onclick="event.stopPropagation(); openLightbox('${imgUrl}')">
                        <img src="${imgUrl}" alt="Output #${r.id}" loading="lazy">
                    </div>
                    <div class="hc-detail">
                        <div class="hc-detail-grid">
                            <div class="hc-detail-item">
                                <span class="dl">Total Luas</span>
                                <span class="dv">${r.total_area_cm2} cm²</span>
                            </div>
                            <div class="hc-detail-item">
                                <span class="dl">Jumlah Objek</span>
                                <span class="dv">${objCount}</span>
                            </div>
                        </div>
                        ${objectsListHTML ? `
                            <div class="hc-objects-list">
                                ${objectsListHTML}
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }

        card.innerHTML = headerHTML + bodyHTML;
        historyList.appendChild(card);
    });
}

function toggleCard(headerEl) {
    const card = headerEl.closest('.history-card');
    const body = card.querySelector('.history-card-body');
    if (body) card.classList.toggle('expanded');
}


// ── Lightbox ───────────────────────────────
function openLightbox(src) {
    const lb = document.getElementById('lightbox');
    const lbImg = document.getElementById('lightbox-img');
    lbImg.src = src;
    lb.classList.add('visible');
}

function closeLightbox() {
    document.getElementById('lightbox').classList.remove('visible');
}

// Close on Escape key
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeLightbox();
});
