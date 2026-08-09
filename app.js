document.addEventListener("DOMContentLoaded", () => {
  const socket = io();
  let scripts = [];
  let currentLogScript = "";

  // ── Elements ──
  const views = document.querySelectorAll(".view");
  const navItems = document.querySelectorAll(".nav-item");
  const scriptCards = document.getElementById("scriptCards");
  const scriptTableBody = document.getElementById("scriptTableBody");
  const logPanel = document.getElementById("logPanel");
  const logScriptSelect = document.getElementById("logScriptSelect");
  const pageTitle = document.getElementById("pageTitle");

  // Stats
  const countRunning = document.getElementById("countRunning");
  const countStopped = document.getElementById("countStopped");
  const countError = document.getElementById("countError");
  const countTotal = document.getElementById("countTotal");

  // ── Navigation ──
  navItems.forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const viewId = item.getAttribute("data-view");
      showView(viewId);
    });
  });

  function showView(viewId) {
    views.forEach(v => v.classList.remove("active"));
    navItems.forEach(n => n.classList.remove("active"));
    document.getElementById(`view-${viewId}`).classList.add("active");
    document.querySelector(`[data-view="${viewId}"]`).classList.add("active");
    pageTitle.textContent = viewId.charAt(0).toUpperCase() + viewId.slice(1);
  }

  // ── Fetch & Render ──
  async function fetchScripts() {
    try {
      const res = await fetch("/api/scripts");
      scripts = await res.json();
      renderAll();
    } catch (err) {
      showToast("Failed to fetch scripts", "error");
    }
  }

  function renderAll() {
    renderDashboard();
    renderTable();
    updateLogSelect();
    updateStats();
  }

  function updateStats() {
    countTotal.textContent = scripts.length;
    countRunning.textContent = scripts.filter(s => s.status === "running").length;
    countStopped.textContent = scripts.filter(s => s.status === "stopped").length;
    countError.textContent = scripts.filter(s => s.status === "error").length;
  }

  function renderDashboard() {
    scriptCards.innerHTML = scripts.map(s => `
      <div class="script-card" data-name="${s.name}">
        <div class="script-card-header">
          <div class="script-name">${s.name}</div>
          <div class="status-badge ${s.status}">
            <span class="status-dot"></span> ${s.status}
          </div>
        </div>
        <div class="script-meta">
          <span><i class="fa-solid fa-microchip"></i> PID: ${s.pid || '--'}</span>
          <span><i class="fa-solid fa-clock"></i> ${s.started_at ? s.started_at.split(' ')[1] : '--'}</span>
        </div>
        <div class="script-actions">
          ${s.status === 'running' 
            ? `<button class="btn btn-secondary btn-sm" onclick="controlScript('${s.name}', 'stop')"><i class="fa-solid fa-stop"></i> Stop</button>`
            : `<button class="btn btn-success btn-sm" onclick="controlScript('${s.name}', 'start')"><i class="fa-solid fa-play"></i> Start</button>`
          }
          <button class="btn btn-secondary btn-sm" onclick="controlScript('${s.name}', 'restart')"><i class="fa-solid fa-rotate-right"></i></button>
          <button class="btn btn-secondary btn-sm" onclick="openEdit('${s.name}')"><i class="fa-solid fa-pen"></i></button>
          <button class="btn btn-secondary btn-sm" onclick="viewLogs('${s.name}')"><i class="fa-solid fa-terminal"></i></button>
        </div>
      </div>
    `).join("");
  }

  function renderTable() {
    scriptTableBody.innerHTML = scripts.map(s => `
      <tr>
        <td><strong>${s.name}</strong></td>
        <td><span class="status-badge ${s.status}">${s.status}</span></td>
        <td><code>${s.pid || '-'}</code></td>
        <td>${s.started_at || '-'}</td>
        <td>${(s.size / 1024).toFixed(1)} KB</td>
        <td>
          <div class="script-actions">
            <button class="btn btn-icon btn-secondary btn-sm" title="Install Requirements" onclick="installReq('${s.name}')"><i class="fa-solid fa-box-open"></i></button>
            <button class="btn btn-icon btn-danger btn-sm" title="Delete" onclick="confirmDelete('${s.name}')"><i class="fa-solid fa-trash"></i></button>
          </div>
        </td>
      </tr>
    `).join("");
  }

  function updateLogSelect() {
    const current = logScriptSelect.value;
    logScriptSelect.innerHTML = '<option value="">-- Select Script --</option>' + 
      scripts.map(s => `<option value="${s.name}" ${s.name === current ? 'selected' : ''}>${s.name}</option>`).join("");
  }

  // ── Controls ──
  window.controlScript = async (name, action) => {
    try {
      const res = await fetch(`/api/${action}/${name}`, { method: "POST" });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      showToast(data.message, "success");
      fetchScripts();
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  window.viewLogs = (name) => {
    logScriptSelect.value = name;
    currentLogScript = name;
    showView("logs");
    logPanel.innerHTML = '<span class="log-placeholder">Loading logs...</span>';
    socket.emit("request_logs", { name });
  };

  window.installReq = async (name) => {
    try {
      const res = await fetch(`/api/install/${name}`, { method: "POST" });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      showToast(data.message, "info");
      viewLogs(name);
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  // ── Edit Logic ──
  const editModal = document.getElementById("editModal");
  const codeEditor = document.getElementById("codeEditor");
  const editModalTitle = document.getElementById("editModalTitle");
  let editingName = "";

  window.openEdit = async (name) => {
    editingName = name;
    editModalTitle.textContent = name;
    try {
      const res = await fetch(`/api/edit/${name}`);
      const data = await res.json();
      codeEditor.value = data.content;
      editModal.classList.add("open");
    } catch (err) {
      showToast("Failed to load script", "error");
    }
  };

  document.getElementById("saveScript").addEventListener("click", async () => {
    try {
      const res = await fetch(`/api/edit/${editingName}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: codeEditor.value })
      });
      const data = await res.json();
      showToast(data.message, "success");
      editModal.classList.remove("open");
      fetchScripts();
    } catch (err) {
      showToast("Failed to save script", "error");
    }
  });

  // ── Delete Logic ──
  const confirmModal = document.getElementById("confirmModal");
  const confirmMsg = document.getElementById("confirmMsg");
  let deletingName = "";

  window.confirmDelete = (name) => {
    deletingName = name;
    confirmMsg.innerHTML = `Are you sure you want to delete <strong>${name}</strong>? This action cannot be undone.`;
    confirmModal.classList.add("open");
  };

  document.getElementById("confirmYes").addEventListener("click", async () => {
    try {
      const res = await fetch(`/api/delete/${deletingName}`, { method: "DELETE" });
      const data = await res.json();
      showToast(data.message, "success");
      confirmModal.classList.remove("open");
      fetchScripts();
    } catch (err) {
      showToast("Delete failed", "error");
    }
  });

  // ── Upload Logic ──
  const uploadBtn = document.getElementById("uploadBtn");
  const uploadModal = document.getElementById("uploadModal");
  const fileInput = document.getElementById("fileInput");
  const dropZone = document.getElementById("dropZone");
  const uploadStatus = document.getElementById("uploadStatus");

  uploadBtn.onclick = () => uploadModal.classList.add("open");
  
  const handleUpload = async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    uploadStatus.innerHTML = "Uploading...";
    try {
      const res = await fetch("/api/upload", { method: "POST", body: formData });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      uploadStatus.innerHTML = `<span class="success">${data.message}</span>`;
      setTimeout(() => {
        uploadModal.classList.remove("open");
        uploadStatus.innerHTML = "";
        fetchScripts();
      }, 1000);
    } catch (err) {
      uploadStatus.innerHTML = `<span class="error">${err.message}</span>`;
    }
  };

  fileInput.onchange = (e) => handleUpload(e.target.files[0]);
  dropZone.ondragover = (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); };
  dropZone.ondragleave = () => dropZone.classList.remove("drag-over");
  dropZone.ondrop = (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    handleUpload(e.dataTransfer.files[0]);
  };

  // ── Socket Events ──
  socket.on("status_change", (data) => {
    const s = scripts.find(x => x.name === data.name);
    if (s) {
      s.status = data.status;
      s.pid = data.pid || s.pid;
      renderAll();
    }
  });

  socket.on("log_line", (data) => {
    if (currentLogScript === data.name) {
      const line = document.createElement("div");
      line.textContent = data.line;
      // Basic coloring
      if (data.line.toLowerCase().includes("error") || data.line.toLowerCase().includes("exception")) line.className = "log-line-error";
      if (data.line.toLowerCase().includes("warn")) line.className = "log-line-warn";
      if (data.line.toLowerCase().includes("success") || data.line.toLowerCase().includes("started")) line.className = "log-line-success";
      
      logPanel.appendChild(line);
      if (logPanel.scrollHeight - logPanel.scrollTop < 1000) {
        logPanel.scrollTop = logPanel.scrollHeight;
      }
    }
  });

  socket.on("full_log", (data) => {
    if (currentLogScript === data.name) {
      logPanel.textContent = data.content;
      logPanel.scrollTop = logPanel.scrollHeight;
    }
  });

  logScriptSelect.onchange = (e) => {
    currentLogScript = e.target.value;
    if (currentLogScript) {
      logPanel.innerHTML = '<span class="log-placeholder">Loading logs...</span>';
      socket.emit("request_logs", { name: currentLogScript });
    } else {
      logPanel.innerHTML = '<span class="log-placeholder">Select a script to view logs...</span>';
    }
  };

  // ── System Stats ──
  async function updateSysStats() {
    try {
      const res = await fetch("/api/system");
      const data = await res.json();
      document.getElementById("cpuBar").style.width = data.cpu + "%";
      document.getElementById("cpuVal").textContent = Math.round(data.cpu) + "%";
      document.getElementById("ramBar").style.width = data.ram + "%";
      document.getElementById("ramVal").textContent = Math.round(data.ram) + "%";
      document.getElementById("diskBar").style.width = data.disk + "%";
      document.getElementById("diskVal").textContent = Math.round(data.disk) + "%";
    } catch(e){}
  }

  // ── UI Helpers ──
  function showToast(msg, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i class="fa-solid fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'circle-xmark' : 'circle-info'}"></i> <span>${msg}</span>`;
    document.getElementById("toastContainer").appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(20px)";
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  // Close modals on overlay click
  document.querySelectorAll(".modal-overlay").forEach(m => {
    m.onclick = (e) => { if (e.target === m) m.classList.remove("open"); };
  });
  document.querySelectorAll(".modal-close, #closeEdit2, #confirmNo").forEach(b => {
    b.onclick = () => document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("open"));
  });

  document.getElementById("clearLogBtn").onclick = () => logPanel.innerHTML = "";
  document.getElementById("scrollBottomBtn").onclick = () => logPanel.scrollTop = logPanel.scrollHeight;

  // Init
  fetchScripts();
  setInterval(updateSysStats, 3000);
  updateSysStats();
});
