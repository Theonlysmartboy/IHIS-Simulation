#!/usr/bin/env python3
"""
IHIS Simulation Dashboard
Flask app: upload Synthea FHIR data, run simulation, view results.
"""

import sys
import os
import json

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

import numpy as np
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import io
import zipfile
from flask.json.provider import DefaultJSONProvider
from werkzeug.utils import secure_filename


class NumpyJSONProvider(DefaultJSONProvider):
    @staticmethod
    def default(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            v = float(obj)
            if v != v or v == float("inf") or v == float("-inf"):
                return None
            return v
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, float):
            if obj != obj or obj == float("inf") or obj == float("-inf"):
                return None
        if callable(obj):
            return None
        return super().default(obj)


app = Flask(__name__)
app.json_provider_class = NumpyJSONProvider
app.json = NumpyJSONProvider(app)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max upload

# Vercel has read-only filesystem — use /tmp for uploads
if os.environ.get("VERCEL"):
    UPLOAD_DIR = "/tmp/uploads"
else:
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
except OSError:
    UPLOAD_DIR = "/tmp/uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

# Database URL placeholder (user will provide Neon URL)
DB_URL = os.environ.get("DATABASE_URL", "")
db_initialized = False


def ensure_db():
    global db_initialized
    if not db_initialized and DB_URL:
        from dashboard.db import init_db
        init_db(DB_URL)
        db_initialized = True


# ============================================================
# Routes
# ============================================================

@app.route("/")
def index():
    ensure_db()
    data = {"has_data": False, "results": None, "data_summary": None}

    if db_initialized:
        from dashboard.simulation import get_data_summary
        data["data_summary"] = get_data_summary()
        data["has_data"] = data["data_summary"]["has_data"]

    return render_template("index.html", data=data, data_json=json.dumps(data, default=str))


@app.route("/upload", methods=["POST"])
def upload():
    ensure_db()
    if not db_initialized:
        return jsonify({"error": "Database not connected. Set DATABASE_URL."}), 500

    from dashboard.fhir_parser import parse_synthea_bundle

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    results = []
    for f in files:
        if not f.filename:
            continue
        filename = secure_filename(f.filename)
        if not filename.endswith(".json"):
            results.append({"filename": filename, "error": "Not a JSON file"})
            continue

        content = f.read().decode("utf-8")
        result = parse_synthea_bundle(content, filename)
        results.append(result)

    return jsonify({"uploads": results})


@app.route("/simulate", methods=["POST"])
def simulate():
    ensure_db()
    if not db_initialized:
        return jsonify({"error": "Database not connected. Set DATABASE_URL."}), 500

    from dashboard.simulation import run_full_simulation

    body = request.get_json(silent=True) or {}
    arrival_rate = body.get("arrival_rate", 48)
    num_servers = body.get("num_servers", 3)

    results = run_full_simulation(arrival_rate=arrival_rate, num_servers=num_servers)
    return jsonify(results)


@app.route("/api/data-summary")
def api_data_summary():
    ensure_db()
    if not db_initialized:
        return jsonify({"has_data": False})
    from dashboard.simulation import get_data_summary
    return jsonify(get_data_summary())


@app.route("/api/clear", methods=["POST"])
def api_clear():
    """Clear all uploaded data from the database."""
    ensure_db()
    if not db_initialized:
        return jsonify({"error": "Database not connected"}), 500

    from dashboard.db import get_session, Patient, Encounter, Observation, Condition, Medication, UploadBatch, SimulationRun, Dhis2Data
    session = get_session()
    try:
        for model in [Observation, Condition, Medication, Encounter, Patient, SimulationRun, UploadBatch, Dhis2Data]:
            session.query(model).delete()
        session.commit()
        return jsonify({"status": "cleared"})
    finally:
        session.close()


@app.route("/api/import-fhir-server")
def import_fhir_server():
    """Fetch sample resources from the public HAPI FHIR test server."""
    ensure_db()
    if not db_initialized:
        return jsonify({"error": "Database not connected"}), 500
    from dashboard.fhir_server import fetch_from_hapi
    result = fetch_from_hapi()
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@app.route("/api/import-dhis2")
def import_dhis2():
    """Fetch health indicators from DHIS2 public demo."""
    ensure_db()
    if not db_initialized:
        return jsonify({"error": "Database not connected"}), 500
    from dashboard.dhis2 import fetch_from_dhis2
    result = fetch_from_dhis2()
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@app.route("/api/dhis2-indicators")
def api_dhis2_indicators():
    """Return DHIS2 indicators grouped by indicator, with values across periods."""
    ensure_db()
    if not db_initialized:
        return jsonify({"indicators": [], "periods": []})

    from dashboard.db import get_session, Dhis2Data
    session = get_session()
    try:
        rows = session.query(Dhis2Data).order_by(Dhis2Data.indicator_name, Dhis2Data.period).all()
        if not rows:
            return jsonify({"indicators": [], "periods": []})

        periods = sorted({r.period for r in rows})
        indicators = {}
        for r in rows:
            if r.indicator_name not in indicators:
                indicators[r.indicator_name] = {
                    "name": r.indicator_name,
                    "org_unit": r.org_unit,
                    "values": {}
                }
            indicators[r.indicator_name]["values"][r.period] = r.value

        indicator_list = []
        for ind in indicators.values():
            row = {"name": ind["name"], "org_unit": ind["org_unit"], "values": []}
            vals = [ind["values"].get(p) for p in periods]
            row["values"] = vals
            valid_vals = [v for v in vals if v is not None]
            row["latest"] = vals[-1] if vals else None
            row["avg"] = round(sum(valid_vals) / len(valid_vals), 2) if valid_vals else None
            indicator_list.append(row)

        return jsonify({
            "indicators": indicator_list,
            "periods": periods,
            "total_indicators": len(indicator_list),
        })
    finally:
        session.close()


@app.route("/samples")
def samples_page():
    """Page listing pre-generated Synthea data batches."""
    samples_dir = os.path.join(PROJECT_ROOT, "data", "samples")
    batches = []
    if os.path.isdir(samples_dir):
        for name in sorted(os.listdir(samples_dir)):
            batch_path = os.path.join(samples_dir, name)
            if os.path.isdir(batch_path):
                files = [f for f in os.listdir(batch_path) if f.endswith(".json")]
                total_size = sum(os.path.getsize(os.path.join(batch_path, f)) for f in files)
                batches.append({
                    "name": name,
                    "label": name.replace("_", " ").title(),
                    "files": len(files),
                    "size_mb": round(total_size / (1024 * 1024), 1),
                })
    return render_template("samples.html", batches=batches)


@app.route("/api/download-batch/<batch_name>")
def download_batch(batch_name):
    """Download a batch folder as a zip file."""
    batch_path = os.path.join(PROJECT_ROOT, "data", "samples", batch_name)
    if not os.path.isdir(batch_path):
        return jsonify({"error": "Batch not found"}), 404

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in os.listdir(batch_path):
            if f.endswith(".json"):
                zf.write(os.path.join(batch_path, f), arcname=f)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{batch_name}.zip"
    )


@app.route("/api/import-batch", methods=["POST"])
def import_batch():
    """Import a single file from a pre-generated batch."""
    ensure_db()
    if not db_initialized:
        return jsonify({"error": "Database not connected"}), 500

    from dashboard.fhir_parser import parse_synthea_bundle

    body = request.get_json(silent=True) or {}
    batch_name = body.get("batch")
    filename = body.get("filename")

    if not batch_name or not filename:
        return jsonify({"error": "Missing batch or filename"}), 400

    filepath = os.path.join(PROJECT_ROOT, "data", "samples", batch_name, filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "File not found"}), 404

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    result = parse_synthea_bundle(content, filename)
    return jsonify(result)


@app.route("/api/batch-files")
def batch_files():
    """List files in a batch for sequential import."""
    batch_name = request.args.get("batch")
    if not batch_name:
        return jsonify({"error": "Missing batch param"}), 400

    batch_path = os.path.join(PROJECT_ROOT, "data", "samples", batch_name)
    if not os.path.isdir(batch_path):
        return jsonify({"error": "Batch not found"}), 404

    files = sorted([f for f in os.listdir(batch_path) if f.endswith(".json")])
    return jsonify({"batch": batch_name, "files": files, "count": len(files)})


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    # Get DB URL from env or prompt
    if not DB_URL:
        url = os.environ.get("DATABASE_URL", "")
        if not url:
            print("\n  No DATABASE_URL set.")
            print("  Set it as environment variable or pass on command line:")
            print("  DATABASE_URL=postgresql://... python dashboard/app.py\n")
            print("  Starting without database (upload disabled)...\n")
        else:
            DB_URL = url

    if DB_URL:
        from dashboard.db import init_db
        init_db(DB_URL)
        db_initialized = True
        print("  Database connected.")

    print("\n  IHIS Simulation Dashboard")
    print("  http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
