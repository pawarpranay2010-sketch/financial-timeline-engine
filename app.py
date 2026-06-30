# =========================================================
# 1. IMPORTS & GLOBAL SETUP
# =========================================================
import streamlit as st
import requests
import io
from docx import Document

# Set Page Config immediately at the absolute top
st.set_page_config(page_title="Multi-Modal Timeline Engine", layout="wide")

# Universal Model Configuration
PRIMARY_MODEL = "google/gemma-4-31b-it:free"
FALLBACK_MODEL = "openrouter/free"

# Initialize a session state tracking flag for actual AI connection success
if "ai_connected" not in st.session_state:
    st.session_state["ai_connected"] = False

# =========================================================
# 2. FILE EXTRACTION LAYER (CACHED DATA MODULE)
# =========================================================
@st.cache_data(show_spinner=False)
def extract_document_data(uploaded_file):
    """Reads text lines from uploaded files safely."""
    if uploaded_file is None:
        return ""
    try:
        filename = uploaded_file.name.lower()
        if filename.endswith(".txt") or filename.endswith(".csv"):
            return uploaded_file.read().decode("utf-8")
        else:
            # Fallback simple reader for byte streams (Ready for PDF/PPT libraries later)
            return uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return f"Error reading file text content: {str(e)}"

# =========================================================
# 3. SECURE AI THESIS ENGINE (WITH TIMEOUT RETRIES)
# =========================================================
def call_openrouter_engine(prompt_text):
    """Sends financial data requests to OpenRouter securely with hard timeout retries."""
    api_key = st.secrets.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return "❌ OpenRouter API Key missing inside Streamlit Secrets panel."
        
    endpoint = "https://openrouter.ai"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://streamlit.app",
        "X-Title": "Financial Timeline Engine"
    }
    
    payload = {
        "model": PRIMARY_MODEL,
        "messages": [
            {"role": "system", "content": "You are an elite institutional financial research analyst. Generate detailed, multi-paragraph investment memos and market trend outlines based on raw text data."},
            {"role": "user", "content": prompt_text}
        ]
    }
    
    # Pass 1: Try Primary Google Gemma Intelligence
    try:
        res = requests.post(endpoint, headers=headers, json=payload, timeout=45)
        if res.status_code == 200:
            data = res.json()
            if "choices" in data and len(data["choices"]) > 0:
                st.session_state["ai_connected"] = True
                return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        pass  # Gracefully fall through to retry block below

    # Pass 2: Fallback to the Smart Router Net
    try:
        payload["model"] = FALLBACK_MODEL
        res = requests.post(endpoint, headers=headers, json=payload, timeout=45)
        if res.status_code == 200:
            data = res.json()
            if "choices" in data and len(data["choices"]) > 0:
                st.session_state["ai_connected"] = True
                return data["choices"][0]["message"]["content"]
    except Exception:
        return "🔴 AI server busy or experiencing high latency volume right now. Please tap regenerate to claim a fresh server slot link."
        
    return "⚠️ Primary AI endpoint returned an unusual response. Please check your token quota limit logs."

# =========================================================
# 4. MICRO-UTILITY DOCUMENT EXPORTER (.DOCX EXPORTER)
# =========================================================
def generate_docx_download(text_content):
    """Compiles the generated AI analysis report into a clean Word document download stream."""
    doc = Document()
    doc.add_heading("Institutional Investment Timeline Memo Narrative", level=1)
    doc.add_paragraph("Generated via Multi-Modal Timeline Engine Platform Hub")
    doc.add_paragraph("-" * 40)
    doc.add_paragraph(text_content)
    
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

st.success(
    "📣 We actively improve this platform based on user feedback. "
    "[Submit feedback or feature requests here](https://google.com)"
)


# =========================================================
# 6. MAIN WORKSPACE CONTROL LAYER
# =========================================================
def main():
    st.title("📈 Multi-Modal Financial Timeline Engine")
    
    # Dynamic status tracker logic
    api_key_check = st.secrets.get("OPENROUTER_API_KEY", "")
    if not api_key_check:
        st.error("🔴 AI Status: Offline (Missing OpenRouter Secrets Key Mapping)")
    elif st.session_state["ai_connected"]:
        st.success("🟢 AI Status: Connected & Verified Live")
    else:
        st.info("🟡 AI Status: API Key Loaded (Awaiting First Live Document Generation Connection)")

    # Sidebar Document Ingestion
    st.sidebar.header("📁 Document Ingestion Node")
    uploaded_files = st.sidebar.file_uploader(
        "Upload Corporate Reports or Data Sheets (.txt, .csv)", 
        type=["txt", "csv"], 
        accept_multiple_files=True
    )
    
    combined_raw_text = ""
    if uploaded_files:
        for f in uploaded_files:
            combined_raw_text += f"\n--- Start of File: {f.name} ---\n"
            combined_raw_text += extract_document_data(f)
            
        # Clean executive metric data grid view summary for corporate users
        st.subheader("📊 Ingested Data Grid Matrix")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(label="📄 Files Processed", value=len(uploaded_files))
        col2.metric(label="📑 Processing Status", value="Success")
        col3.metric(label="📊 Extracted Characters", value=len(combined_raw_text))
        col4.metric(label="🤖 Pipeline Node", value="Ready")
        
        # Trigger Action Analysis Button Link
        st.markdown("---")
        st.subheader("🔬 AI Narrative Generation Engine")
        if st.button("🚀 Process & Generate Timeline Memo Narrative"):
            with st.spinner("Synthesizing multi-modal financial data timeline memo via OpenRouter link..."):
                prompt = f"Analyze the following corporate document data text carefully. Extract key event milestones, timelines, and potential controversy flags. Write a comprehensive multi-paragraph financial research thesis memo:\n\n{combined_raw_text}"
                ai_narrative_result = call_openrouter_engine(prompt)
                
                # Show AI Result
                st.markdown("### 📝 Generated Strategic Investment Memo Text")
                st.write(ai_narrative_result)
                
                # Render Working Document Exporter Module Download Button Link
                if "❌" not in ai_narrative_result and "🔴" not in ai_narrative_result:
                    docx_file_stream = generate_docx_download(ai_narrative_result)
                    st.download_button(
                        label="📥 Download Generated Investment Memo as Word Document (.docx)",
                        data=docx_file_stream,
                        file_name="Financial_Timeline_Investment_Memo.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
    else:
        st.warning("📥 Welcome! Please slide open the left sidebar drawer and upload your corporate financial tracking documents to activate processing modules.")

    # Single Authorized Global Form Render at base
    render_feedback_panel()

if __name__ == "__main__":
    main()
    
