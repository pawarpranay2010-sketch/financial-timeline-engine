# =========================================================
# 1. IMPORTS & GLOBAL SETUP
# =========================================================
import streamlit as st
import requests
import io
import pandas as pd
from docx import Document
from docx import Document as ReadDocument
import json
from datetime import datetime

# Set Page Config immediately at the absolute top
st.set_page_config(page_title="Multi-Modal Timeline Engine", layout="wide")

# Universal Model Configuration
PRIMARY_MODEL = "openrouter/free"
FALLBACK_MODEL = "openrouter/free"

# Initialize a session state tracking flag for actual AI connection success
if "ai_connected" not in st.session_state:
    st.session_state["ai_connected"] = False

# Initialize extracted timeline data storage
if "timeline_data" not in st.session_state:
    st.session_state["timeline_data"] = []

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
        elif filename.endswith(".xlsx"):
            # EXCEL PARSER
            df_sheets = pd.read_excel(uploaded_file, sheet_name=None)
            excel_text = ""
            for sheet, df in df_sheets.items():
                excel_text += f"\n--- Excel Sheet: {sheet} ---\n" + df.to_string() + "\n"
            return excel_text
        elif filename.endswith(".docx"):
            # WORD PARSER
            word_doc = ReadDocument(uploaded_file)
            word_text = f"\n--- Word Document: {filename} ---\n"
            for para in word_doc.paragraphs:
                if para.text.strip():
                    word_text += para.text + "\n"
            return word_text
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
        
    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://streamlit.app",
        "X-Title": "Financial Timeline Engine"
    }
    
    payload = {
        "model": PRIMARY_MODEL,
        "messages": [
            {"role": "system", "content": "You are an elite Wall Street financial research analyst. Generate structured multi-section corporate reports with key dates, events, and milestones."},
            {"role": "user", "content": prompt_text}
        ]
    }
    
    # Pass 1: Try Primary Model
    try:
        res = requests.post(endpoint, headers=headers, json=payload, timeout=45)
        if res.status_code == 200:
            try:
                data = res.json()
                if "choices" in data and len(data["choices"]) > 0:
                    st.session_state["ai_connected"] = True
                    return data["choices"][0]["message"]["content"]
                else:
                    return "⚠️ OpenRouter returned an empty choices payload. Please try clicking the button again."
            except Exception:
                return "⚠️ OpenRouter server returned a malformed response. The free pool is heavily congested right now. Please try again in 10 seconds!"
        else:
            return f"❌ OpenRouter Connection Failed. Server status code: {res.status_code}. Please retry."
    except requests.exceptions.Timeout:
        pass  # Gracefully fall through to retry block below

    # Pass 2: Fallback to the Smart Router Net
    try:
        payload["model"] = FALLBACK_MODEL
        res = requests.post(endpoint, headers=headers, json=payload, timeout=45)
        if res.status_code == 200:
            try:
                data = res.json()
                if "choices" in data and len(data["choices"]) > 0:
                    st.session_state["ai_connected"] = True
                    return data["choices"][0]["message"]["content"]
                else:
                    return "⚠️ OpenRouter returned an empty choices payload. Please try clicking the button again."
            except Exception:
                return "⚠️ OpenRouter server returned a malformed response. The free pool is heavily congested right now. Please try again in 10 seconds!"
        else:
            return f"❌ OpenRouter Connection Failed. Server status code: {res.status_code}. Please retry."
    except Exception:
        return "🔴 AI server busy or experiencing high latency volume right now. Please tap regenerate to claim a fresh server slot link."
        
    return "⚠️ Primary AI endpoint returned an unusual response. Please check your token quota limit logs."

# =========================================================
# 3.5 TIMELINE EXTRACTION & PARSING ENGINE
# =========================================================
def extract_timeline_events(ai_narrative):
    """Parses AI narrative to extract structured timeline events."""
    try:
        # Send narrative back to AI to structure it
        api_key = st.secrets.get("OPENROUTER_API_KEY", "")
        if not api_key:
            return []
        
        endpoint = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://streamlit.app",
            "X-Title": "Financial Timeline Engine"
        }
        
        structuring_prompt = f"""Extract timeline events from this narrative and return as JSON array with objects containing: date (YYYY-MM-DD or YYYY-MM or YYYY), event (string), category (string), impact (string).

Narrative:
{ai_narrative}

Return ONLY valid JSON array, no markdown, no extra text."""
        
        payload = {
            "model": PRIMARY_MODEL,
            "messages": [{"role": "user", "content": structuring_prompt}],
            "temperature": 0.3
        }
        
        res = requests.post(endpoint, headers=headers, json=payload, timeout=45)
        if res.status_code == 200:
            data = res.json()
            if "choices" in data and len(data["choices"]) > 0:
                response_text = data["choices"][0]["message"]["content"]
                # Try to parse JSON
                try:
                    events = json.loads(response_text)
                    return events if isinstance(events, list) else []
                except:
                    return []
        return []
    except Exception:
        return []

# =========================================================
# 4. MICRO-UTILITY DOCUMENT EXPORTER (.DOCX EXPORTER)
# =========================================================
def generate_docx_download(text_content, timeline_data=None):
    """Compiles the generated AI analysis report into a clean Word document download stream."""
    doc = Document()
    doc.add_heading("Institutional Investment Timeline Memo Narrative", level=1)
    doc.add_paragraph("Generated via Multi-Modal Timeline Engine Platform Hub")
    doc.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph("-" * 40)
    
    doc.add_heading("Executive Summary", level=2)
    doc.add_paragraph(text_content)
    
    # Add timeline section if data exists
    if timeline_data and len(timeline_data) > 0:
        doc.add_heading("Extracted Timeline Events", level=2)
        for event in timeline_data:
            date_str = event.get("date", "N/A")
            event_name = event.get("event", "N/A")
            category = event.get("category", "N/A")
            impact = event.get("impact", "N/A")
            
            doc.add_paragraph(f"📅 {date_str}: {event_name}", style="List Bullet")
            doc.add_paragraph(f"Category: {category} | Impact: {impact}", style="List Bullet 2")
    
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

st.success(
    "📣 We actively improve this platform based on user feedback. "
    "[Submit feedback or feature requests here](https://google.com)"
)


# =========================================================
# 5. TIMELINE VISUALIZATION ENGINE
# =========================================================
def render_timeline_visualization(timeline_data):
    """Renders an interactive timeline visualization."""
    if not timeline_data or len(timeline_data) == 0:
        st.info("No timeline events extracted yet.")
        return
    
    st.subheader("📊 Timeline Visualization")
    
    # Create a dataframe for display
    df_timeline = pd.DataFrame(timeline_data)
    
    # Display as table
    st.dataframe(df_timeline, use_container_width=True, hide_index=True)
    
    # Create a simple timeline chart if we have dates
    if "date" in df_timeline.columns:
        try:
            # Convert dates to datetime for sorting
            df_timeline["date_obj"] = pd.to_datetime(df_timeline["date"], errors="coerce")
            df_timeline_sorted = df_timeline.dropna(subset=["date_obj"]).sort_values("date_obj")
            
            if len(df_timeline_sorted) > 0:
                st.line_chart(df_timeline_sorted.set_index("date")[["event"]].astype(str))
        except:
            pass

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
        "Upload Corporate Reports or Data Sheets (.txt, .csv, .pdf, .xlsx, .docx)", 
        type=["txt", "pdf", "csv", "xlsx", "docx"], 
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
                prompt = f"""Analyze the following corporate document data text carefully. Extract key event milestones, timelines, and potential controversy flags. Write a comprehensive multi-paragraph investment memo that identifies:
1. Key financial events and dates
2. Market movements and impacts
3. Risk factors and opportunities
4. Strategic implications

Document Data:
{combined_raw_text}

Generate a professional investment memo."""
                ai_narrative_result = call_openrouter_engine(prompt)
                
                # Show AI Result
                st.markdown("### 📝 Generated Strategic Investment Memo Text")
                st.write(ai_narrative_result)
                
                # Extract timeline events
                with st.spinner("Extracting timeline events..."):
                    timeline_events = extract_timeline_events(ai_narrative_result)
                    st.session_state["timeline_data"] = timeline_events
                
                # Render timeline visualization
                if timeline_events:
                    render_timeline_visualization(timeline_events)
                
                # Render Working Document Exporter Module Download Button Link
                if "❌" not in ai_narrative_result and "🔴" not in ai_narrative_result:
                    docx_file_stream = generate_docx_download(ai_narrative_result, timeline_events)
                    st.download_button(
                        label="📥 Download Generated Investment Memo as Word Document (.docx)",
                        data=docx_file_stream,
                        file_name="Financial_Timeline_Investment_Memo.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
    else:
        st.warning("📥 Welcome! Please slide open the left sidebar drawer and upload your corporate financial tracking documents to activate processing modules.")

def check_login():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.markdown("<h2 style='text-align: center;'>🔐 Institutional Terminal Access</h2>", unsafe_allow_html=True)
        col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
        with col_l2:
            input_user = st.text_input("Username")
            input_pass = st.text_input("Password", type="password")
            if st.button("🚀 Log In", use_container_width=True):
                if input_user == "admin" and input_pass == "financial_terminal_2026":
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("❌ Invalid Credentials")
        return False
    return True

if __name__ == "__main__":
    if check_login():
        main()
