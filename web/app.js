/* RNAlyst Application Controller (Figma Make Frontend Contract) */

let currentProjectId = null;
let currentAnalysisId = null;
let activeGalleryArtifacts = [];
let activeGalleryIndex = 0;
let attachedFiles = [];
let pendingUploadFiles = [];

document.addEventListener("DOMContentLoaded", () => {
  initApp();
});

function initApp() {
  bindEvents();
  loadActiveProjects();
  loadRecentAnalyses();
}

function bindEvents() {
  // Navigation & Reset
  const brandBtn = document.getElementById("nav-brand-btn");
  if (brandBtn) {
    brandBtn.addEventListener("click", showLandingView);
  }

  // Landing Query
  const landingInput = document.getElementById("landing-query-input");
  const landingSend = document.getElementById("landing-send-btn");
  if (landingSend) {
    landingSend.addEventListener("click", () => submitQuery(landingInput.value));
  }
  if (landingInput) {
    landingInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") submitQuery(landingInput.value);
    });
  }

  // Bottom Sticky Query
  const bottomInput = document.getElementById("bottom-query-input");
  const bottomSend = document.getElementById("bottom-send-btn");
  if (bottomSend) {
    bottomSend.addEventListener("click", () => submitQuery(bottomInput.value));
  }
  if (bottomInput) {
    bottomInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") submitQuery(bottomInput.value);
    });
  }

  // Example Pills
  document.querySelectorAll(".example-pill").forEach(pill => {
    pill.addEventListener("click", () => {
      const q = pill.getAttribute("data-query");
      if (q) submitQuery(q);
    });
  });

  // Dropzone & File Input
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const startUploadBtn = document.getElementById("start-upload-btn");

  if (dropZone && fileInput) {
    fileInput.addEventListener("click", (e) => e.stopPropagation());
    dropZone.addEventListener("click", (e) => {
      if (e.target !== fileInput && e.target !== startUploadBtn) fileInput.click();
    });
    dropZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropZone.classList.add("dragging");
    });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragging"));
    dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragging");
      if (e.dataTransfer.files.length > 0) {
        handleFileSelection(e.dataTransfer.files);
      }
    });
    fileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        handleFileSelection(e.target.files);
      }
    });
  }

  if (startUploadBtn) {
    startUploadBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      uploadPendingFiles();
    });
  }

  // Trace Drawer Toggle
  const toggleTraceBtn = document.getElementById("toggle-trace-btn");
  const traceDrawer = document.getElementById("trace-drawer");
  if (toggleTraceBtn && traceDrawer) {
    toggleTraceBtn.addEventListener("click", () => {
      const isHidden = traceDrawer.style.display === "none";
      traceDrawer.style.display = isHidden ? "block" : "none";
      toggleTraceBtn.textContent = isHidden ? "Hide details" : "Analysis details";
    });
  }

  // Lightbox Modal Controls
  const closeBtn = document.getElementById("close-fig-modal-btn");
  const modal = document.getElementById("fig-modal");
  const prevBtn = document.getElementById("prev-fig-btn");
  const nextBtn = document.getElementById("next-fig-btn");

  if (closeBtn) closeBtn.addEventListener("click", closeLightbox);
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeLightbox();
    });
  }
  if (prevBtn) prevBtn.addEventListener("click", navigatePrevLightbox);
  if (nextBtn) nextBtn.addEventListener("click", navigateNextLightbox);

  document.addEventListener("keydown", (e) => {
    if (!modal || modal.style.display === "none") return;
    if (e.key === "Escape") closeLightbox();
    if (e.key === "ArrowLeft") navigatePrevLightbox();
    if (e.key === "ArrowRight") navigateNextLightbox();
  });

  // Event Delegation for Visualization Gallery Cards
  const stream = document.getElementById("chat-stream");
  if (stream) {
    stream.addEventListener("click", (e) => {
      const card = e.target.closest(".visualization-card");
      if (card) {
        const idx = parseInt(card.getAttribute("data-gallery-index"), 10);
        if (!isNaN(idx)) openLightboxAtIndex(idx);
      }
    });
  }

  // Event Delegation for Active Sidebar Projects Selection
  const projectsList = document.getElementById("active-projects-list");
  if (projectsList) {
    projectsList.addEventListener("click", (e) => {
      const projCard = e.target.closest(".project-card");
      if (projCard) {
        const pid = projCard.getAttribute("data-project-id");
        if (pid) {
          currentProjectId = pid;
          loadActiveProjects();
        }
      }
    });
  }
}

function showLandingView() {
  document.getElementById("landing-view").style.display = "flex";
  document.getElementById("results-view").style.display = "none";
}

function showResultsView() {
  document.getElementById("landing-view").style.display = "none";
  document.getElementById("results-view").style.display = "flex";
}

async function loadActiveProjects() {
  const listEl = document.getElementById("active-projects-list");
  try {
    const res = await fetch("/api/v1/projects");
    if (!res.ok) return;
    const data = await res.json();
    const projects = Array.isArray(data) ? data : (data.projects || []);
    if (projects.length === 0) {
      listEl.innerHTML = '<div style="font-size: 11px; color: var(--muted); font-style: italic;">No active projects loaded.</div>';
      return;
    }
    listEl.innerHTML = projects.map(p => `
      <div class="project-card ${p.project_id === currentProjectId ? 'active' : ''}" data-project-id="${p.project_id}">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px;">
          <span style="font-size: 12px; font-weight: 600; color: var(--charcoal);">${escapeHtml(p.project_id)}</span>
          ${p.project_id === currentProjectId ? '<span style="width: 6px; height: 6px; border-radius: 50%; background: var(--steel); display: inline-block;"></span>' : ''}
        </div>
        <div style="font-size: 10px; color: var(--muted); font-style: italic;">${escapeHtml(p.organism || 'Custom Project')}</div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Failed to load active projects:", err);
  }
}

async function loadRecentAnalyses() {
  const listEl = document.getElementById("recent-analyses-list");
  try {
    const res = await fetch("/api/v1/analyses");
    if (!res.ok) return;
    const data = await res.json();
    const analyses = Array.isArray(data) ? data : (data.analyses || []);
    if (analyses.length === 0) {
      listEl.innerHTML = '<div style="font-size: 11px; color: var(--muted); font-style: italic;">No recent analyses.</div>';
      return;
    }
    listEl.innerHTML = analyses.map(a => `
      <div class="recent-analysis-item" data-analysis-id="${a.analysis_id}">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <span style="font-size: 11px; color: var(--charcoal); font-weight: 500;">${escapeHtml(a.analysis_id)}</span>
          <span style="font-size: 10px; color: var(--muted);">${escapeHtml(a.status || 'Done')}</span>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Failed to load recent analyses:", err);
  }
}

async function handleFileUpload(files) {
  await handleFileSelection(files);
}

async function handleFileSelection(files) {
  const textEl = document.getElementById("dropzone-text");
  const startUploadBtn = document.getElementById("start-upload-btn");
  const fileInput = document.getElementById("file-input");
  const fileArr = Array.from(files);
  if (fileArr.length === 0) return;

  // Check if uploading CSV sample-sheet metadata vs FASTQ
  if (fileArr.length === 1 && fileArr[0].name.toLowerCase().endsWith(".csv") && currentProjectId) {
    await handleMetadataCsvUpload(fileArr[0]);
    if (fileInput) fileInput.value = "";
    return;
  }

  // Accumulate files in pendingUploadFiles (prevent duplicates by name + size)
  fileArr.forEach(f => {
    if (!pendingUploadFiles.some(p => p.name === f.name && p.size === f.size)) {
      pendingUploadFiles.push(f);
    }
  });

  if (textEl) {
    textEl.textContent = `Attached: ${pendingUploadFiles.length} file(s) selected — Click 'Upload FASTQ Files' to submit.`;
  }
  if (startUploadBtn) {
    startUploadBtn.style.display = "inline-block";
    startUploadBtn.textContent = `Upload ${pendingUploadFiles.length} File(s)`;
  }
  if (fileInput) {
    fileInput.value = "";
  }
}

async function uploadPendingFiles() {
  const textEl = document.getElementById("dropzone-text");
  const dropZone = document.getElementById("drop-zone");
  const startUploadBtn = document.getElementById("start-upload-btn");

  if (pendingUploadFiles.length === 0) return;
  if (dropZone) dropZone.classList.add("uploading");
  if (textEl) textEl.textContent = `Uploading ${pendingUploadFiles.length} file(s)…`;

  const formData = new FormData();
  if (currentProjectId) {
    formData.append("project_id", currentProjectId);
  }
  pendingUploadFiles.forEach(f => {
    formData.append("files", f);
    formData.append("file", f);
  });

  try {
    const res = await fetch("/api/v1/qc", { method: "POST", body: formData });

    if (!res.ok) {
      let errDetail = `Server returned HTTP ${res.status}`;
      try {
        const err = await res.json();
        if (err.detail) errDetail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
      } catch (e) {}
      alert(`Upload failed: ${errDetail}`);
      if (textEl) textEl.textContent = "Attach FASTQ files or drop them here";
      return;
    }

    const data = await res.json();

    if (!data || (data.status !== "completed" && !data.file_id) || data.validation?.is_valid === false) {
      const valErr = data.validation?.error || data.detail || "Invalid FASTQ file or backend validation failed.";
      alert(`Upload rejected: ${valErr}`);
      if (textEl) textEl.textContent = "Attach FASTQ files or drop them here";
      return;
    }

    pendingUploadFiles.forEach(f => {
      if (!attachedFiles.includes(f.name)) attachedFiles.push(f.name);
    });
    if (data.project_id || data.file_id) {
      currentProjectId = data.project_id || data.file_id;
    }

    const totalFiles = data.files_count || data.files?.length || pendingUploadFiles.length;
    const samplesCount = data.samples_count || (data.samples ? data.samples.length : 1);
    const layoutStr = data.samples && data.samples.some(s => s.layout === 'PAIRED') ? 'paired-end' : 'single-end';

    if (textEl) {
      textEl.textContent = `Attached: ${totalFiles} file(s) → ${samplesCount} ${layoutStr} sample(s)`;
    }

    pendingUploadFiles = [];
    if (startUploadBtn) startUploadBtn.style.display = "none";

    await loadActiveProjects();
    await loadRecentAnalyses();

  } catch (err) {
    console.error("Upload error:", err);
    alert(`Upload network error: ${err.message || err}`);
    if (textEl) textEl.textContent = "Attach FASTQ files or drop them here";
  } finally {
    if (dropZone) dropZone.classList.remove("uploading");
  }
}

async function submitQuery(queryString) {
  if (!queryString || !queryString.trim()) return;
  const q = queryString.trim();

  // Require active project/dataset context — NO synthetic/benchmark fallbacks!
  if (!currentProjectId) {
    showResultsView();
    renderErrorState("No active project or dataset selected. Please attach FASTQ files or select a project from the sidebar before submitting a query.");
    return;
  }

  // Switch to Results view
  showResultsView();

  // Reset/Clear UI state
  document.getElementById("landing-query-input").value = "";
  document.getElementById("bottom-query-input").value = "";
  document.getElementById("res-analysis-title").textContent = `Query: "${q.length > 35 ? q.substring(0, 35) + '…' : q}"`;
  
  const statusBarBadges = document.getElementById("status-badges");
  statusBarBadges.innerHTML = '<span>● Dispatching Gemini LLM request…</span>';
  document.getElementById("status-dot").style.background = "#D95F02";
  document.getElementById("status-text").textContent = "Executing Scientific Pipeline…";

  // Hide optional sections
  document.getElementById("exec-summary-section").style.display = "none";
  document.getElementById("interpretation-section").style.display = "none";
  document.getElementById("viz-gallery-section").style.display = "none";
  document.getElementById("three-col-section").style.display = "none";
  document.getElementById("deg-panel").style.display = "none";
  document.getElementById("insights-panel").style.display = "none";
  document.getElementById("pathways-panel").style.display = "none";

  const payload = {
    query: q,
    dataset_id: currentProjectId,
    session_id: currentAnalysisId || null
  };

  try {
    const res = await fetch("/api/v1/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const errData = await res.json();
      renderErrorState(errData.detail || `Server returned HTTP ${res.status}`);
      return;
    }

    const data = await res.json();
    renderAgentResponse(data);

  } catch (err) {
    console.error("Query API error:", err);
    renderErrorState(err.message || "Failed to reach backend server.");
  }
}

function renderErrorState(errorMsg) {
  let displayMsg = "";
  if (Array.isArray(errorMsg)) {
    displayMsg = errorMsg.map(e => e.msg || e.detail || (typeof e === "object" ? JSON.stringify(e) : String(e))).join("; ");
  } else if (typeof errorMsg === "object" && errorMsg !== null) {
    displayMsg = errorMsg.msg || errorMsg.detail || errorMsg.message || JSON.stringify(errorMsg);
  } else {
    displayMsg = String(errorMsg);
  }

  document.getElementById("status-dot").style.background = "#D95F02";
  document.getElementById("status-text").textContent = "Execution Failed";
  document.getElementById("status-badges").innerHTML = `<span style="color: #D95F02;">✖ ${escapeHtml(displayMsg)}</span>`;
  
  const interpSection = document.getElementById("interpretation-section");
  interpSection.style.display = "block";
  document.getElementById("interpretation-text").innerHTML = `
    <div style="color: #D95F02; font-weight: 600; margin-bottom: 6px;">[EXECUTION ERROR]</div>
    <div>${escapeHtml(displayMsg)}</div>
  `;
}

function renderAgentResponse(resp) {
  if (resp && resp.success === false) {
    renderErrorState(resp.message || "Query execution failed.");
    return;
  }

  currentProjectId = resp.project_id || currentProjectId;
  currentAnalysisId = resp.analysis_id || currentAnalysisId;

  // Status Bar
  document.getElementById("status-dot").style.background = "#6F887C";
  document.getElementById("status-text").textContent = "Analysis Complete";
  
  const steps = resp.requested_outputs || ["QC", "Differential Expression", "Synthesis"];
  document.getElementById("status-badges").innerHTML = steps.map(s => `<span>✓ ${escapeHtml(s)}</span>`).join("");

  // Trace Logs
  if (resp.trace_logs || resp.execution_trace) {
    const traceArr = resp.trace_logs || resp.execution_trace || [];
    document.getElementById("trace-logs-container").innerHTML = traceArr.map(t => `<div>● ${escapeHtml(typeof t === 'string' ? t : JSON.stringify(t))}</div>`).join("");
  }

  // Executive Summary Metrics (if available in artifacts or summary)
  if (resp.de_results || resp.summary_metrics) {
    const metrics = resp.summary_metrics || {};
    const totalG = metrics.total_genes || resp.total_genes || "N/A";
    const degs = metrics.deg_count || resp.deg_count || "N/A";
    const up = metrics.upregulated || resp.upregulated || "N/A";
    const down = metrics.downregulated || resp.downregulated || "N/A";

    document.getElementById("exec-metrics-container").innerHTML = `
      <div class="metric-card"><div style="font-size: 10px; color: var(--muted); text-transform: uppercase;">Total Genes</div><div class="font-serif" style="font-size: 28px;">${totalG}</div></div>
      <div class="metric-card"><div style="font-size: 10px; color: var(--muted); text-transform: uppercase;">DEGs (padj < 0.05)</div><div class="font-serif" style="font-size: 28px;">${degs}</div></div>
      <div class="metric-card"><div style="font-size: 10px; color: var(--muted); text-transform: uppercase;">Upregulated</div><div class="font-serif" style="font-size: 28px; color: var(--steel);">${up}</div></div>
      <div class="metric-card"><div style="font-size: 10px; color: var(--muted); text-transform: uppercase;">Downregulated</div><div class="font-serif" style="font-size: 28px; color: var(--steel-dark);">${down}</div></div>
    `;
    document.getElementById("exec-summary-section").style.display = "block";
  }

  // Interpretation Text
  const interpText = resp.message || "No synthesis text returned.";
  if (typeof marked !== "undefined" && typeof marked.parse === "function") {
    document.getElementById("interpretation-text").innerHTML = marked.parse(interpText);
  } else {
    document.getElementById("interpretation-text").innerHTML = escapeHtml(interpText).replace(/\n/g, "<br>");
  }
  document.getElementById("interpretation-section").style.display = "block";

  // Visualizations Gallery
  activeGalleryArtifacts = [];
  const artifacts = resp.artifacts || resp.generated_artifacts || [];
  const plotArtifacts = artifacts.filter(a => a.artifact_type === "plot" || a.type === "plot" || (a.path && a.path.endsWith(".png")));

  if (plotArtifacts.length > 0) {
    activeGalleryArtifacts = plotArtifacts.map(a => {
      const filename = a.name || (a.path ? a.path.split("/").pop().split("\\").pop() : "plot.png");
      const relativeUrl = `/api/v1/analyses/artifacts/${filename}?analysis_id=${resp.analysis_id || ''}`;
      return {
        title: a.title || filename.replace(".png", "").replace(/_/g, " ").toUpperCase(),
        subtitle: a.subtitle || "Scientific Plot",
        url: relativeUrl,
        interp: a.interpretation || "Quantitative visualization derived from current user dataset."
      };
    });

    const vizGrid = document.getElementById("viz-gallery-grid");
    vizGrid.innerHTML = activeGalleryArtifacts.map((item, idx) => `
      <div class="visualization-card" data-gallery-index="${idx}">
        <div style="padding: 12px 12px 8px;">
          <div style="font-size: 10px; color: var(--border); font-weight: 600;">0${idx + 1}</div>
          <div style="font-size: 12px; font-weight: 600; color: var(--charcoal);">${escapeHtml(item.title)}</div>
        </div>
        <div style="height: 140px; padding: 0 6px 8px; overflow: hidden; display: flex; align-items: center; justify-content: center; background: #faf8f5;">
          <img src="${item.url}" alt="${escapeHtml(item.title)}" style="max-height: 100%; max-width: 100%; object-fit: contain;" onerror="this.onerror=null; this.parentElement.innerHTML='<span style=\'font-size:10px; color:var(--muted);\'>[PLOT GENERATED]</span>';" />
        </div>
      </div>
    `).join("");

    document.getElementById("viz-gallery-section").style.display = "block";
  }

  // DEG Table
  if (resp.de_results && Array.isArray(resp.de_results) && resp.de_results.length > 0) {
    const degRows = resp.de_results.slice(0, 10);
    document.getElementById("deg-table-container").innerHTML = `
      <table style="width: 100%; border-collapse: collapse;">
        <thead>
          <tr>
            <th style="text-align: left; font-size: 10px; color: var(--muted); padding-bottom: 6px;">Gene ID</th>
            <th style="text-align: left; font-size: 10px; color: var(--muted); padding-bottom: 6px;">log2FC</th>
            <th style="text-align: left; font-size: 10px; color: var(--muted); padding-bottom: 6px;">padj</th>
          </tr>
        </thead>
        <tbody>
          ${degRows.map(r => `
            <tr style="border-top: 1px solid var(--border);">
              <td style="padding: 6px 0; font-size: 11px; font-weight: 600;">${escapeHtml(r.gene_id || r.gene || '')}</td>
              <td style="font-size: 11px; color: ${(r.log2FoldChange || 0) > 0 ? 'var(--steel)' : 'var(--steel-dark)'};">${r.log2FoldChange ? (r.log2FoldChange > 0 ? '+' : '') + Number(r.log2FoldChange).toFixed(2) : 'N/A'}</td>
              <td style="font-size: 11px; color: var(--muted);">${r.padj ? Number(r.padj).toExponential(2) : 'N/A'}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
    document.getElementById("deg-panel").style.display = "block";
    document.getElementById("three-col-section").style.display = "grid";
  }

  // Biological Insights
  if (resp.biological_insights && Array.isArray(resp.biological_insights) && resp.biological_insights.length > 0) {
    document.getElementById("insights-list").innerHTML = resp.biological_insights.map(ins => `
      <div style="display: flex; gap: 8px; align-items: flex-start;">
        <span style="color: var(--steel);">•</span>
        <span style="font-size: 12px; color: var(--charcoal);">${escapeHtml(typeof ins === 'string' ? ins : ins.summary || '')}</span>
      </div>
    `).join("");
    document.getElementById("insights-panel").style.display = "block";
    document.getElementById("three-col-section").style.display = "grid";
  }

  // Pathways
  if (resp.pathway_enrichment && Array.isArray(resp.pathway_enrichment) && resp.pathway_enrichment.length > 0) {
    document.getElementById("pathways-list").innerHTML = resp.pathway_enrichment.map(p => `
      <div style="border-bottom: 1px solid var(--border); padding-bottom: 8px;">
        <div style="font-size: 11px; font-weight: 600; color: var(--charcoal);">${escapeHtml(p.name || p.pathway || '')}</div>
        <div style="display: flex; gap: 8px; margin-top: 2px;">
          <span style="font-size: 10px; color: var(--muted);">${escapeHtml(p.id || p.db || '')}</span>
          <span style="font-size: 10px; color: var(--muted);">p=${p.padj || p.pvalue || 'N/A'}</span>
        </div>
      </div>
    `).join("");
    document.getElementById("pathways-panel").style.display = "block";
    document.getElementById("three-col-section").style.display = "grid";
  }

  // Literature Evidence Panel
  renderLiteraturePanel(resp.literature_results || resp.literature_citations || []);
}

function renderLiteraturePanel(papers) {
  const listEl = document.getElementById("literature-cards-list");
  const countBadge = document.getElementById("lit-count-badge");
  countBadge.textContent = `${papers.length} paper${papers.length === 1 ? '' : 's'}`;

  if (!papers || papers.length === 0) {
    listEl.innerHTML = '<div style="font-size: 12px; color: var(--muted); font-style: italic;">No literature evidence returned for current request.</div>';
    return;
  }

  listEl.innerHTML = papers.map(p => `
    <div class="paper-card">
      <div style="font-size: 12px; font-weight: 600; color: var(--charcoal); line-height: 1.4; margin-bottom: 6px;">${escapeHtml(p.title || 'Scientific Paper')}</div>
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
        ${p.pmid ? `<span style="font-size: 10px; color: var(--muted);">PMID: ${escapeHtml(p.pmid)}</span>` : ''}
        ${p.year ? `<span style="font-size: 10px; color: var(--muted);">${escapeHtml(p.year)}</span>` : ''}
      </div>
      <p style="font-size: 11px; color: var(--muted); line-height: 1.55; margin: 0;">${escapeHtml(p.summary || p.abstract || '')}</p>
    </div>
  `).join("");
}

// Lightbox functions
function openLightboxAtIndex(index) {
  if (!activeGalleryArtifacts || index < 0 || index >= activeGalleryArtifacts.length) return;
  activeGalleryIndex = index;
  const item = activeGalleryArtifacts[index];

  document.getElementById("modal-title").textContent = item.title;
  document.getElementById("modal-subtitle").textContent = item.subtitle;
  document.getElementById("modal-interp").textContent = item.interp;
  document.getElementById("modal-counter-badge").textContent = `Figure ${index + 1} of ${activeGalleryArtifacts.length}`;

  const img = document.getElementById("modal-image");
  const errBlock = document.getElementById("modal-error-block");
  
  img.style.display = "block";
  errBlock.style.display = "none";

  img.onerror = () => {
    img.style.display = "none";
    errBlock.style.display = "block";
  };
  img.src = item.url;

  document.getElementById("fig-modal").style.display = "flex";
}

function closeLightbox() {
  document.getElementById("fig-modal").style.display = "none";
}

function navigatePrevLightbox() {
  if (activeGalleryArtifacts.length === 0) return;
  const newIdx = (activeGalleryIndex - 1 + activeGalleryArtifacts.length) % activeGalleryArtifacts.length;
  openLightboxAtIndex(newIdx);
}

function navigateNextLightbox() {
  if (activeGalleryArtifacts.length === 0) return;
  const newIdx = (activeGalleryIndex + 1) % activeGalleryArtifacts.length;
  openLightboxAtIndex(newIdx);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}


async function handleMetadataCsvUpload(file) {
  if (!currentProjectId) {
    alert("Please upload FASTQ files first to establish project context.");
    return;
  }
  const textEl = document.getElementById("dropzone-text");
  if (textEl) textEl.textContent = "Uploading metadata CSV…";
  const formData = new FormData();
  formData.append("file", file);
  try {
    const res = await fetch(`/api/v1/projects/${currentProjectId}/metadata/csv`, { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json();
      alert(`Metadata assignment failed: ${err.detail || 'CSV parse error'}`);
      if (textEl) textEl.textContent = "Attach FASTQ files or drop them here";
      return;
    }
    const data = await res.json();
    alert(`Successfully imported sample metadata for project ${currentProjectId}!`);
    if (textEl) textEl.textContent = `Metadata imported (${data.manifest?.samples?.length || 0} samples)`;
    await loadActiveProjects();
  } catch (e) {
    alert(`CSV import error: ${e.message || e}`);
  }
}
