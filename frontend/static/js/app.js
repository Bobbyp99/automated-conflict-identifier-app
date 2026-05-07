/* app.js — FPPC Conflict Analyzer frontend */

const API = "http://localhost:8000";

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  interestsDataset: null,   // { id, name, rows, headers }
  votesDataset: null,
  currentRunId: null,
  allMatches: [],
};

// ── Helpers ────────────────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API error");
  }
  return res.json();
}

function esc(s) {
  return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function showErr(id, msg) {
  const el = document.getElementById(id);
  if (el) el.textContent = msg || "";
}

function setTab(name) {
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.toggle("hidden", p.dataset.panel !== name));
  if (name === "history") loadHistory();
}

// ── File Upload ────────────────────────────────────────────────────────────
async function handleUpload(kind, file) {
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  form.append("kind", kind);

  const zoneId  = kind === "interests" ? "zone-i" : "zone-v";
  const fnId    = kind === "interests" ? "fn-i"   : "fn-v";
  const fcId    = kind === "interests" ? "fc-i"   : "fc-v";

  document.getElementById(fnId).textContent = "Uploading…";

  try {
    const data = await apiFetch("/api/upload", { method: "POST", body: form });

    document.getElementById(zoneId).classList.add("loaded");
    document.getElementById(fnId).textContent = data.name;
    document.getElementById(fcId).textContent = `${data.rows} rows · ${data.headers.length} columns`;

    if (kind === "interests") state.interestsDataset = data;
    else                      state.votesDataset = data;

    showErr("upload-err", "");
    maybeOpenMapping();
  } catch (e) {
    showErr("upload-err", e.message);
    document.getElementById(fnId).textContent = "";
  }
}

function maybeOpenMapping() {
  if (!state.interestsDataset || !state.votesDataset) return;
  document.getElementById("step1-done").classList.remove("hidden");
  document.getElementById("mapping-body").classList.remove("hidden");
  populateMappingSelects();
}

function populateMappingSelects() {
  const iH = state.interestsDataset.headers;
  const vH = state.votesDataset.headers;
  const g  = state.interestsDataset.guessed;
  const gv = state.votesDataset.guessed;

  fillSelect("ci-emp",  iH, g.employee);
  fillSelect("ci-ent",  iH, g.entity, false);
  fillSelect("ci-type", iH, null, true);
  fillSelect("cv-emp",  vH, gv.employee);
  fillSelect("cv-sub",  vH, gv.subject, false);
  fillSelect("cv-date", vH, null, true);
}

function fillSelect(id, headers, preferred, optional = false) {
  const el = document.getElementById(id);
  const none = optional ? `<option value="">— none —</option>` : "";
  el.innerHTML = none + headers.map(h =>
    `<option value="${esc(h)}"${h === preferred ? " selected" : ""}>${esc(h)}</option>`
  ).join("");
}

// ── Run Analysis ───────────────────────────────────────────────────────────
async function runAnalysis() {
  showErr("analyze-err", "");
  document.getElementById("run-btn").disabled = true;
  document.getElementById("run-btn").textContent = "Analyzing…";

  const body = {
    interests_dataset_id:    state.interestsDataset.id,
    votes_dataset_id:        state.votesDataset.id,
    col_employee_interests:  document.getElementById("ci-emp").value,
    col_entity:              document.getElementById("ci-ent").value,
    col_employee_votes:      document.getElementById("cv-emp").value,
    col_subject:             document.getElementById("cv-sub").value,
  };

  try {
    const data = await apiFetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    state.currentRunId = data.run_id;
    state.allMatches = data.matches;

    document.getElementById("step2-done").classList.remove("hidden");
    document.getElementById("results-area").classList.remove("hidden");

    renderStats();
    populateEmployeeFilter();
    renderResults();

    document.getElementById("results-area").scrollIntoView({ behavior: "smooth" });
  } catch (e) {
    showErr("analyze-err", e.message);
  } finally {
    document.getElementById("run-btn").disabled = false;
    document.getElementById("run-btn").textContent = "Run conflict analysis";
  }
}

// ── Stats ──────────────────────────────────────────────────────────────────
function renderStats() {
  const m = state.allMatches;
  const high = m.filter(x => x.likelihood === "High").length;
  const med  = m.filter(x => x.likelihood === "Medium").length;
  const low  = m.filter(x => x.likelihood === "Low").length;
  const emps = new Set(m.map(x => x.employee)).size;

  document.getElementById("stats-bar").innerHTML = `
    <div class="stat-cell"><div class="stat-num red">${high}</div><div class="stat-label">High likelihood</div></div>
    <div class="stat-cell"><div class="stat-num yellow">${med}</div><div class="stat-label">Medium</div></div>
    <div class="stat-cell"><div class="stat-num green">${low}</div><div class="stat-label">Low</div></div>
    <div class="stat-cell"><div class="stat-num">${emps}</div><div class="stat-label">Officials flagged</div></div>
    <div class="stat-cell"><div class="stat-num">${m.length}</div><div class="stat-label">Total matches</div></div>
  `;
}

function populateEmployeeFilter() {
  const emps = [...new Set(state.allMatches.map(m => m.employee))].sort();
  const sel = document.getElementById("f-emp");
  sel.innerHTML = `<option value="">All employees</option>` +
    emps.map(e => `<option value="${esc(e)}">${esc(e)}</option>`).join("");
}

// ── Render Results ─────────────────────────────────────────────────────────
function renderResults() {
  const search = (document.getElementById("f-search").value || "").toLowerCase();
  const level  = document.getElementById("f-level").value;
  const emp    = document.getElementById("f-emp").value;

  let filtered = state.allMatches;
  if (level)  filtered = filtered.filter(m => m.likelihood === level);
  if (emp)    filtered = filtered.filter(m => m.employee === emp);
  if (search) filtered = filtered.filter(m =>
    m.employee.toLowerCase().includes(search) ||
    m.entity.toLowerCase().includes(search) ||
    m.subject.toLowerCase().includes(search)
  );

  document.getElementById("r-count").textContent =
    filtered.length + " match" + (filtered.length !== 1 ? "es" : "");

  const list = document.getElementById("match-list");
  if (!filtered.length) {
    list.innerHTML = `<div class="empty">No matches for the selected filters.</div>`;
    return;
  }

  list.innerHTML = filtered.map(m => {
    const barColor = m.likelihood === "High" ? "#ef4444" : m.likelihood === "Medium" ? "#f59e0b" : "#22c55e";
    const extra = [
      m.vote_date   ? `<span><strong>Date:</strong> ${esc(m.vote_date)}</span>` : "",
      m.entity_type ? `<span><strong>Interest type:</strong> ${esc(m.entity_type)}</span>` : "",
    ].join("");
    return `<div class="match-card ${m.likelihood.toLowerCase()}">
      <div class="match-top">
        <div>
          <div class="match-emp">${esc(m.employee)}</div>
          <div class="match-entity">Interest: ${esc(m.entity)}</div>
        </div>
        <span class="badge badge-${m.likelihood.toLowerCase()}">${esc(m.likelihood)}</span>
      </div>
      <div class="score-row">
        <div class="score-bg"><div class="score-fill" style="width:${Math.min(m.score,100)}%;background:${barColor};"></div></div>
        <span class="score-val">${m.score}%</span>
      </div>
      <div class="match-detail">
        <span><strong>Vote subject:</strong> ${esc(m.subject)}</span>
        ${extra}
      </div>
    </div>`;
  }).join("");
}

// ── History tab ────────────────────────────────────────────────────────────
async function loadHistory() {
  document.getElementById("history-list").innerHTML = `<div class="loader">Loading past runs…</div>`;
  try {
    const runs = await apiFetch("/api/runs");
    if (!runs.length) {
      document.getElementById("history-list").innerHTML = `<div class="empty">No analysis runs yet.</div>`;
      return;
    }
    document.getElementById("history-list").innerHTML = runs.map(r => {
      const d = new Date(r.created_at).toLocaleString();
      return `<div class="run-row" onclick="loadRun('${esc(r.run_id)}')">
        <div>
          <div class="run-count">${r.count} matches</div>
          <div class="run-date">${d}</div>
        </div>
        <div class="run-high">${r.high} high-likelihood</div>
        <span style="color:var(--text-dim);font-size:11px;">→ load</span>
      </div>`;
    }).join("");
  } catch (e) {
    document.getElementById("history-list").innerHTML = `<div class="err">${esc(e.message)}</div>`;
  }
}

async function loadRun(runId) {
  try {
    const matches = await apiFetch(`/api/results/${runId}`);
    state.currentRunId = runId;
    state.allMatches = matches;
    setTab("analyze");
    document.getElementById("results-area").classList.remove("hidden");
    renderStats();
    populateEmployeeFilter();
    renderResults();
    document.getElementById("results-area").scrollIntoView({ behavior: "smooth" });
  } catch (e) {
    alert("Failed to load run: " + e.message);
  }
}

// ── Event wiring ───────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Tab clicks
  document.querySelectorAll(".tab").forEach(t => {
    t.addEventListener("click", () => setTab(t.dataset.tab));
  });

  // File input changes
  document.getElementById("fi").addEventListener("change", e => handleUpload("interests", e.target.files[0]));
  document.getElementById("fv").addEventListener("change", e => handleUpload("votes", e.target.files[0]));

  // Drag and drop
  ["zone-i", "zone-v"].forEach(zoneId => {
    const zone = document.getElementById(zoneId);
    const kind = zoneId === "zone-i" ? "interests" : "votes";
    zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("drag-over"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", e => {
      e.preventDefault();
      zone.classList.remove("drag-over");
      handleUpload(kind, e.dataTransfer.files[0]);
    });
  });

  // Analyze button
  document.getElementById("run-btn").addEventListener("click", runAnalysis);

  // Filters
  ["f-search", "f-level", "f-emp"].forEach(id => {
    document.getElementById(id).addEventListener("input", renderResults);
    document.getElementById(id).addEventListener("change", renderResults);
  });
});
