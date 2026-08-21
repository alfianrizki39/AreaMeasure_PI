"""
Flask backend — Area Measurement Web App.

Endpoints:
    GET  /                      → Halaman utama (kamera + upload)
    POST /api/measure           → Terima gambar, proses, kembalikan hasil
    GET  /api/history           → Ambil semua riwayat pengukuran (JSON)
    GET  /api/history/<id>      → Detail satu pengukuran (JSON)
    GET  /history               → Halaman riwayat pengukuran
"""

import base64
import os
import uuid
from datetime import datetime

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request, send_from_directory

from models import get_all_measurements, init_db, insert_measurement
from processing import process_image

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload

# Output images disimpan di static/outputs agar bisa diakses langsung via URL
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "static", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ──────────────────────────────────────────────
# Pages
# ──────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/history")
def history_page():
    return render_template("index.html")


# ──────────────────────────────────────────────
# API
# ──────────────────────────────────────────────
@app.route("/api/measure", methods=["POST"])
def api_measure():
    """
    Menerima gambar via:
      • multipart file  → field name "image"
      • JSON base64      → { "image_base64": "data:image/jpeg;base64,..." }

    Mengembalikan JSON:
      {
        "success": true,
        "total_area_cm2": 150.5,
        "object_count": 5,
        "objects": [{"index": 1, "area_cm2": 33.75}, ...],
        "output_image_url": "/static/outputs/abc123_output.jpg",
        "output_image_base64": "data:image/jpeg;base64,...",
        "measurement_id": 1
      }
    """
    try:
        img_array = _decode_input_image(request)
        total_area, objects, output_img = process_image(img_array)

        # Simpan output image ke disk
        uid = uuid.uuid4().hex[:8]
        filename = f"{uid}_output.jpg"
        filepath = os.path.join(OUTPUT_DIR, filename)
        cv2.imwrite(filepath, output_img, [cv2.IMWRITE_JPEG_QUALITY, 90])

        # Encode output image → base64 untuk response langsung
        _, buffer = cv2.imencode(".jpg", output_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        output_b64 = base64.b64encode(buffer).decode("utf-8")

        # Simpan ke database
        row_id = insert_measurement(total_area, objects, filename, "success")

        return jsonify(
            success=True,
            total_area_cm2=total_area,
            object_count=len(objects),
            objects=objects,
            output_image_url=f"/static/outputs/{filename}",
            output_image_base64=f"data:image/jpeg;base64,{output_b64}",
            measurement_id=row_id,
        )

    except Exception as exc:
        insert_measurement(None, None, None, "failed")
        return jsonify(success=False, error=str(exc)), 400


@app.route("/api/history", methods=["GET"])
def api_history():
    """Return all measurements as JSON array."""
    rows = get_all_measurements()
    return jsonify(rows)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def _decode_input_image(req) -> np.ndarray:
    """Decode image from multipart file upload OR JSON base64 payload."""

    # 1) Multipart file upload
    if "image" in req.files:
        file = req.files["image"]
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("File yang diunggah bukan gambar valid.")
        return img

    # 2) JSON base64
    data = req.get_json(silent=True)
    if data and "image_base64" in data:
        header, encoded = data["image_base64"].split(",", 1)
        img_bytes = base64.b64decode(encoded)
        file_bytes = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Data base64 bukan gambar valid.")
        return img

    raise ValueError("Tidak ada gambar ditemukan di request. Kirim via 'image' file atau 'image_base64' JSON.")


# ──────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    # host 0.0.0.0 agar bisa diakses dari HP di jaringan yang sama
    app.run(host="0.0.0.0", port=5000, debug=True)
