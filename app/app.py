import json
import os
import sys
import time
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)          # so "import src..." works
os.chdir(ROOT)                    # so relative paths (uploads/, dataset/) work

import requests
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

import database as db
from src.prediction import run
from src.preprocessing import fetch_arxiv_pdf

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024        # 50 MB upload limit
UPLOAD_DIR = os.path.join(ROOT, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
db.init_db()


def error(message, status=400):
    return jsonify({"error": message}), status


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/process", methods=["POST"])
def process():
    started = time.perf_counter()
    label = "unknown"
    try:
        options = json.loads(request.form.get("options", "{}"))
        uploaded = request.files.get("file")
        arxiv = request.form.get("arxiv", "").strip()
        if uploaded and uploaded.filename:
            label = secure_filename(uploaded.filename)
            if not label.lower().endswith(".pdf"):
                return error("Only PDF files are supported.")
            path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex[:8]}_{label}")
            uploaded.save(path)
        elif arxiv:
            label = arxiv
            path = fetch_arxiv_pdf(arxiv, UPLOAD_DIR)
        else:
            return error("Add a PDF or an arXiv ID first.")

        result = run(path, options)
        result = db.add_paper(label, result["mode"], result["length"], result)
        ms = int((time.perf_counter() - started) * 1000)
        db.log_event("Process", f"{result['title']} | {result['mode']}/{result['length']}", "ok", ms)
        return jsonify(result)

    except ValueError as e:                                  # bad input or unreadable PDF
        db.log_event("Process", label, f"error: {e}")
        return error(str(e))
    except requests.RequestException:
        db.log_event("Process", label, "error: download failed")
        return error("Could not download that paper. Check the arXiv ID and your internet.", 502)
    except Exception as e:                                   # anything unexpected
        db.log_event("Process", label, f"error: {e}")
        return error(f"Something went wrong: {e}", 500)


@app.route("/api/papers")
def papers():
    return jsonify(db.list_papers())


@app.route("/api/papers/<int:pid>", methods=["GET", "DELETE"])
def paper(pid):
    if request.method == "DELETE":
        db.delete_paper(pid)
        db.log_event("Delete", f"paper {pid}")
        return jsonify({"deleted": pid})
    result = db.get_paper(pid)
    return jsonify(result) if result else error("Paper not found.", 404)


@app.route("/api/history", methods=["GET", "DELETE"])
def history():
    if request.method == "DELETE":
        db.clear_history()
        return jsonify({"cleared": True})
    return jsonify(db.list_history())


@app.route("/api/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        db.log_event("Settings", "changed")
        return jsonify(db.save_settings(request.get_json(silent=True) or {}))
    return jsonify(db.get_settings())


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)      # reloader off: it would reload the spaCy model twice