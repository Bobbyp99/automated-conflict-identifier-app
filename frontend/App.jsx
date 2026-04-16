import { useState, useCallback, useMemo } from "react";

const STYLE = `
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --navy: #0b1628;
    --navy-mid: #152240;
    --navy-light: #1e3160;
    --amber: #e8a020;
    --amber-light: #f5c55a;
    --red: #c0392b;
    --red-light: #e74c3c;
    --text: #d4dde8;
    --text-dim: #7a8fa8;
    --border: rgba(232,160,32,0.2);
    --border-strong: rgba(232,160,32,0.5);
    --conflict: rgba(192,57,43,0.12);
    --conflict-border: rgba(192,57,43,0.5);
  }

  body {
    background: var(--navy);
    color: var(--text);
    font-family: 'IBM Plex Sans', sans-serif;
    min-height: 100vh;
  }

  .app {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 24px 60px;
  }

  /* Header */
  .header {
    border-bottom: 1px solid var(--border);
    padding: 28px 0 24px;
    margin-bottom: 40px;
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
  }
  .header-seal {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .seal-icon {
    width: 52px;
    height: 52px;
    border: 2px solid var(--amber);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    flex-shrink: 0;
  }
  .header-title {
    font-family: 'Playfair Display', serif;
    font-size: 22px;
    font-weight: 900;
    color: #fff;
    letter-spacing: -0.3px;
    line-height: 1.1;
  }
  .header-sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: var(--amber);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-top: 4px;
  }
  .header-meta {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: var(--text-dim);
    text-align: right;
  }

  /* Upload Zone */
  .upload-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 32px;
  }
  .upload-card {
    border: 1px dashed var(--border-strong);
    border-radius: 6px;
    padding: 28px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    background: rgba(255,255,255,0.02);
    position: relative;
  }
  .upload-card:hover, .upload-card.drag-over {
    border-color: var(--amber);
    background: rgba(232,160,32,0.05);
  }
  .upload-card.loaded {
    border-style: solid;
    border-color: var(--amber);
    background: rgba(232,160,32,0.04);
  }
  .upload-icon { font-size: 28px; margin-bottom: 10px; }
  .upload-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: var(--amber);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 6px;
  }
  .upload-desc { font-size: 13px; color: var(--text-dim); }
  .upload-file { font-size: 12px; color: var(--amber-light); margin-top: 8px; font-family: 'IBM Plex Mono', monospace; }
  .upload-count { font-size: 11px; color: var(--text-dim); margin-top: 4px; }
  input[type="file"] { display: none; }

  /* Controls */
  .controls {
    display: flex;
    gap: 12px;
    margin-bottom: 28px;
    align-items: center;
    flex-wrap: wrap;
  }
  .search-box {
    flex: 1;
    min-width: 220px;
    background: var(--navy-mid);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 10px 14px;
    color: var(--text);
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
  }
  .search-box:focus { border-color: var(--amber); }
  .search-box::placeholder { color: var(--text-dim); }

  .filter-select {
    background: var(--navy-mid);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 10px 14px;
    color: var(--text);
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 14px;
    outline: none;
    cursor: pointer;
    transition: border-color 0.2s;
  }
  .filter-select:focus { border-color: var(--amber); }

  .btn-analyze {
    background: var(--amber);
    color: var(--navy);
    border: none;
    border-radius: 4px;
    padding: 10px 22px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .btn-analyze:hover { background: var(--amber-light); }
  .btn-analyze:disabled { opacity: 0.4; cursor: not-allowed; }

  /* Stats bar */
  .stats-bar {
    display: flex;
    gap: 1px;
    margin-bottom: 24px;
    background: var(--border);
    border-radius: 6px;
    overflow: hidden;
  }
  .stat-cell {
    flex: 1;
    padding: 14px 18px;
    background: var(--navy-mid);
  }
  .stat-cell:first-child { border-radius: 6px 0 0 6px; }
  .stat-cell:last-child { border-radius: 0 6px 6px 0; }
  .stat-num {
    font-family: 'Playfair Display', serif;
    font-size: 28px;
    font-weight: 700;
    color: #fff;
    line-height: 1;
  }
  .stat-num.red { color: var(--red-light); }
  .stat-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-top: 4px;
  }

  /* Results */
  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
  }
  .section-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--amber);
  }
  .section-count { font-size: 12px; color: var(--text-dim); }

  .result-list { display: flex; flex-direction: column; gap: 8px; }

  .result-row {
    background: var(--navy-mid);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 16px 20px;
    display: grid;
    grid-template-columns: 200px 1fr 140px 120px 100px;
    gap: 16px;
    align-items: center;
    transition: border-color 0.15s;
  }
  .result-row:hover { border-color: rgba(232,160,32,0.4); }
  .result-row.conflict {
    background: var(--conflict);
    border-color: var(--conflict-border);
  }
  .result-row.conflict:hover { border-color: var(--red-light); }

  .col-name {
    font-weight: 500;
    font-size: 14px;
    color: #fff;
  }
  .col-name mark {
    background: rgba(232,160,32,0.3);
    color: var(--amber-light);
    border-radius: 2px;
    padding: 0 2px;
  }
  .col-role { font-size: 13px; color: var(--text-dim); }
  .col-org { font-size: 13px; color: var(--text); }
  .col-date {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: var(--text-dim);
  }
  .conflict-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(192,57,43,0.2);
    border: 1px solid var(--conflict-border);
    border-radius: 3px;
    padding: 4px 8px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: var(--red-light);
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  .clear-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  /* Table header */
  .result-header {
    padding: 10px 20px;
    display: grid;
    grid-template-columns: 200px 1fr 140px 120px 100px;
    gap: 16px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--text-dim);
    border-bottom: 1px solid var(--border);
    margin-bottom: 8px;
  }

  /* Empty state */
  .empty-state {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-dim);
    font-size: 14px;
    border: 1px dashed var(--border);
    border-radius: 6px;
  }
  .empty-icon { font-size: 36px; margin-bottom: 12px; opacity: 0.5; }
  .empty-title { font-family: 'Playfair Display', serif; font-size: 20px; color: var(--text); margin-bottom: 6px; }

  @media (max-width: 768px) {
    .upload-grid { grid-template-columns: 1fr; }
    .result-row, .result-header { grid-template-columns: 1fr 1fr; }
    .col-date, .col-org { display: none; }
  }
`;

// ── CSV parser ──────────────────────────────────────────────
function parseCSV(text) {
  const lines = text.trim().split("\n");
  if (lines.length < 2) return [];
  const headers = lines[0].split(",").map(h => h.trim().replace(/^"|"$/g, "").toLowerCase());
  return lines.slice(1).map((line, i) => {
    const vals = line.split(",").map(v => v.trim().replace(/^"|"$/g, ""));
    const row = { _id: i };
    headers.forEach((h, idx) => { row[h] = vals[idx] || ""; });
    return row;
  });
}

function findField(row, candidates) {
  for (const c of candidates) {
    const key = Object.keys(row).find(k => k.includes(c));
    if (key) return row[key];
  }
  return "";
}

function normalizeRow(row) {
  return {
    _id: row._id,
    name: findField(row, ["name", "employee", "official", "person", "filer"]),
    role: findField(row, ["role", "title", "position", "job"]),
    org: findField(row, ["org", "agency", "department", "company", "employer", "entity"]),
    date: findField(row, ["date", "filed", "period", "year"]),
    raw: row,
  };
}

// Conflict detection: same name appears in both datasets
function detectConflicts(set1, set2) {
  const names2 = new Set(set2.map(r => r.name.toLowerCase().trim()));
  return set1.map(r => ({
    ...r,
    isConflict: names2.has(r.name.toLowerCase().trim()),
  }));
}

function highlight(text, query) {
  if (!query || !text) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark>{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

// ── UploadCard ──────────────────────────────────────────────
function UploadCard({ label, desc, loaded, fileName, count, drag, onDragOver, onDragLeave, onDrop, onChange, id }) {
  return (
    <label
      htmlFor={id}
      className={`upload-card${loaded ? " loaded" : ""}${drag ? " drag-over" : ""}`}
      onDragOver={e => { e.preventDefault(); onDragOver(); }}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <div className="upload-icon">{loaded ? "✅" : "📂"}</div>
      <div className="upload-label">{label}</div>
      <div className="upload-desc">{desc}</div>
      {fileName && <div className="upload-file">{fileName}</div>}
      {count !== undefined && <div className="upload-count">{count} rows</div>}
      {!loaded && <div className="upload-desc" style={{marginTop: 8}}>Click or drag a CSV file here</div>}
      <input type="file" id={id} accept=".csv" onChange={onChange} />
    </label>
  );
}

// ── Main App ────────────────────────────────────────────────
export default function FPCCTool() {
  const [file1, setFile1] = useState(null); // {name, rows}
  const [file2, setFile2] = useState(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [drag1, setDrag1] = useState(false);
  const [drag2, setDrag2] = useState(false);

  const handleFile = useCallback((file, setter) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = e => {
      const rows = parseCSV(e.target.result).map(normalizeRow);
      setter({ name: file.name, rows });
    };
    reader.readAsText(file);
  }, []);

  const results = useMemo(() => {
    if (!file1) return [];
    const base = file2 ? detectConflicts(file1.rows, file2.rows) : file1.rows.map(r => ({ ...r, isConflict: false }));
    return base;
  }, [file1, file2]);

  const filtered = useMemo(() => {
    return results.filter(r => {
      const matchSearch = !search || [r.name, r.role, r.org].some(v => v?.toLowerCase().includes(search.toLowerCase()));
      const matchFilter = filter === "all" || (filter === "conflicts" && r.isConflict) || (filter === "clear" && !r.isConflict);
      return matchSearch && matchFilter;
    });
  }, [results, search, filter]);

  const conflictCount = results.filter(r => r.isConflict).length;

  return (
    <>
      <style>{STYLE}</style>
      <div className="app">
        {/* Header */}
        <header className="header">
          <div className="header-seal">
            <div className="seal-icon">⚖️</div>
            <div>
              <div className="header-title">FPCC Conflict Analyzer</div>
              <div className="header-sub">Fair Political Practices Commission · Conflict of Interest Tool</div>
            </div>
          </div>
          <div className="header-meta">
            {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}<br />
            {file1 ? `${results.length} records loaded` : "No data loaded"}
          </div>
        </header>

        {/* Upload */}
        <div className="upload-grid">
          <UploadCard
            label="Base Dataset"
            desc="Form 700 Information"
            loaded={!!file1}
            fileName={file1?.name}
            count={file1?.rows.length}
            drag={drag1}
            onDragOver={() => setDrag1(true)}
            onDragLeave={() => setDrag1(false)}
            onDrop={e => { e.preventDefault(); setDrag1(false); handleFile(e.dataTransfer.files[0], setFile1); }}
            onChange={e => handleFile(e.target.files[0], setFile1)}
            id="f1"
          />
          <UploadCard
            label="Minutes Dataset"
            desc="Decisions Record"
            loaded={!!file2}
            fileName={file2?.name}
            count={file2?.rows.length}
            drag={drag2}
            onDragOver={() => setDrag2(true)}
            onDragLeave={() => setDrag2(false)}
            onDrop={e => { e.preventDefault(); setDrag2(false); handleFile(e.dataTransfer.files[0], setFile2); }}
            onChange={e => handleFile(e.target.files[0], setFile2)}
            id="f2"
          />
        </div>

        {/* Controls */}
        <div className="controls">
          <input
            className="search-box"
            placeholder="Search by name, role, or organization…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <select className="filter-select" value={filter} onChange={e => setFilter(e.target.value)}>
            <option value="all">All Records</option>
            <option value="conflicts">Conflicts Only</option>
            <option value="clear">Clear Records</option>
          </select>
        </div>

        {/* Stats */}
        {results.length > 0 && (
          <div className="stats-bar">
            <div className="stat-cell">
              <div className="stat-num">{results.length}</div>
              <div className="stat-label">Total Records</div>
            </div>
            <div className="stat-cell">
              <div className="stat-num red">{conflictCount}</div>
              <div className="stat-label">Potential Conflicts</div>
            </div>
            <div className="stat-cell">
              <div className="stat-num">{results.length - conflictCount}</div>
              <div className="stat-label">Clear</div>
            </div>
            <div className="stat-cell">
              <div className="stat-num">{conflictCount > 0 ? ((conflictCount / results.length) * 100).toFixed(1) : 0}%</div>
              <div className="stat-label">Conflict Rate</div>
            </div>
          </div>
        )}

        {/* Results */}
        {file1 ? (
          <>
            <div className="section-header">
              <span className="section-title">
                {filter === "conflicts" ? "⚠ Flagged Records" : filter === "clear" ? "✓ Clear Records" : "All Records"}
              </span>
              <span className="section-count">{filtered.length} shown</span>
            </div>
            <div className="result-header">
              <span>Name</span>
              <span>Role</span>
              <span>Organization</span>
              <span>Date</span>
              <span>Status</span>
            </div>
            <div className="result-list">
              {filtered.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">🔍</div>
                  <div className="empty-title">No matching records</div>
                  <div>Try adjusting your search or filter</div>
                </div>
              ) : filtered.map(r => (
                <div key={r._id} className={`result-row${r.isConflict ? " conflict" : ""}`}>
                  <div className="col-name">{highlight(r.name || "—", search)}</div>
                  <div className="col-role">{highlight(r.role || "—", search)}</div>
                  <div className="col-org">{highlight(r.org || "—", search)}</div>
                  <div className="col-date">{r.date || "—"}</div>
                  <div>
                    {r.isConflict
                      ? <span className="conflict-badge">⚠ Conflict</span>
                      : <span className="clear-badge">✓ Clear</span>
                    }
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <div className="empty-title">Upload a CSV to begin</div>
            <div>Drop a CSV file into the Primary Dataset slot above to start analyzing records</div>
          </div>
        )}
      </div>
    </>
  );
}
