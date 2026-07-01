# =========================================================
# 1. IMPORTS & GLOBAL SETUP
# =========================================================
import streamlit as st
import requests
import io
from docx import Document
import time

# Set Page Config immediately at the absolute top
st.set_page_config(page_title="Multi-Modal Timeline Engine", layout="wide")

# Universal Model Configuration
PRIMARY_MODEL = "gemini-2.5-flash"
BACKUP_MODEL_1 = "openrouter/free"
BACKUP_MODEL_2 = "llama3-8b-8192"

# Initialize a session state tracking flag for actual AI connection success
if "ai_connected" not in st.session_state:
    st.session_state["ai_connected"] = False

if "provider_used" not in st.session_state:
    st.session_state["provider_used"] = "None"

# =========================================================
# 2. PERSISTENT AUTHENTICATION LAYER
# =========================================================
def get_persistent_auth():
    """Retrieve authentication state from browser URL parameters (persistent)."""
    return st.query_params.get("auth_token") == "financial_terminal_2026_verified"

def set_persistent_auth():
    """Set authentication state in browser URL parameters (persistent)."""
    st.query_params["auth_token"] = "financial_terminal_2026_verified"

def clear_persistent_auth():
    """Clear authentication state from browser URL parameters."""
    if "auth_token" in st.query_params:
        del st.query_params["auth_token"]

# =========================================================
# 3. FILE EXTRACTION LAYER (CACHED DATA MODULE)
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
# 4. GOOGLE AI STUDIO ENGINE (PRIMARY PROVIDER)
# =========================================================
def call_google_ai_studio(prompt_text):
    """Sends financial data requests to Google AI Studio via SDK with precise error handling."""
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    if not api_key:
        return None, "❌ Google API Key missing from Streamlit Secrets panel."
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(PRIMARY_MODEL)
        
        # System context
        system_prompt = "You are an elite institutional financial research analyst. Generate detailed, multi-paragraph investment memos and market trend outlines based on raw text analysis."
        full_prompt = f"{system_prompt}\n\nAnalyze the following corporate document data: {prompt_text}"
        
        response = model.generate_content(full_prompt, request_options={"timeout": 45})
        
        if response and response.text:
            st.session_state["ai_connected"] = True
            st.session_state["provider_used"] = "Google AI Studio"
            return response.text, "🟢 Generated via Google AI Studio"
        else:
            return None, "Google AI Studio returned empty content."
    
    except requests.exceptions.Timeout:
        return None, "Google AI Studio request timed out (45s)."
    except Exception as e:
        return None, f"Google AI Studio error: {str(e)}"

# =========================================================
# 5. OPENROUTER ENGINE (BACKUP PROVIDER 1 - 3-RETRY CIRCUIT)
# =========================================================
def call_openrouter_engine(prompt_text):
    """Sends financial data requests to OpenRouter securely with hard timeout retries."""
    api_key = st.secrets.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return None, "❌ OpenRouter API Key missing from Streamlit Secrets panel."
        
    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://streamlit.app",
        "X-Title": "Financial Timeline Engine"
    }
    
    payload = {
        "model": BACKUP_MODEL_1,
        "messages": [
            {"role": "system", "content": "You are an elite institutional financial research analyst. Generate detailed, multi-paragraph investment memos and market trend outlines based on raw text analysis."},
            {"role": "user", "content": prompt_text}
        ]
    }
    
    # Pass 1: Try Primary OpenRouter Model
    try:
        res = requests.post(endpoint, headers=headers, json=payload, timeout=45)
        if res.status_code == 200:
            data = res.json()
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                if content and content.strip():
                    st.session_state["ai_connected"] = True
                    st.session_state["provider_used"] = "OpenRouter"
                    return content, "🟢 Generated via OpenRouter"
        elif res.status_code in [429, 502, 503, 504]:
            # Rate limit or server busy - trigger fallback
            return None, f"OpenRouter returned HTTP {res.status_code} (rate limit/server busy)."
    except requests.exceptions.Timeout:
        return None, "OpenRouter request timed out (45s)."
    except requests.exceptions.ConnectionError:
        return None, "OpenRouter connection error."
    except Exception:
        pass  # Gracefully fall through to Pass 2

    # Pass 2: Fallback to Alternative Router Net with 2-second backoff
    try:
        time.sleep(2)
        res = requests.post(endpoint, headers=headers, json=payload, timeout=45)
        if res.status_code == 200:
            data = res.json()
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                if content and content.strip():
                    st.session_state["ai_connected"] = True
                    st.session_state["provider_used"] = "OpenRouter"
                    return content, "🟢 Generated via OpenRouter (Retry)"
        elif res.status_code in [429, 502, 503, 504]:
            return None, f"OpenRouter retry returned HTTP {res.status_code}."
    except Exception:
        pass  # Fall through to Pass 3

    # Pass 3: Final Attempt with 4-second backoff
    try:
        time.sleep(4)
        res = requests.post(endpoint, headers=headers, json=payload, timeout=45)
        if res.status_code == 200:
            data = res.json()
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                if content and content.strip():
                    st.session_state["ai_connected"] = True
                    st.session_state["provider_used"] = "OpenRouter"
                    return content, "🟢 Generated via OpenRouter (Final Attempt)"
    except Exception:
        pass

    return None, "🔴 OpenRouter failed after 3 retry attempts."

# =========================================================
# 6. GROQ ENGINE (BACKUP PROVIDER 2)
# =========================================================
def call_groq_engine(prompt_text):
    """Sends financial data requests to Groq with precise error handling."""
    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        return None, "❌ Groq API Key missing from Streamlit Secrets panel."
    
    endpoint = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": BACKUP_MODEL_2,
        "messages": [
            {"role": "system", "content": "You are an elite institutional financial research analyst. Generate detailed, multi-paragraph investment memos and market trend outlines based on raw text analysis."},
            {"role": "user", "content": prompt_text}
        ]
    }
    
    try:
        res = requests.post(endpoint, headers=headers, json=payload, timeout=45)
        
        if res.status_code == 200:
            data = res.json()
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                if content and content.strip():
                    st.session_state["ai_connected"] = True
                    st.session_state["provider_used"] = "Groq"
                    return content, "🟢 Generated via Groq"
            return None, "Groq returned empty content."
        elif res.status_code in [429, 502, 503, 504]:
            return None, f"Groq returned HTTP {res.status_code} (rate limit/server busy)."
        else:
            return None, f"Groq returned HTTP {res.status_code}."
    
    except requests.exceptions.Timeout:
        return None, "Groq request timed out (45s)."
    except requests.exceptions.ConnectionError:
        return None, "Groq connection error."
    except Exception as e:
        return None, f"Groq error: {str(e)}"

# =========================================================
# 7. TRIPLE-PROVIDER FALLBACK ORCHESTRATOR
# =========================================================
def call_ai_triple_fallback(prompt_text):
    """
    Orchestrates provider fallback: Google AI Studio → OpenRouter → Groq
    Returns (content, provider_status_message)
    """
    # Primary Provider: Google AI Studio
    content, status = call_google_ai_studio(prompt_text)
    if content:
        return content, status
    
    # Backup Provider 1: OpenRouter (with 3-retry circuit intact)
    content, status = call_openrouter_engine(prompt_text)
    if content:
        return content, status
    
    # Backup Provider 2: Groq
    content, status = call_groq_engine(prompt_text)
    if content:
        return content, status
    
    # All providers failed
    return None, "🔴 All AI providers exhausted. Please check your API keys and try again later."

# =========================================================
# 8. MICRO-UTILITY DOCUMENT EXPORTER (.DOCX EXPORTER)
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
# 9. MAIN WORKSPACE CONTROL LAYER
# =========================================================
def main():
    st.title("📈 Multi-Modal Financial Timeline Engine")
    
    # Dynamic status tracker logic
    google_key_check = st.secrets.get("GOOGLE_API_KEY", "")
    openrouter_key_check = st.secrets.get("OPENROUTER_API_KEY", "")
    groq_key_check = st.secrets.get("GROQ_API_KEY", "")
    
    providers_available = sum([bool(google_key_check), bool(openrouter_key_check), bool(groq_key_check)])
    
    if providers_available == 0:
        st.error("🔴 AI Status: Offline (No API Keys Configured)")
    elif st.session_state["ai_connected"]:
        st.success(f"🟢 AI Status: Connected & Verified Live (Provider: {st.session_state['provider_used']})")
    else:
        st.info(f"🟡 AI Status: {providers_available} Provider(s) Ready (Awaiting First Live Document Generation Connection)")

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
            with st.spinner("Synthesizing multi-modal financial data timeline memo via triple-provider fallback..."):
                prompt = f"Analyze the following corporate document data text carefully. Extract key event milestones, timelines, and potential controversy flags. Write a comprehensive multi-paragraph investment memo with strategic recommendations:\n\n{combined_raw_text}"
                ai_narrative_result, provider_status = call_ai_triple_fallback(prompt)
                
                if ai_narrative_result:
                    # Show AI Result
                    st.markdown("### 📝 Generated Strategic Investment Memo Text")
                    st.write(ai_narrative_result)
                    
                    # Display Provider Status
                    st.info(provider_status)
                    
                    # Render Working Document Exporter Module Download Button Link
                    docx_file_stream = generate_docx_download(ai_narrative_result)
                    st.download_button(
                        label="📥 Download Generated Investment Memo as Word Document (.docx)",
                        data=docx_file_stream,
                        file_name="Financial_Timeline_Investment_Memo.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                else:
                    st.error(provider_status)
    else:
        st.warning("📥 Welcome! Please slide open the left sidebar drawer and upload your corporate financial tracking documents to activate processing modules.")

    # Single Authorized Global Form Render at base

def check_login():
    # First check persistent authentication
    if get_persistent_auth():
        st.session_state["authenticated"] = True
        return True
    
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
                    set_persistent_auth()
                    st.success("✅ Authentication successful! Redirecting...")
                    st.rerun()
                else:
                    st.error("❌ Invalid Credentials")
        return False
    
    # Authenticated user - show logout button in sidebar
    with st.sidebar:
        st.markdown("---")
        if st.button("🔓 Log Out"):
            st.session_state["authenticated"] = False
            clear_persistent_auth()
            st.success("✅ Logged out successfully!")
            st.rerun()
    
    return True

if __name__ == "__main__":
    if check_login():
        main()
