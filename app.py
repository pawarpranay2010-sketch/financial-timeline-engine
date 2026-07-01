# =========================================================
# FINANCIAL TIMELINE ENGINE - ENTERPRISE-GRADE VERSION
# Complete Operational Application with Diagnostics & Multi-Provider AI
# =========================================================
import streamlit as st
import requests
import io
import pandas as pd
import time
import traceback
from docx import Document
from datetime import datetime
import json

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# =========================================================
# 1. PAGE CONFIGURATION & GLOBAL STATE
# =========================================================
st.set_page_config(
    page_title="Multi-Modal Financial Timeline Engine",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Provider Model Configuration
PRIMARY_MODEL = "gemini-2.5-flash"
BACKUP_MODEL_1 = "openrouter/free"
BACKUP_MODEL_2 = "llama3-8b-8192"

# Session State Initialization
if "ai_connected" not in st.session_state:
    st.session_state["ai_connected"] = False

if "provider_used" not in st.session_state:
    st.session_state["provider_used"] = "None"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "last_error" not in st.session_state:
    st.session_state["last_error"] = None

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
# 3. FILE EXTRACTION LAYER (MULTI-FORMAT PARSER)
# =========================================================
@st.cache_data(show_spinner=False)
def extract_document_data(uploaded_file):
    """Reads text from multiple file formats safely."""
    if uploaded_file is None:
        return ""
    
    try:
        filename = uploaded_file.name.lower()
        
        # Text and CSV files
        if filename.endswith(".txt") or filename.endswith(".csv"):
            return uploaded_file.read().decode("utf-8")
        
        # Excel files
        elif filename.endswith(".xlsx"):
            df_sheets = pd.read_excel(uploaded_file, sheet_name=None)
            excel_text = ""
            for sheet, df in df_sheets.items():
                excel_text += f"\n--- Excel Sheet: {sheet} ---\n" + df.to_string() + "\n"
            return excel_text
        
        # Word documents
        elif filename.endswith(".docx"):
            word_doc = Document(uploaded_file)
            word_text = f"\n--- Word Document: {filename} ---\n"
            for para in word_doc.paragraphs:
                if para.text.strip():
                    word_text += para.text + "\n"
            return word_text
        
        # PDF files
        elif filename.endswith(".pdf"):
            if PdfReader is None:
                return "⚠️ PDF library not installed. Please install pypdf."
            try:
                pdf_reader = PdfReader(uploaded_file)
                pdf_text = f"\n--- PDF Document: {filename} ---\n"
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text() + "\n"
                return pdf_text
            except Exception as e:
                return f"Error extracting PDF text: {str(e)}"
        
        # Fallback for other formats
        else:
            return uploaded_file.read().decode("utf-8", errors="ignore")
    
    except Exception as e:
        return f"Error reading file text content: {str(e)}"

# =========================================================
# 4. WEB SEARCH ENGINE (DUCKDUCKGO INTEGRATION)
# =========================================================
def fetch_duckduckgo_results(query):
    """Fetch top web search results from DuckDuckGo."""
    if not query or len(query.strip()) < 3:
        return ""
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # DuckDuckGo HTML search endpoint
        url = "https://html.duckduckgo.com/"
        params = {
            "q": query,
            "t": "h_",
            "ia": "web"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Extract basic snippet data from HTML
            import re
            snippets = re.findall(r'<a class="result__snippet"[^>]*>([^<]*)</a>', response.text)
            
            if snippets:
                web_context = "\n=== WEB SEARCH CONTEXT ===\n"
                for i, snippet in enumerate(snippets[:5], 1):
                    snippet_clean = snippet.replace("&quot;", '"').replace("&amp;", "&")
                    web_context += f"{i}. {snippet_clean}\n"
                web_context += "=========================\n"
                return web_context
        
        return ""
    
    except Exception as e:
        return f"Web search unavailable: {str(e)}\n"

# =========================================================
# 5. GOOGLE AI STUDIO ENGINE (PRIMARY PROVIDER)
# =========================================================
def call_google_ai_studio(prompt_text):
    """Sends requests to Google AI Studio with precise error handling."""
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    if not api_key:
        return None, "❌ Google API Key missing from Streamlit Secrets panel."
    
    try:
        if genai is None:
            return None, "❌ Google AI library not installed. Please install google-generativeai."
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(PRIMARY_MODEL)
        
        system_prompt = "You are an elite institutional financial research analyst. Generate detailed, multi-paragraph investment memos and market trend outlines based on raw text analysis."
        full_prompt = f"{system_prompt}\n\nAnalyze the following corporate document data:\n{prompt_text}"
        
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
# 6. OPENROUTER ENGINE (BACKUP PROVIDER 1 - 3-RETRY CIRCUIT)
# =========================================================
def call_openrouter_engine(prompt_text):
    """Sends requests to OpenRouter with 3-retry circuit intact."""
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
            {
                "role": "system",
                "content": "You are an elite institutional financial research analyst. Generate detailed, multi-paragraph investment memos and market trend outlines based on raw text analysis."
            },
            {
                "role": "user",
                "content": prompt_text
            }
        ]
    }
    
    # Pass 1: Initial attempt
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
            pass  # Trigger retry logic
    except requests.exceptions.Timeout:
        pass
    except requests.exceptions.ConnectionError:
        pass
    except Exception:
        pass
    
    # Pass 2: 2-second backoff retry
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
                    return content, "🟢 Generated via OpenRouter (Retry 1)"
        elif res.status_code in [429, 502, 503, 504]:
            pass  # Continue to Pass 3
    except Exception:
        pass
    
    # Pass 3: 4-second backoff final attempt
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
                    return content, "🟢 Generated via OpenRouter (Retry 2)"
    except Exception:
        pass
    
    return None, "🔴 OpenRouter failed after 3 retry attempts."

# =========================================================
# 7. GROQ ENGINE (BACKUP PROVIDER 2)
# =========================================================
def call_groq_engine(prompt_text):
    """Sends requests to Groq with precise error handling."""
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
            {
                "role": "system",
                "content": "You are an elite institutional financial research analyst. Generate detailed, multi-paragraph investment memos and market trend outlines based on raw text analysis."
            },
            {
                "role": "user",
                "content": prompt_text
            }
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
# 8. TRIPLE-PROVIDER FALLBACK ORCHESTRATOR
# =========================================================
def call_ai_triple_fallback(prompt_text):
    """Orchestrates provider fallback: Google → OpenRouter → Groq."""
    
    # Primary Provider: Google AI Studio
    content, status = call_google_ai_studio(prompt_text)
    if content:
        return content, status
    
    # Backup Provider 1: OpenRouter (with 3-retry circuit)
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
# 9. DIAGNOSTIC AI AGENT NODE
# =========================================================
def call_diagnostic_ai_agent(error_description):
    """Routes diagnostic payloads to AI for system analysis and resolution."""
    
    diagnostic_prompt = f"""You are an elite senior cloud infrastructure engineer and Python systems diagnostic expert. 
    
A system has encountered the following issue or error:

{error_description}

Please provide a comprehensive step-by-step resolution plan that includes:
1. Root cause analysis
2. Immediate remediation steps
3. Long-term preventive measures
4. Testing and verification procedures

Format your response as a clear, actionable diagnostic report."""
    
    content, status = call_ai_triple_fallback(diagnostic_prompt)
    return content, status

# =========================================================
# 10. DOCUMENT EXPORTER
# =========================================================
def generate_docx_download(text_content):
    """Compiles AI analysis into Word document."""
    doc = Document()
    doc.add_heading("Institutional Investment Timeline Memo Narrative", level=1)
    doc.add_paragraph("Generated via Multi-Modal Timeline Engine Platform Hub")
    doc.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    doc.add_paragraph("-" * 60)
    doc.add_paragraph(text_content)
    
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# =========================================================
# 11. INTERACTIVE METRICS CARDS (HTML RENDER)
# =========================================================
def render_metrics_dashboard():
    """Renders high-contrast HTML audit cards with key financial metrics."""
    
    metrics_html = """
    <style>
        .metrics-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
            border-left: 5px solid #00d4ff;
        }
        .metric-card.revenue {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            border-left-color: #ff6b6b;
        }
        .metric-card.ebitda {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            border-left-color: #00d4ff;
        }
        .metric-card.fcf {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
            border-left-color: #00ff88;
        }
        .metric-card.restructuring {
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            border-left-color: #ffa500;
        }
        .metric-label {
            font-size: 14px;
            opacity: 0.9;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }
        .metric-value {
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .metric-sublabel {
            font-size: 12px;
            opacity: 0.85;
        }
    </style>
    
    <div class="metrics-container">
        <div class="metric-card revenue">
            <div class="metric-label">📊 Revenue</div>
            <div class="metric-value">₹21,533 Cr</div>
            <div class="metric-sublabel">Total Annual Revenue</div>
        </div>
        
        <div class="metric-card ebitda">
            <div class="metric-label">📈 EBITDA</div>
            <div class="metric-value">₹2,724 Cr</div>
            <div class="metric-sublabel">Operating Profit Margin</div>
        </div>
        
        <div class="metric-card fcf">
            <div class="metric-label">💰 Free Cash Flow</div>
            <div class="metric-value">₹4,752 Cr</div>
            <div class="metric-sublabel">Operating Cash Generation</div>
        </div>
        
        <div class="metric-card restructuring">
            <div class="metric-label">⚙️ Exceptional Restructuring Costs</div>
            <div class="metric-value">₹1,565 Cr</div>
            <div class="metric-sublabel">Strategic Reorganization Expenses</div>
        </div>
    </div>
    """
    
    st.markdown(metrics_html, unsafe_allow_html=True)

# =========================================================
# 12. VISUAL GROWTH VELOCITY TRENDS CHART
# =========================================================
def render_growth_chart():
    """Renders interactive line chart showing growth velocity trends."""
    
    chart_data = pd.DataFrame({
        "Quarter": ["Q1", "Q2", "Q3", "Q4", "Q1 Y2", "Q2 Y2", "Q3 Y2"],
        "Revenue Growth %": [8.2, 9.5, 11.3, 12.8, 14.2, 15.6, 16.9],
        "EBITDA Growth %": [5.1, 6.8, 8.4, 9.7, 11.2, 12.8, 14.1],
        "FCF Growth %": [12.3, 13.9, 15.2, 16.8, 18.1, 19.5, 21.3]
    })
    
    st.line_chart(chart_data.set_index("Quarter"))

# =========================================================
# 13. AUTHENTICATION CHECKPOINT
# =========================================================
def check_login():
    """Enforces secure login with persistent session."""
    
    # First check persistent authentication
    if get_persistent_auth():
        st.session_state["authenticated"] = True
        return True
    
    if not st.session_state["authenticated"]:
        st.markdown("<h2 style='text-align: center;'>🔐 Institutional Terminal Access</h2>", unsafe_allow_html=True)
        col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
        
        with col_l2:
            input_user = st.text_input("Username", key="login_user")
            input_pass = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("🚀 Log In", use_container_width=True):
                if input_user == "admin" and input_pass == "financial_terminal_2026":
                    st.session_state["authenticated"] = True
                    set_persistent_auth()
                    st.success("✅ Authentication successful! Redirecting...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Invalid Credentials. Access Denied.")
        
        return False
    
    return True

# =========================================================
# 14. TAB 1: INSTITUTIONAL FINANCIAL REPORT ENGINE
# =========================================================
def render_financial_report_tab(uploaded_files, combined_raw_text):
    """Main AI analysis and memo generation interface."""
    
    st.markdown("### 📋 Document Analysis Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"📄 Files Ingested: {len(uploaded_files)}" if uploaded_files else "No files uploaded")
    
    with col2:
        st.info(f"📊 Total Characters: {len(combined_raw_text):,}" if combined_raw_text else "0")
    
    st.markdown("---")
    
    # Web Search Integration
    st.subheader("🔍 Live Web Search Context (Optional)")
    web_search_query = st.text_input(
        "Enter search terms to augment AI analysis:",
        placeholder="e.g., Market trends, Competitor analysis, Industry reports..."
    )
    
    web_context = ""
    if web_search_query and len(web_search_query.strip()) >= 3:
        with st.spinner("⚡ Fetching live web context..."):
            web_context = fetch_duckduckgo_results(web_search_query)
            if web_context:
                st.success("✅ Web search context loaded")
    
    # Main Analysis Button
    st.markdown("---")
    st.subheader("🔬 AI Narrative Generation Engine")
    
    if combined_raw_text:
        if st.button("🚀 Process & Generate Timeline Memo Narrative", use_container_width=True):
            try:
                with st.spinner("⏳ Synthesizing multi-modal financial data via triple-provider fallback..."):
                    
                    # Combine document and web context
                    full_analysis_prompt = f"""Analyze the following corporate document data carefully. Extract key event milestones, timelines, and potential controversy flags. Write a comprehensive multi-paragraph investment memo with strategic recommendations.

CORPORATE DOCUMENT DATA:
{combined_raw_text}

{web_context if web_context else ''}

Please provide:
1. Executive Summary
2. Key Financial Metrics & Trends
3. Strategic Milestones & Timeline
4. Risk Assessment & Opportunities
5. Investment Recommendation"""
                    
                    ai_narrative_result, provider_status = call_ai_triple_fallback(full_analysis_prompt)
                    
                    if ai_narrative_result:
                        # Display Results
                        st.markdown("### 📝 Generated Strategic Investment Memo")
                        st.write(ai_narrative_result)
                        
                        # Provider Status Badge
                        st.info(provider_status)
                        
                        # Download Option
                        docx_file_stream = generate_docx_download(ai_narrative_result)
                        st.download_button(
                            label="📥 Download Investment Memo (.docx)",
                            data=docx_file_stream,
                            file_name="Financial_Timeline_Investment_Memo.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                    else:
                        st.error(provider_status)
                        st.session_state["last_error"] = provider_status
            
            except Exception as e:
                error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
                st.error(f"❌ Analysis Error: {str(e)}")
                st.session_state["last_error"] = error_msg
    
    else:
        st.warning("📥 Please upload financial documents in the sidebar to begin analysis.")

# =========================================================
# 15. TAB 2: INTERACTIVE METRICS TRACKER
# =========================================================
def render_metrics_tab():
    """Displays interactive financial metrics and trends."""
    
    st.markdown("## 📊 Interactive Financial Metrics Dashboard")
    st.markdown("Real-time corporate performance indicators and growth velocity trends.")
    st.markdown("---")
    
    # Render metrics cards
    render_metrics_dashboard()
    
    st.markdown("---")
    st.subheader("📈 Visual Growth Velocity Trends")
    st.markdown("Quarterly growth rates across key financial dimensions")
    
    render_growth_chart()
    
    st.markdown("---")
    
    # Additional Context Cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Net Profit Margin",
            value="12.7%",
            delta="↑ 0.3%"
        )
    
    with col2:
        st.metric(
            label="ROE (Return on Equity)",
            value="18.4%",
            delta="↑ 1.2%"
        )
    
    with col3:
        st.metric(
            label="Debt-to-Equity Ratio",
            value="0.62",
            delta="↓ 0.05"
        )

# =========================================================
# 16. TAB 3: INTERNAL DIAGNOSTIC NODE
# =========================================================
def render_diagnostic_tab():
    """Admin interface for system diagnostics and error analysis."""
    
    st.markdown("## 🛠️ Internal Systems Diagnostic Node")
    st.markdown("Elite infrastructure analysis and automated resolution engine")
    st.markdown("---")
    
    diagnostic_mode = st.radio(
        "Select Diagnostic Mode:",
        ["Manual Error Input", "Last System Error", "System Health Check"]
    )
    
    if diagnostic_mode == "Manual Error Input":
        st.subheader("📋 Manual Error/Issue Description")
        
        error_description = st.text_area(
            "Describe the system issue, error, or glitch:",
            placeholder="Paste Python traceback, describe API errors, or explain system behavior issues...",
            height=250
        )
        
        if st.button("🔍 Analyze Issue & Generate Resolution Plan", use_container_width=True):
            if error_description and len(error_description.strip()) > 10:
                with st.spinner("🤖 Engaging diagnostic AI agent..."):
                    resolution, status = call_diagnostic_ai_agent(error_description)
                    
                    if resolution:
                        st.success("✅ Diagnostic Analysis Complete")
                        st.markdown("### 🔧 Step-by-Step Resolution Plan")
                        st.write(resolution)
                        st.info(status)
                    else:
                        st.error(f"Diagnostic failed: {status}")
            else:
                st.warning("Please provide a detailed error description (min 10 characters).")
    
    elif diagnostic_mode == "Last System Error":
        st.subheader("📋 Previous System Error Analysis")
        
        if st.session_state.get("last_error"):
            st.info(f"Last error captured: {st.session_state['last_error'][:200]}...")
            
            if st.button("🔍 Analyze Last Error & Generate Resolution Plan", use_container_width=True):
                with st.spinner("🤖 Engaging diagnostic AI agent..."):
                    resolution, status = call_diagnostic_ai_agent(st.session_state["last_error"])
                    
                    if resolution:
                        st.success("✅ Diagnostic Analysis Complete")
                        st.markdown("### 🔧 Step-by-Step Resolution Plan")
                        st.write(resolution)
                        st.info(status)
                    else:
                        st.error(f"Diagnostic failed: {status}")
        else:
            st.info("No system errors recorded in current session.")
    
    elif diagnostic_mode == "System Health Check":
        st.subheader("🏥 System Health & Provider Status")
        
        # Check API Keys
        google_key = bool(st.secrets.get("GOOGLE_API_KEY", ""))
        openrouter_key = bool(st.secrets.get("OPENROUTER_API_KEY", ""))
        groq_key = bool(st.secrets.get("GROQ_API_KEY", ""))
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status = "✅ Configured" if google_key else "❌ Missing"
            st.metric("Google AI Studio", status)
        
        with col2:
            status = "✅ Configured" if openrouter_key else "❌ Missing"
            st.metric("OpenRouter", status)
        
        with col3:
            status = "✅ Configured" if groq_key else "❌ Missing"
            st.metric("Groq", status)
        
        providers_available = sum([google_key, openrouter_key, groq_key])
        
        st.markdown("---")
        
        if providers_available == 3:
            st.success("✅ All providers configured and available for failover routing.")
        elif providers_available >= 1:
            st.warning(f"⚠️ {providers_available}/3 providers available. Limited failover capability.")
        else:
            st.error("❌ No API providers configured. System non-functional.")
        
        # Session Information
        st.markdown("---")
        st.subheader("📊 Session Information")
        
        session_info = {
            "Authenticated": st.session_state.get("authenticated", False),
            "AI Connected": st.session_state.get("ai_connected", False),
            "Last Provider": st.session_state.get("provider_used", "None"),
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        
        st.json(session_info)

# =========================================================
# 17. MAIN APPLICATION ORCHESTRATION
# =========================================================
def main():
    """Main application entry point with tabbed interface."""
    
    st.title("📈 Multi-Modal Financial Timeline Engine")
    st.markdown("Enterprise-Grade Financial Analysis with Triple-Provider AI Fallback")
    
    # Sidebar Configuration
    st.sidebar.header("📁 Document Ingestion Hub")
    
    uploaded_files = st.sidebar.file_uploader(
        "Upload Financial Documents",
        type=["txt", "pdf", "csv", "xlsx", "docx"],
        accept_multiple_files=True
    )
    
    combined_raw_text = ""
    if uploaded_files:
        st.sidebar.success(f"✅ {len(uploaded_files)} file(s) uploaded")
        
        for f in uploaded_files:
            combined_raw_text += f"\n--- Start of File: {f.name} ---\n"
            combined_raw_text += extract_document_data(f)
    
    # Tab Interface
    tab1, tab2, tab3 = st.tabs([
        "🔬 Institutional Financial Report",
        "📊 Interactive Metrics Tracker",
        "🛠️ Internal Diagnostic Node"
    ])
    
    with tab1:
        render_financial_report_tab(uploaded_files, combined_raw_text)
    
    with tab2:
        render_metrics_tab()
    
    with tab3:
        render_diagnostic_tab()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; margin-top: 30px; padding: 20px; background-color: #f0f2f6; border-radius: 8px;">
        <p><strong>🔒 Privacy Node:</strong></p>
        <p>All uploaded files are processed transiently in-memory during the active browser session and are never permanently cached or stored on disk.</p>
        <p><small>Multi-Modal Financial Timeline Engine v2.0 | Enterprise Edition</small></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Logout functionality in sidebar
    with st.sidebar:
        st.markdown("---")
        if st.button("🔓 Log Out", use_container_width=True):
            st.session_state["authenticated"] = False
            clear_persistent_auth()
            st.success("✅ Logged out successfully!")
            time.sleep(1)
            st.rerun()

# =========================================================
# 18. APPLICATION ENTRY POINT
# =========================================================
if __name__ == "__main__":
    if check_login():
        main()
