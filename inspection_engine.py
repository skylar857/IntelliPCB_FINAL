import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

DEFECT_SEVERITY = {
    "Short Circuit": {"weight": 25, "color": (0, 0, 255)},    # Red
    "Open Trace": {"weight": 20, "color": (0, 165, 255)},      # Orange
    "Spurious Copper": {"weight": 10, "color": (255, 0, 255)},  # Purple
    "Missing Hole/Pad": {"weight": 15, "color": (255, 255, 0)}, # Yellow
    "Mouse Bite/Scratch": {"weight": 8, "color": (0, 255, 255)} # Cyan
}

def preprocess_image(image_bytes):
    """Decodes image, denoises, and aligns dimensions."""
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    img_resized = cv2.resize(img, (800, 600))
    gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
    denoised = cv2.GaussianBlur(gray, (5, 5), 0)
    return img_resized, denoised

def inspect_pcb(inspected_bytes, reference_bytes=None):
    """
    Performs differential AOI comparison or standalone edge-anomaly detection.
    """
    inspected_bgr, inspected_gray = preprocess_image(inspected_bytes)
    
    if reference_bytes:
        _, ref_gray = preprocess_image(reference_bytes)
    else:
        # If no reference supplied, build a clean bilateral threshold model
        ref_gray = cv2.bilateralFilter(inspected_gray, 9, 75, 75)

    # Compute Structural Similarity Index (SSIM)
    score, diff = ssim(ref_gray, inspected_gray, full=True)
    diff = (diff * 255).astype("uint8")

    # Threshold the difference image to find defect contours
    thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    cleaned_thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(cleaned_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    defects_detected = []
    annotated_bgr = inspected_bgr.copy()

    for idx, c in enumerate(contours):
        area = cv2.contourArea(c)
        if area < 15 or area > 5000:
            continue  # Filter background noise and oversized borders

        x, y, w, h = cv2.boundingRect(c)
        aspect_ratio = float(w) / h

        # Defect heuristic classification
        if aspect_ratio > 3.0 or aspect_ratio < 0.33:
            defect_type = "Open Trace"
        elif area > 350:
            defect_type = "Short Circuit"
        elif 0.8 <= aspect_ratio <= 1.2 and area < 80:
            defect_type = "Missing Hole/Pad"
        elif area > 100:
            defect_type = "Spurious Copper"
        else:
            defect_type = "Mouse Bite/Scratch"

        defects_detected.append({
            "id": f"DEF-{idx+1:03d}",
            "type": defect_type,
            "area_px": int(area),
            "bbox": (x, y, w, h),
            "severity_weight": DEFECT_SEVERITY[defect_type]["weight"]
        })

        color = DEFECT_SEVERITY[defect_type]["color"]
        cv2.rectangle(annotated_bgr, (x, y), (x + w, y + h), color, 2)
        cv2.putText(annotated_bgr, defect_type[:4], (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    # Calculate Quality Score
    total_penalty = sum(d["severity_weight"] for d in defects_detected)
    quality_score = max(0.0, min(100.0, 100.0 - total_penalty))
    
    if quality_score >= 90:
        status = "PASSED - Grade A"
    elif quality_score >= 70:
        status = "CONDITIONAL PASS - Grade B"
    else:
        status = "REJECTED - Grade C"

    return {
        "annotated_bgr": annotated_bgr,
        "defects": defects_detected,
        "score": round(quality_score, 1),
        "status": status,
        "total_defects": len(defects_detected)
    }