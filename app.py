import streamlit as st
import cv2
from inspection_engine import inspect_pcb
from pdf_generator import build_pdf_report

st.set_page_config(
    page_title="IntelliPCB | AI Optical Quality Control",
    page_icon="🔬",
    layout="wide"
)

# Custom High-End Styling
st.markdown("""
<style>
    .main { background-color: #0E1117; }
    .metric-card {
        background: linear-gradient(135deg, #1E2640 0%, #151A2E 100%);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #2B385E;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE & AUTHENTICATION -----------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

def login_form():
    st.markdown("<h2 style='text-align: center;'>🔐 IntelliPCB Enterprise Access</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_box"):
            user = st.text_input("Engineer Username", placeholder="e.g. lead_inspector")
            pwd = st.text_input("Password", type="password", placeholder="••••••••")
            submit = st.form_submit_button("Authenticate & Enter Portal", use_container_width=True)
            if submit:
                # Lightweight credentials for demo (can be linked to SQLite / Firebase)
                if user and pwd == "pcb2026":
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = user
                    st.rerun()
                else:
                    st.error("Invalid credentials. Try username with password: `pcb2026`")

if not st.session_state["authenticated"]:
    login_form()
    st.stop()

# ----------------- MAIN INTERFACE -----------------
st.sidebar.markdown(f"### 👤 Logged in as: **{st.session_state['username']}**")
if st.sidebar.button("🚪 Log Out", use_container_width=True):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Inspection Configuration")
batch_id = st.sidebar.text_input("Production Batch ID", value="BATCH-CIT-2026-X1")
input_mode = st.sidebar.radio("Image Acquisition Mode", ["📁 Upload High-Res Image", "📷 Laptop Webcam Capture"])

st.markdown("# 🔬 IntelliPCB — AI Optical Inspection Suite")
st.caption("Real-Time Micro-Defect Localization, Automated IPC-A-610 Scoring, and Compliance Reporting")

col_left, col_right = st.columns([1, 1])

inspected_image_bytes = None
reference_image_bytes = None

with col_left:
    st.markdown("### 1. Board Input Acquisition")
    if input_mode == "📁 Upload High-Res Image":
        uploaded_file = st.file_uploader("Upload Inspection PCB Image", type=["png", "jpg", "jpeg"])
        if uploaded_file:
            inspected_image_bytes = uploaded_file.read()
            st.image(inspected_image_bytes, caption="Uploaded Target Board", use_container_width=True)
    else:
        cam_file = st.camera_input("Capture Real PCB via Laptop Camera")
        if cam_file:
            inspected_image_bytes = cam_file.read()

    ref_file = st.file_uploader("Optional: Upload Golden Reference Board (Template Matching)", type=["png", "jpg", "jpeg"])
    if ref_file:
        reference_image_bytes = ref_file.read()

with col_right:
    st.markdown("### 2. AI Defect Detection & Analytics")
    if inspected_image_bytes:
        with st.spinner("Analyzing trace morphology and running defect classifier..."):
            results = inspect_pcb(inspected_image_bytes, reference_image_bytes)

        # Metrics Row
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric(label="Quality Score", value=f"{results['score']}/100")
        with m2:
            st.metric(label="Defects Detected", value=results['total_defects'])
        with m3:
            st.metric(label="Board Status", value=results['status'].split('-')[0])

        # Annotated Image
        annotated_rgb = cv2.cvtColor(results["annotated_bgr"], cv2.COLOR_BGR2RGB)
        st.image(annotated_rgb, caption="AI Annotated Defect Map (Color-Coded)", use_container_width=True)

        # Defect Table
        if results["defects"]:
            st.markdown("#### Identified Defect Details")
            st.dataframe(results["defects"], use_container_width=True)

        # Generate & Download PDF
        pdf_path = build_pdf_report(results, batch_id, st.session_state["username"])
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📄 Download ISO Inspection PDF Certificate",
                data=f,
                file_name=f"IntelliPCB_{batch_id}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    else:
        st.info("Upload or capture a PCB image on the left panel to begin automated inspection.")