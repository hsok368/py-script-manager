"""
Universal Python Script Manager Dashboard
==========================================
A web-based dashboard to host, manage, and monitor any Python script.
Features: Start/Stop/Restart, Live Logs, Error Reporting, Edit Scripts,
          Install Requirements, Delete Scripts.
"""

import os
import sys
import json
import time
import signal
import shutil
import subprocess
import threading
import traceback
from pathlib import Path
from datetime import datetime

import psutil
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

# ─── App Configuration ────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
SCRIPTS_DIR = BASE_DIR / "scripts"
LOGS_DIR    = BASE_DIR / "logs"
UPLOADS_DIR = BASE_DIR / "uploads"

# If scripts folder is missing or empty, use the current folder for scripts
if not SCRIPTS_DIR.exists() or not any(SCRIPTS_DIR.glob("*.py")):
    SCRIPTS_DIR = BASE_DIR

for d in (LOGS_DIR, UPLOADS_DIR):
    d.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".py", ".txt"}

app = Flask(__name__, template_folder='.', static_folder='.')
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# ─── In-memory process registry ───────────────────────────────────────────────
# { script_name: { "process": Popen, "status": str, "pid": int, "started_at": str } }
processes: dict = {}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def script_path(name: str) -> Path:
    return SCRIPTS_DIR / secure_filename(name)


def log_path(name: str) -> Path:
    return LOGS_DIR / (Path(name).stem + ".log")


def get_status(name: str) -> str:
    entry = processes.get(name)
    if not entry:
        return "stopped"
    proc = entry.get("process")
    if proc is None:
        return "stopped"
    ret = proc.poll()
    if ret is None:
        return "running"
    return "error" if ret != 0 else "stopped"


def list_scripts() -> list:
    result = []
    for f in sorted(SCRIPTS_DIR.glob("*.py")):
        name = f.name
        status = get_status(name)
        entry  = processes.get(name, {})
        result.append({
            "name":       name,
            "status":     status,
            "pid":        entry.get("pid"),
            "started_at": entry.get("started_at"),
            "size":       f.stat().st_size,
        })
    return result


def stream_output(name: str, proc: subprocess.Popen):
    """Read stdout+stderr from process and emit via SocketIO + write to log."""
    lp = log_path(name)
    with open(lp, "a", encoding="utf-8") as lf:
        lf.write(f"\n{'='*60}\n[{datetime.now():%Y-%m-%d %H:%M:%S}] STARTED\n{'='*60}\n")
        for line in iter(proc.stdout.readline, ""):
            if line:
                lf.write(line)
                lf.flush()
                socketio.emit("log_line", {"name": name, "line": line.rstrip()})
        # Capture any remaining stderr
        err = proc.stderr.read() if proc.stderr else ""
        if err:
            lf.write(err)
            lf.flush()
            for el in err.splitlines():
                socketio.emit("log_line", {"name": name, "line": el})
        ret = proc.wait()
        finish_msg = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] PROCESS EXITED (code={ret})\n"
        lf.write(finish_msg)
        socketio.emit("log_line", {"name": name, "line": finish_msg.rstrip()})
        socketio.emit("status_change", {"name": name, "status": "error" if ret != 0 else "stopped"})
        if name in processes:
            processes[name]["status"] = "error" if ret != 0 else "stopped"


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    # Look for index.html in root if templates/index.html is missing
    if not (BASE_DIR / "templates" / "index.html").exists():
        return render_template("index.html", scripts=list_scripts())
    return render_template("index.html", scripts=list_scripts())


@app.route("/api/scripts", methods=["GET"])
def api_list():
    return jsonify(list_scripts())


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Upload a .py or requirements.txt file."""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Extension '{ext}' not allowed"}), 400

    fname = secure_filename(f.filename)
    dest  = SCRIPTS_DIR / fname
    f.save(dest)
    return jsonify({"message": f"'{fname}' uploaded successfully", "name": fname})


@app.route("/api/start/<name>", methods=["POST"])
def api_start(name: str):
    sp = script_path(name)
    if not sp.exists():
        return jsonify({"error": "Script not found"}), 404
    if get_status(name) == "running":
        return jsonify({"error": "Already running"}), 409

    try:
        proc = subprocess.Popen(
            [sys.executable, str(sp)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=str(SCRIPTS_DIR),
        )
        processes[name] = {
            "process":    proc,
            "pid":        proc.pid,
            "status":     "running",
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        t = threading.Thread(target=stream_output, args=(name, proc), daemon=True)
        t.start()
        socketio.emit("status_change", {"name": name, "status": "running", "pid": proc.pid})
        return jsonify({"message": f"'{name}' started", "pid": proc.pid})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stop/<name>", methods=["POST"])
def api_stop(name: str):
    entry = processes.get(name)
    if not entry or get_status(name) != "running":
        return jsonify({"error": "Not running"}), 409
    proc = entry["process"]
    try:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        processes[name]["status"] = "stopped"
        socketio.emit("status_change", {"name": name, "status": "stopped"})
        return jsonify({"message": f"'{name}' stopped"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/restart/<name>", methods=["POST"])
def api_restart(name: str):
    api_stop(name)
    time.sleep(0.5)
    return api_start(name)


@app.route("/api/logs/<name>", methods=["GET"])
def api_logs(name: str):
    lp = log_path(name)
    if not lp.exists():
        return jsonify({"log": ""})
    lines = int(request.args.get("lines", 200))
    with open(lp, "r", encoding="utf-8", errors="replace") as f:
        content = f.readlines()
    return jsonify({"log": "".join(content[-lines:])})


@app.route("/api/edit/<name>", methods=["GET"])
def api_get_script(name: str):
    sp = script_path(name)
    if not sp.exists():
        return jsonify({"error": "Not found"}), 404
    with open(sp, "r", encoding="utf-8", errors="replace") as f:
        return jsonify({"name": name, "content": f.read()})


@app.route("/api/edit/<name>", methods=["POST"])
def api_save_script(name: str):
    sp = script_path(name)
    data = request.get_json(force=True)
    content = data.get("content", "")
    was_running = get_status(name) == "running"
    if was_running:
        api_stop(name)
    with open(sp, "w", encoding="utf-8") as f:
        f.write(content)
    if was_running:
        time.sleep(0.3)
        api_start(name)
    return jsonify({"message": f"'{name}' saved successfully"})


@app.route("/api/install/<name>", methods=["POST"])
def api_install(name: str):
    """Install packages from a requirements.txt sitting next to the script."""
    req_file = SCRIPTS_DIR / "requirements.txt"
    # Also accept a per-script requirements file: <stem>_requirements.txt
    stem_req = SCRIPTS_DIR / (Path(name).stem + "_requirements.txt")
    target = stem_req if stem_req.exists() else req_file

    if not target.exists():
        return jsonify({"error": "No requirements.txt found in scripts/ folder"}), 404

    def run_install():
        lp = log_path(name)
        with open(lp, "a", encoding="utf-8") as lf:
            lf.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] Installing from {target.name}...\n")
        proc = subprocess.Popen(
            [sys.executable, "-m", "pip", "install", "-r", str(target)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        with open(lp, "a", encoding="utf-8") as lf:
            for line in iter(proc.stdout.readline, ""):
                lf.write(line)
                lf.flush()
                socketio.emit("log_line", {"name": name, "line": line.rstrip()})
        ret = proc.wait()
        msg = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] pip install finished (code={ret})\n"
        with open(lp, "a", encoding="utf-8") as lf:
            lf.write(msg)
        socketio.emit("log_line", {"name": name, "line": msg.rstrip()})
        socketio.emit("install_done", {"name": name, "code": ret})

    threading.Thread(target=run_install, daemon=True).start()
    return jsonify({"message": "Installation started — watch the log panel"})


@app.route("/api/delete/<name>", methods=["DELETE"])
def api_delete(name: str):
    if get_status(name) == "running":
        api_stop(name)
    sp = script_path(name)
    lp = log_path(name)
    if sp.exists():
        sp.unlink()
    if lp.exists():
        lp.unlink()
    processes.pop(name, None)
    socketio.emit("script_deleted", {"name": name})
    return jsonify({"message": f"'{name}' deleted"})


@app.route("/api/system", methods=["GET"])
def api_system():
    return jsonify({
        "cpu":    psutil.cpu_percent(interval=0.1),
        "ram":    psutil.virtual_memory().percent,
        "disk":   psutil.disk_usage("/").percent,
        "uptime": int(time.time() - psutil.boot_time()),
    })


# ─── SocketIO events ──────────────────────────────────────────────────────────

@socketio.on("connect")
def on_connect():
    emit("scripts_list", list_scripts())


@socketio.on("request_logs")
def on_request_logs(data):
    name = data.get("name", "")
    lp   = log_path(name)
    if lp.exists():
        with open(lp, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        emit("full_log", {"name": name, "content": content})
    else:
        emit("full_log", {"name": name, "content": "(no log yet)"})


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[Dashboard] Running at http://0.0.0.0:{port}")
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
