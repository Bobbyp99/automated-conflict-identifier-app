const API = 'http://localhost:8000';

// Upload IDs returned by /api/upload
let interestsUploadId = null;
let votesUploadId     = null;

// Active scan job
let currentJobId   = null;
let pollInterval   = null;


// ── Tab switching ─────────────────────────────────────────────────────────────

document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.tab).classList.add('active');
    if (tab.dataset.tab === 'history') loadHistory();
  });
});


// ── Drop zone setup ───────────────────────────────────────────────────────────

['interests-zone', 'decisions-zone'].forEach(zoneId => {
  const zone  = document.getElementById(zoneId);
  const input = zone.querySelector('input[type="file"]');
  const kind  = zone.dataset.kind;

  zone.addEventListener('click', () => input.click());

  zone.addEventListener('dragover', e => {
    e.preventDefault();
    zone.classList.add('drag-over');
  });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) handleUpload(e.dataTransfer.files[0], kind, zone);
  });

  input.addEventListener('change', () => {
    if (input.files[0]) handleUpload(input.files[0], kind, zone);
  });
});


// ── Upload ────────────────────────────────────────────────────────────────────

async function handleUpload(file, kind, zone) {
  zone.classList.remove('uploaded');
  zone.querySelector('.drop-hint').textContent = 'Uploading…';

  const form = new FormData();
  form.append('file', file);
  form.append('kind', kind);

  try {
    const res  = await fetch(`${API}/api/upload`, { method: 'POST', body: form });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    if (kind === 'interests') {
      interestsUploadId = data.id;
    } else {
      votesUploadId = data.id;
    }

    zone.classList.add('uploaded');
    zone.querySelector('.drop-label').textContent = data.name;
    zone.querySelector('.drop-hint').textContent  = `${data.rows.toLocaleString()} rows loaded`;

    refreshStep2();
  } catch (err) {
    zone.querySelector('.drop-hint').textContent = `Upload failed: ${err.message}`;
  }
}

function refreshStep2() {
  if (!interestsUploadId || !votesUploadId) return;
  document.getElementById('step2').style.display = '';
  document.getElementById('interests-pill').textContent = 'Interests uploaded ✓';
  document.getElementById('decisions-pill').textContent = 'Decisions uploaded ✓';
}


// ── Run scan ──────────────────────────────────────────────────────────────────

document.getElementById('run-btn').addEventListener('click', startScan);

async function startScan() {
  if (!interestsUploadId || !votesUploadId) return;

  // Reset UI
  document.getElementById('results-area').style.display   = 'none';
  document.getElementById('progress-area').style.display  = '';
  document.getElementById('run-btn').disabled             = true;
  setProgress(0, 0, 0);

  try {
    const res = await fetch(`${API}/api/scan`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ interests_id: interestsUploadId, votes_id: votesUploadId }),
    });
    if (!res.ok) throw new Error(await res.text());
    const { job_id } = await res.json();

    currentJobId = job_id;
    // Persist so user can reload the page and still see results
    localStorage.setItem('activeJobId', job_id);

    pollInterval = setInterval(pollStatus, 3000);
  } catch (err) {
    alert(`Failed to start scan: ${err.message}`);
    document.getElementById('progress-area').style.display = 'none';
    document.getElementById('run-btn').disabled            = false;
  }
}

async function pollStatus() {
  if (!currentJobId) return;
  try {
    const res  = await fetch(`${API}/api/scan/${currentJobId}`);
    const data = await res.json();

    setProgress(data.processed, data.total, data.flagged);

    if (data.status === 'done') {
      clearInterval(pollInterval);
      pollInterval = null;
      localStorage.removeItem('activeJobId');
      await showResults(currentJobId);
      document.getElementById('run-btn').disabled = false;
    } else if (data.status === 'error') {
      clearInterval(pollInterval);
      pollInterval = null;
      localStorage.removeItem('activeJobId');
      document.getElementById('progress-area').style.display = 'none';
      document.getElementById('run-btn').disabled            = false;
      alert(`Scan error: ${data.error || 'Unknown error'}`);
    }
  } catch (err) {
    console.warn('Poll error:', err);
  }
}

function setProgress(processed, total, flagged) {
  const pct = total > 0 ? Math.round((processed / total) * 100) : 0;
  document.getElementById('progress-bar').style.width  = `${pct}%`;
  document.getElementById('progress-label').textContent =
    total > 0 ? `Scanning matters…` : 'Starting scan…';
  document.getElementById('progress-count').textContent =
    total > 0 ? `${processed.toLocaleString()} / ${total.toLocaleString()} (${pct}%)` : '';
  document.getElementById('progress-flagged').textContent =
    `${flagged} conflict${flagged !== 1 ? 's' : ''} flagged so far`;
}


// ── Results ───────────────────────────────────────────────────────────────────

async function showResults(jobId) {
  document.getElementById('progress-area').style.display = 'none';

  const res     = await fetch(`${API}/api/results/${jobId}`);
  const results = await res.json();
  renderResults(results);
}

function renderResults(results) {
  const area = document.getElementById('results-area');
  area.style.display = '';

  const counts = { High: 0, Medium: 0, Low: 0 };
  results.forEach(r => { if (counts[r.likelihood] !== undefined) counts[r.likelihood]++; });

  document.getElementById('stat-total').textContent  = `${results.length} conflicts`;
  document.getElementById('stat-high').textContent   = `${counts.High} High`;
  document.getElementById('stat-medium').textContent = `${counts.Medium} Medium`;
  document.getElementById('stat-low').textContent    = `${counts.Low} Low`;

  const list = document.getElementById('results-list');
  list.innerHTML = '';

  if (results.length === 0) {
    list.innerHTML = '<div class="empty-state">No conflicts flagged.</div>';
    return;
  }

  results.forEach(r => list.appendChild(buildCard(r)));
}

function buildCard(r) {
  const card = document.createElement('div');
  card.className = 'match-card';

  const linkHtml = r.link
    ? `<a href="${r.link}" target="_blank" rel="noopener">View Matter ↗</a>`
    : '';

  // For results from conflictScanner there's no pre-computed score/likelihood;
  // derive a simple display tier from the schedule type.
  const likelihood = r.likelihood || deriveLikelihood(r);
  const badgeClass = likelihood;

  card.innerHTML = `
    <div class="match-top">
      <div>
        <div class="match-name">${esc(r.official_name)}</div>
        <div class="match-entity">${esc(r.entity_matched)}</div>
      </div>
      <span class="likelihood-badge ${badgeClass}">${likelihood}</span>
    </div>
    <div class="match-subject">${esc(r.subject)}</div>
    <div class="match-meta">
      <span>${esc(r.vote_date)}</span>
      <span>${esc(r.vote_outcome)}</span>
      <span>${esc(r.file_number)}</span>
      <span>${esc(r.interest_schedule)} · ${esc(r.interest_year)}</span>
      ${linkHtml}
    </div>
  `;
  return card;
}

function deriveLikelihood(r) {
  // Assign tier based on schedule type when no score is available
  const s = (r.interest_schedule || '').toUpperCase();
  if (s.startsWith('C'))  return 'High';    // Direct income source
  if (s.startsWith('A'))  return 'Medium';  // Investment
  if (s.startsWith('B'))  return 'Low';     // Real property
  return 'Low';
}

function esc(str) {
  return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}


// ── Past runs ─────────────────────────────────────────────────────────────────

async function loadHistory() {
  const list = document.getElementById('runs-list');
  list.innerHTML = '<div class="empty-state">Loading…</div>';

  try {
    const res  = await fetch(`${API}/api/runs`);
    const runs = await res.json();

    if (!runs.length) {
      list.innerHTML = '<div class="empty-state">No past runs yet.</div>';
      return;
    }

    list.innerHTML = '';
    runs.forEach(run => list.appendChild(buildRunCard(run)));
  } catch (err) {
    list.innerHTML = `<div class="empty-state">Error loading runs: ${err.message}</div>`;
  }
}

function buildRunCard(run) {
  const card = document.createElement('div');
  card.className = 'run-card';

  const date      = run.created_at ? new Date(run.created_at).toLocaleString() : '—';
  const statusCls = run.status;
  const progress  = run.total > 0
    ? `${run.processed} / ${run.total} matters`
    : '';

  card.innerHTML = `
    <div class="run-summary">
      <div class="run-meta">
        <span class="run-date">${date}</span>
        <span class="run-status ${statusCls}">${run.status}${progress ? ' · ' + progress : ''}</span>
      </div>
      <span class="run-flagged">${run.flagged} flagged</span>
    </div>
    <div class="run-expand" id="expand-${run.job_id}"></div>
  `;

  card.querySelector('.run-summary').addEventListener('click', () =>
    toggleRunExpand(run.job_id, card)
  );

  return card;
}

async function toggleRunExpand(jobId, card) {
  const expand = card.querySelector('.run-expand');
  const open   = expand.classList.toggle('open');

  if (open && !expand.dataset.loaded) {
    expand.innerHTML = '<div class="empty-state">Loading results…</div>';
    try {
      const res     = await fetch(`${API}/api/results/${jobId}`);
      const results = await res.json();
      expand.innerHTML = '';
      if (results.length === 0) {
        expand.innerHTML = '<div class="empty-state">No conflicts in this run.</div>';
      } else {
        results.forEach(r => expand.appendChild(buildCard(r)));
      }
      expand.dataset.loaded = '1';
    } catch (err) {
      expand.innerHTML = `<div class="empty-state">Error: ${err.message}</div>`;
    }
  }
}


// ── Resume in-progress scan on page load ──────────────────────────────────────

(async function resumeIfActive() {
  const savedJobId = localStorage.getItem('activeJobId');
  if (!savedJobId) return;

  try {
    const res  = await fetch(`${API}/api/scan/${savedJobId}`);
    const data = await res.json();

    if (data.status === 'done') {
      localStorage.removeItem('activeJobId');
      currentJobId = savedJobId;
      await showResults(savedJobId);
    } else if (data.status === 'running' || data.status === 'pending') {
      currentJobId = savedJobId;
      document.getElementById('progress-area').style.display = '';
      document.getElementById('run-btn').disabled            = true;
      setProgress(data.processed, data.total, data.flagged);
      pollInterval = setInterval(pollStatus, 3000);
    } else {
      localStorage.removeItem('activeJobId');
    }
  } catch {
    localStorage.removeItem('activeJobId');
  }
})();
