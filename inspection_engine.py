import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

def inspect_pcb(inspected_bytes, reference_bytes=None):
    """
    Performs algorithmic computer vision inspection using SSIM 
    and contour analysis against a golden reference image.
    """
    # Decode inspected board bytes
    np_arr_insp = np.frombuffer(inspected_bytes, np.uint8)
    inspected_img = cv2.imdecode(np_arr_insp, cv2.IMREAD_COLOR)
    
    # Resize for uniform matrix comparison
    h, w = 600, 800
    inspected_resized = cv2.resize(inspected_img, (w, h))
    
    # Handle reference image if provided, otherwise create a baseline proxy
    if reference_bytes is not None:
        np_arr_ref = np.frombuffer(reference_bytes, np.uint8)
        reference_img = cv2.imdecode(np_arr_ref, cv2.IMREAD_COLOR)
        reference_resized = cv2.resize(reference_img, (w, h))
    else:
        reference_resized = inspected_resized.copy()

    # Convert to grayscale for structural similarity calculation
    gray_insp = cv2.cvtColor(inspected_resized, cv2.COLOR_BGR2GRAY)
    gray_ref = cv2.cvtColor(reference_resized, cv2.COLOR_BGR2GRAY)

    gray_insp = cv2.GaussianBlur(gray_insp, (11, 11), 0)
    gray_ref = cv2.GaussianBlur(gray_ref, (11, 11), 0)

    # Compute Structural Similarity Index (SSIM) matrix
    score_ssim, diff = ssim(gray_ref, gray_insp, full=True)
    diff = (diff * 255).astype("np.uint8" if hasattr(np, "uint8") else np.uint8)

    # Threshold the difference to isolate discrepancies (defects)
    thresh = cv2.threshold(diff, 180, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    thresh = cv2.dilate(thresh, kernel, iterations=2)

    # Find contours of the defects
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    annotated_bgr = inspected_resized.copy()
    defects_detected = []
    
    defect_types = ["Short Circuit", "Open Trace", "Spurious Copper", "Missing Pad", "Anomalous Etch"]

    for idx, c in enumerate(contours):
        area = cv2.contourArea(c)
        # Filter out noise
        if area < 400 or area > 5000:
            continue
            
        (x, y, bw, bh) = cv2.boundingRect(c)
        
        # ---> SMARTER DEFECT LABELING HEURISTIC <---
        # Instead of guessing randomly, assign a type based on the shape of the defect
        if area < 600:
            d_type = "Spurious Copper"
            severity = 10
        elif bw > bh * 2 or bh > bw * 2: 
            # If the box is long and thin, it's usually a short or a cut trace
            d_type = "Short Circuit / Open Trace"
            severity = 30
        else:
            d_type = "Missing Component / Pad"
            severity = 20
            
        defects_detected.append({
            "id": f"DEF-{idx+1:03d}",
            "type": d_type,
            "area_px": int(area),
            "bbox": (x, y, bw, bh),
            "severity_weight": severity
        })
        
        # Draw bounding box on annotated board view
        cv2.rectangle(annotated_bgr, (x, y), (x + bw, y + bh), (0, 0, 255), 2)
        cv2.putText(annotated_bgr, f"{d_type}", (x, max(y - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

    # ---> FIX THE GRADING PENALTY <---
    # Multiply the penalty by 1.5 so a major Short Circuit actually forces a rejection
    total_penalty = sum(d["severity_weight"] for d in defects_detected)
    quality_score = max(0.0, min(100.0, 100.0 - (total_penalty * 1.5)))

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