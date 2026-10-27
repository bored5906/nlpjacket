// ============ 1. CONFIG ============
const CONFIG = { USE_MOCK: false, API: "/api", MAX_HISTORY: 500 };

// ============ 2. HELPERS ============
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} }
};

// ============ 3. STATE ============
const S = {
  tabs: [], active: null, nextId: 1, resultTab: "summary",
  history: store.get("pl_history", []),
  settings: store.get("pl_settings", { mode: "compare", length: "medium", theme: "light" })
};

// ============ 4. API LAYER ============
const api = {
  async process(tab, options) {
    const fd = new FormData();
    if (tab.file) fd.append("file", tab.file); else fd.append("arxiv", tab.arxiv);
    fd.append("options", JSON.stringify(options));
    const res = await fetch(CONFIG.API + "/process", { method: "POST", body: fd });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || "Server error " + res.status);
    return res.json();
  }
};

// ============ 5. RESULT RENDERERS ============
const bars = (rows, max) => rows.map(([name, v]) =>
  `<div class="bar-row"><span>${esc(name)}</span><div class="bar"><i style="width:${Math.min(100, v / max * 100)}%"></i></div><span>${(+v).toFixed(2)}</span></div>`).join("");
const card = (title, body) => `<div class="rcard"><h3>${esc(title)}</h3>${body}</div>`;
const NAMES = { lead: "Lead baseline", "TF-IDF": "TF-IDF", "TextRank": "TextRank" };

const RENDERERS = {
  summary: { label: "Summary", render: r => `<div class="cols">${Object.entries(r.summaries || {}).map(
    ([k, t]) => `<div><h3>${esc(NAMES[k] || k)}</h3><p>${esc(t)}</p></div>`).join("")}</div>` },
  insights: { label: "Key insights", render: r => Object.entries(r.insights || {}).map(
    ([k, t]) => card(k[0].toUpperCase() + k.slice(1), `<p>${esc(t) || '<span class="muted">Not found in this paper.</span>'}</p>`)).join("") },
  keywords: { label: "Keywords", render: r => bars((r.keywords || []).map(k => [k.term, k.score]), Math.max(...(r.keywords || []).map(k => k.score), 0.01)) },
  entities: { label: "Entities", render: r => Object.entries(r.entities || {}).map(
    ([type, list]) => card(type, `<div class="chips">${list.map(e => `<span>${esc(e)}</span>`).join("") || '<span class="muted">None found</span>'}</div>`)).join("") },
  sections: { label: "Sections", render: r => Object.entries(r.sections || {}).map(([k, t]) => card(k, `<p>${esc(t)}</p>`)).join("") },
  trace: { label: "Pipeline trace", render: r => `<table><tr><th>Stage</th><th>Time (ms)</th><th>Output preview</th></tr>${(r.trace || []).map(
    t => `<tr><td>${esc(t.stage)}</td><td>${esc(t.ms)}</td><td>${esc(t.output_preview)}</td></tr>`).join("")}</table>` },
  
  // Updated Evaluation Tab: Now renders comparison table and the dynamically generated graph
  evaluation: { label: "Evaluation", render: r => {
    const ev = r.evaluation || {};
    const ts = new Date().getTime(); // Cache buster to force image reload on new processing
    return `<table><tr><th>Method</th><th>ROUGE-1</th><th>ROUGE-2</th><th>ROUGE-L</th></tr>${Object.entries(ev).map(
      ([m, v]) => `<tr><td><strong>${esc(NAMES[m] || m)}</strong></td><td>${v['ROUGE-1']}</td><td>${v['ROUGE-2']}</td><td>${v['ROUGE-L']}</td></tr>`).join("")}</table>
      <div style="margin-top: 25px; text-align: center; background: #fff; padding: 15px; border-radius: 8px; border: 1px solid #eaeaea;">
        <h4 style="margin-bottom: 10px;">Visual Comparison</h4>
        <img src="/results/graphs/rouge_comparison.png?t=${ts}" onerror="this.style.display='none'" alt="ROUGE Comparison Graph" style="max-width: 100%; height: auto;"/>
      </div>
      <p class="muted" style="margin-top:10px">ROUGE F1 scores evaluated against the paper's original abstract.</p>`; } }
};

// ============ 6. TABS ============
const activeTab = () => S.tabs.find(t => t.id === S.active);
function addTab() {
  const id = S.nextId++;
  S.tabs.push({ id, title: `Paper ${id}: new`, file: null, arxiv: "", result: null });
  S.active = id; renderAll();
}
function closeTab(id) {
  if (S.tabs.length === 1) { S.tabs = []; return addTab(); }
  S.tabs = S.tabs.filter(t => t.id !== id);
  if (S.active === id) S.active = S.tabs[S.tabs.length - 1].id;
  renderAll();
}
function renderTabs() {
  $("tabs").innerHTML = S.tabs.map(t => `<div class="tab ${t.id === S.active ? "active" : ""}" data-id="${t.id}">
    <span class="tab-title">${esc(t.title)}</span><button class="tab-close" data-close="${t.id}" aria-label="Close tab">×</button></div>`).join("");
}
$("tabs").addEventListener("click", e => {
  if (e.target.dataset.close) return closeTab(+e.target.dataset.close);
  const el = e.target.closest(".tab");
  if (el) { S.active = +el.dataset.id; renderAll(); }
});
$("newTabBtn").addEventListener("click", addTab);

// ============ 7. INPUT AREA ============
function status(msg, isError = false) { $("status").textContent = msg; $("status").className = "status" + (isError ? " error" : ""); }
function renderInput() {
  const t = activeTab();
  $("dropzone").classList.toggle("has-file", !!t.file);
  $("fileName").textContent = t.file ? "Selected: " + t.file.name : "Text-based PDF files only";
  $("arxivInput").value = t.arxiv;
}
function setFile(file) {
  if (!file || file.type !== "application/pdf") return status("Choose a PDF file.", true);
  const t = activeTab(); t.file = file; t.arxiv = ""; t.title = `Paper ${t.id}: ${file.name.replace(/\.pdf$/i, "")}`;
  log("Upload", file.name); status(""); renderAll();
}
function clearInput() {
  const t = activeTab(); t.file = null; t.arxiv = ""; t.result = null; $("fileInput").value = "";
  status(""); renderAll();
}
$("dropzone").addEventListener("click", () => $("fileInput").click());
$("dropzone").addEventListener("keydown", e => { if (e.key === "Enter") $("fileInput").click(); });
$("uploadBtn").addEventListener("click", () => $("fileInput").click());
$("fileInput").addEventListener("change", e => setFile(e.target.files[0]));
$("dropzone").addEventListener("dragover", e => { e.preventDefault(); $("dropzone").classList.add("drag"); });
$("dropzone").addEventListener("dragleave", () => $("dropzone").classList.remove("drag"));
$("dropzone").addEventListener("drop", e => { e.preventDefault(); $("dropzone").classList.remove("drag"); setFile(e.dataTransfer.files[0]); });
$("clearBtn").addEventListener("click", clearInput);
$("arxivInput").addEventListener("input", e => { const t = activeTab(); t.arxiv = e.target.value.trim(); if (t.arxiv) t.file = null; });

// ============ 8. PROCESS ============
const pick = name => document.querySelector(`input[name="${name}"]:checked`).value;
async function processPaper() {
  const t = activeTab();
  if (!t.file && !t.arxiv) return status("Add a PDF or an arXiv ID first.", true);
  const options = { mode: pick("mode"), length: pick("length"), normalization: $("normSelect").value, ngram: $("ngramSelect").value };
  const started = performance.now();
  $("processBtn").disabled = true; $("progress").classList.remove("hidden"); $("progressBar").style.width = "15%";
  status("Processing…");
  const tick = setInterval(() => { const w = parseFloat($("progressBar").style.width); if (w < 90) $("progressBar").style.width = w + 7 + "%"; }, 400);
  try {
    t.result = await api.process(t, options);
    if (t.result.title) t.title = t.result.title;
    log("Process", `${t.title} | ${options.mode}/${options.length}`, "ok", Math.round(performance.now() - started));
    status("Done."); renderAll();
  } catch (err) {
    log("Process", t.title, "error: " + err.message); status(err.message, true);
  } finally {
    clearInterval(tick); $("progressBar").style.width = "100%";
    setTimeout(() => $("progress").classList.add("hidden"), 500); $("processBtn").disabled = false;
  }
}
$("processBtn").addEventListener("click", processPaper);

// ============ 9. RESULTS ============
function renderResults() {
  const r = activeTab().result;
  $("results").classList.toggle("hidden", !r);
  if (!r) return;
  $("rtabs").innerHTML = Object.entries(RENDERERS).map(([k, v]) =>
    `<button class="rtab ${k === S.resultTab ? "active" : ""}" data-r="${k}">${v.label}</button>`).join("");
  $("rbody").innerHTML = RENDERERS[S.resultTab].render(r);
}
$("rtabs").addEventListener("click", e => { if (e.target.dataset.r) { S.resultTab = e.target.dataset.r; renderResults(); } });

// ============ 10. HISTORY (Local memory only) ============
function log(event, detail, outcome = "ok", ms = "") {
  S.history.unshift({ time: new Date().toLocaleString(), event, detail, outcome, ms });
  S.history = S.history.slice(0, CONFIG.MAX_HISTORY); store.set("pl_history", S.history); renderHistory();
}
function renderHistory() {
  $("historyBody").innerHTML = S.history.length
    ? `<table><tr><th>Time</th><th>Event</th><th>Detail</th><th>Status</th><th>ms</th></tr>${S.history.map(h =>
        `<tr><td>${esc(h.time)}</td><td>${esc(h.event)}</td><td>${esc(h.detail)}</td><td>${esc(h.outcome)}</td><td>${esc(h.ms)}</td></tr>`).join("")}</table>`
    : `<p class="muted">Nothing here yet. Process a paper and it will appear.</p>`;
}
$("clearHistoryBtn").addEventListener("click", () => { S.history = []; store.set("pl_history", []); renderHistory(); });

// ============ 11. SETTINGS + NAV ============
function applySettings() {
  document.documentElement.dataset.theme = S.settings.theme;
  $("setMode").value = S.settings.mode; $("setLength").value = S.settings.length; $("setTheme").value = S.settings.theme;
}
[["setMode", "mode"], ["setLength", "length"], ["setTheme", "theme"]].forEach(([id, key]) =>
  $(id).addEventListener("change", e => { S.settings[key] = e.target.value; store.set("pl_settings", S.settings); applySettings(); }));
document.querySelectorAll(".nav-link").forEach(btn => btn.addEventListener("click", () => {
  document.querySelectorAll(".nav-link").forEach(b => b.classList.toggle("active", b === btn));
  document.querySelectorAll(".view").forEach(v => v.classList.toggle("hidden", v.id !== "view-" + btn.dataset.view));
}));

// ============ 12. START ============
function renderAll() { renderTabs(); renderInput(); renderResults(); }
document.querySelector(`input[name="mode"][value="${S.settings.mode}"]`) ? document.querySelector(`input[name="mode"][value="${S.settings.mode}"]`).checked = true : null;
document.querySelector(`input[name="length"][value="${S.settings.length}"]`) ? document.querySelector(`input[name="length"][value="${S.settings.length}"]`).checked = true : null;
applySettings(); renderHistory(); addTab();