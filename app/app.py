import json
import os
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)          # so "import src..." works
os.chdir(ROOT)                    # so relative paths (uploads/, dataset/) work

import requests
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

# Point directly to our updated pipeline
from src.pipeline import run_pipeline
from src.preprocessing import fetch_arxiv_pdf

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024        # 50 MB upload limit
UPLOAD_DIR = os.path.join(ROOT, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def error(message, status=400):
    return jsonify({"error": message}), status


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/process", methods=["POST"])
def process():
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
            path = fetch_arxiv_pdf(arxiv, UPLOAD_DIR)
        else:
            return error("Add a PDF or an arXiv ID first.")

        # Map options directly to the updated pipeline
        mode = options.get("mode", "compare")
        length = options.get("length", "medium")
        norm = options.get("normalization", "lemma")
        
        # Process strictly in memory without database persistence
        result = run_pipeline(path, mode=mode, length=length, normalization=norm)
        
        # Clean up the file after processing to save space
        if os.path.exists(path):
            os.remove(path)
            
        return jsonify(result)

    except ValueError as e:                                  # bad input or unreadable PDF
        return error(str(e))
    except requests.RequestException:
        return error("Could not download that paper. Check the arXiv ID and your internet.", 502)
    except Exception as e:                                   # anything unexpected
        return error(f"Something went wrong: {e}", 500)
    
from flask import send_from_directory

@app.route('/results/graphs/<filename>')
def serve_graph(filename):
    return send_from_directory(os.path.join(ROOT, 'results', 'graphs'), filename)

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)      # reloader off: it would reload the spaCy model twice