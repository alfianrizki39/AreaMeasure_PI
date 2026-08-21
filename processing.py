"""
Image processing module — Pipeline OpenCV lengkap.

Alur:
  1. Resize 30% → deteksi kontur kertas A4 (filter=4 sudut)
  2. Scale titik kembali ke resolusi asli → Perspective Warp
  3. Deteksi kontur objek di atas kertas → hitung luas (cm²)
  4. Gambar kontur hijau + teks luas di gambar output
  5. Return (total_luas, objects_list, output_img)
"""

import cv2
import numpy as np
import utlis

# ── Konfigurasi A4 & Kalibrasi ──────────────
SCALE = 3
W_PAPER = 210 * SCALE   # Lebar A4 landscape (mm → pixel unit)
H_PAPER = 297 * SCALE   # Tinggi A4 landscape (mm → pixel unit)

RESIZE_FACTOR = 0.3      # Faktor resize untuk deteksi A4

KALIBRASI_W = 1.0
KALIBRASI_H = 1.0
KALIBRASI_LUAS = KALIBRASI_W * KALIBRASI_H


def process_image(img: np.ndarray) -> tuple[float, list[dict], np.ndarray]:
    """
    Memproses satu gambar: deteksi kertas A4, warp, deteksi objek, hitung luas.

    Input:  img         — numpy array BGR (dari cv2.imread / cv2.imdecode)
    Output: total_area  — float, total luas semua objek (cm²)
            objects     — list of dict, detail per objek:
                          [{"index": 1, "area_cm2": 33.75}, ...]
            output_img  — numpy array BGR, gambar warped dengan anotasi kontur

    Raises:
        ValueError — jika kertas A4 atau objek tidak terdeteksi.
    """
    # Simpan salinan resolusi penuh untuk warping
    img_original = img.copy()

    # ── Step 1: Resize untuk deteksi A4 ─────
    img_small = cv2.resize(img, (0, 0), None, RESIZE_FACTOR, RESIZE_FACTOR)

    # ── Step 2: Deteksi kontur kertas A4 (4 sudut) ─────
    _, conts = utlis.getContours(
        img_small, minArea=1000, filter=4, draw=False
    )

    if len(conts) == 0:
        raise ValueError(
            "Kertas A4 tidak terdeteksi. "
            "Pastikan seluruh kertas A4 terlihat jelas di dalam frame "
            "dengan kontras yang cukup terhadap latar belakang."
        )

    # Ambil kontur terbesar (A4) dan scale kembali ke ukuran asli
    biggest = conts[0][2]
    biggest_original = biggest / RESIZE_FACTOR

    # ── Step 3: Perspective Warp ─────
    img_warp = utlis.warpImg(img_original, biggest_original, W_PAPER, H_PAPER)

    # ── Step 4: Deteksi objek di atas kertas A4 ─────
    img_contours, conts2 = utlis.getContours(
        img_warp, minArea=2000, filter=0, cThr=[50, 50], draw=False
    )

    if len(conts2) == 0:
        raise ValueError(
            "Tidak ada objek terdeteksi di atas kertas A4. "
            "Pastikan objek memiliki kontras yang cukup terhadap kertas."
        )

    # ── Step 5: Hitung luas & anotasi ─────
    total_area = 0.0
    objects = []

    for idx, obj in enumerate(conts2, start=1):
        kontur_utuh = obj[4]  # Kontur mentah (bentuk asli)

        # Gambar kontur hijau mengikuti bentuk asli
        cv2.drawContours(img_contours, [kontur_utuh], -1, (0, 255, 0), 2)

        # Hitung luas dalam piksel
        luas_pixel = cv2.contourArea(kontur_utuh)

        # Konversi piksel → cm²
        luas_cm2 = (luas_pixel / ((SCALE ** 2) * 100)) * KALIBRASI_LUAS
        luas_cm2 = round(luas_cm2, 2)
        total_area += luas_cm2

        objects.append({"index": idx, "area_cm2": luas_cm2})

        # Bounding box untuk penempatan teks
        x, y, w, h = obj[3]

        # Kotak batas kuning putus-putus
        cv2.rectangle(img_contours, (x, y), (x + w, y + h), (0, 255, 255), 1)

        # Teks luas area
        cv2.putText(
            img_contours,
            f'Luas: {luas_cm2} cm2',
            (x, y - 10),
            cv2.FONT_HERSHEY_COMPLEX_SMALL,
            1.2,
            (255, 0, 255),
            2,
        )

    total_area = round(total_area, 2)
    return total_area, objects, img_contours
