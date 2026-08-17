import os
import cv2
from fpdf import FPDF
from datetime import datetime

class PCBReport(FPDF):
    def header(self):
        self.set_fill_color(24, 43, 73)
        self.rect(0, 0, 210, 25, 'F')
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "IntelliPCB - Automated Inspection Certificate", ln=True, align="C")
        self.set_font("Helvetica", "I", 9)
        self.cell(0, 5, "ISO-9001 / IPC-A-610 Automated Optical Quality Report", ln=True, align="C")
        self.ln(8)

    def footer(self):
        self.set_y(-18)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 5, f"Generated automatically by IntelliPCB Core Engine | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", align="C")

def build_pdf_report(inspection_data, batch_id, inspector_name, output_path="report.pdf"):
    # Save temporary annotated image for PDF inclusion
    temp_img = "temp_annotated.jpg"
    cv2.imwrite(temp_img, inspection_data["annotated_bgr"])

    pdf = PCBReport(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_text_color(30, 30, 30)

    # Metadata Panel
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(240, 243, 246)
    pdf.rect(10, 32, 190, 22, 'F')
    
    pdf.set_xy(15, 34)
    pdf.cell(90, 6, f"Batch / Board ID: {batch_id}", ln=False)
    pdf.cell(90, 6, f"Inspection Date: {datetime.now().strftime('%d-%b-%Y')}", ln=True)
    pdf.set_xy(15, 42)
    pdf.cell(90, 6, f"Quality Inspector: {inspector_name}", ln=False)
    pdf.cell(90, 6, f"Overall Status: {inspection_data['status']}", ln=True)
    pdf.ln(8)

    # Score Highlight
    pdf.set_font("Helvetica", "B", 12)
    score_color = (34, 139, 34) if inspection_data["score"] >= 85 else (220, 20, 60)
    pdf.set_text_color(*score_color)
    pdf.cell(0, 8, f"Calculated Quality Score: {inspection_data['score']}/100 | Total Defects: {inspection_data['total_defects']}", ln=True, align="C")
    pdf.ln(2)

    # Annotated Image
    pdf.image(temp_img, x=25, y=pdf.get_y(), w=160)
    pdf.set_y(pdf.get_y() + 125)

    # Defect Breakdown Table
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(24, 43, 73)
    pdf.cell(30, 7, "Defect ID", 1, 0, 'C', True)
    pdf.cell(65, 7, "Fault Classification", 1, 0, 'C', True)
    pdf.cell(45, 7, "Bounding Area (px)", 1, 0, 'C', True)
    pdf.cell(50, 7, "Severity Penalty", 1, 1, 'C', True)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    
    if not inspection_data["defects"]:
        pdf.cell(190, 7, "No critical micro-defects detected on this board.", 1, 1, 'C')
    else:
        for idx, defect in enumerate(inspection_data["defects"][:10]):
            fill = (idx % 2 == 0)
            pdf.set_fill_color(248, 249, 250)
            pdf.cell(30, 6, defect["id"], 1, 0, 'C', fill)
            pdf.cell(65, 6, defect["type"], 1, 0, 'L', fill)
            pdf.cell(45, 6, str(defect["area_px"]), 1, 0, 'C', fill)
            pdf.cell(50, 6, f"-{defect['severity_weight']} pts", 1, 1, 'C', fill)

    pdf.output(output_path)
    if os.path.exists(temp_img):
        os.remove(temp_img)
    return output_path