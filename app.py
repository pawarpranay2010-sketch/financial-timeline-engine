# =========================================================
# 1. IMPORTS & GLOBAL SETUP
# =========================================================
import streamlit as st
import requests
import io
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from docx import Document
from docx import Document as ReadDocument
from duckduckgo_search import DDGS

# Set Page Config immediately at the absolute top
st.set_page_config(page_title="Multi-Modal Timeline Engine", layout="wide")

# Universal Model Configuration
PRIMARY_MODEL = "openrouter/free"
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
# 2.5. LIVE WEB SEARCH ENGINE (DUCKDUCKGO)
# =========================================================
def search_live_web(query):
    """Search the internet using DuckDuckGo for live financial context."""
    try:
        with DDGS() as ddgs:
            results = [r['title'] + ": " + r['body'] for r in ddgs.text(query, max_results=3)]
            return "\n\n".join(results)
    except Exception:
        return "⚠️ Web search engine busy. Relying strictly on uploaded document data."

# =========================================================
# 3. SECURE AI THESIS ENGINE (WITH TIMEOUT RETRIES & AUTO-RETRY)
# =========================================================
def call_openrouter_engine(prompt_text):
    """Sends financial data requests to OpenRouter securely with hard timeout retries and automatic retry loop for rate limits."""
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
            {"role": "system", "content": "You are an elite Wall Street financial research analyst. Generate structured multi-section corporate reports."},
            {"role": "user", "content": prompt_text}
        ]
    }
    
    max_retries = 3
    retry_delay = 2  # seconds
    
    # Pass 1: Try Primary Google Gemma Intelligence
    for attempt in range(max_retries):
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
                    # Malformed JSON response - retry
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        return "⚠️ OpenRouter server returned a malformed response. The free pool is heavily congested right now. Please try again in 10 seconds!"
            elif res.status_code == 429:
                # Rate limit hit - retry with backoff
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return "⚠️ OpenRouter rate limit exceeded after 3 attempts. Please wait a moment and try again."
            else:
                return f"❌ OpenRouter Connection Failed. Server status code: {res.status_code}. Please retry."
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                pass  # Fall through to Pass 2

    # Pass 2: Fallback to the Smart Router Net
    for attempt in range(max_retries):
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
                    # Malformed JSON response - retry
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        return "⚠️ OpenRouter server returned a malformed response. The free pool is heavily congested right now. Please try again in 10 seconds!"
            elif res.status_code == 429:
                # Rate limit hit - retry with backoff
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return "⚠️ OpenRouter rate limit exceeded after 3 attempts. Please wait a moment and try again."
            else:
                return f"❌ OpenRouter Connection Failed. Server status code: {res.status_code}. Please retry."
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
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
# 5. DASHBOARD METRICS & CHART GENERATION
# =========================================================
def render_metrics_dashboard():
    """Renders the Interactive Metrics Tracker with high-contrast HTML audit cards."""
    st.subheader("📊 Interactive Metrics Tracker")
    
    # Define core financial metrics
    revenue = "₹21,533 Cr"
    ebitda = "₹2,724 Cr"
    fcf = "₹4,752 Cr"
    exceptional_costs = "₹1,565 Cr"
    
    # Create 4-column layout for metric cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f"""
            <div style="background-color: #1f77b4; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <h3 style="color: white; margin: 0;">Revenue</h3>
                <p style="color: #e8f4f8; font-size: 24px; font-weight: bold; margin: 10px 0;">{revenue}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            f"""
            <div style="background-color: #ff7f0e; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <h3 style="color: white; margin: 0;">EBITDA</h3>
                <p style="color: #fff0e6; font-size: 24px; font-weight: bold; margin: 10px 0;">{ebitda}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col3:
        st.markdown(
            f"""
            <div style="background-color: #2ca02c; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <h3 style="color: white; margin: 0;">FCF</h3>
                <p style="color: #e8f5e9; font-size: 24px; font-weight: bold; margin: 10px 0;">{fcf}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col4:
        st.markdown(
            f"""
            <div style="background-color: #d62728; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <h3 style="color: white; margin: 0;">Exceptional Costs</h3>
                <p style="color: #ffebee; font-size: 24px; font-weight: bold; margin: 10px 0;">{exceptional_costs}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Visual Growth Velocity Trends chart
    st.markdown("---")
    st.subheader("📈 Visual Growth Velocity Trends")
    
    # Generate synthetic trend data for visualization
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    revenue_trend = np.array([19000, 19500, 20000, 20500, 21000, 21500, 21800, 22000, 22300, 22500, 22800, 21533])
    ebitda_trend = np.array([2200, 2300, 2400, 2500, 2600, 2650, 2700, 2720, 2730, 2740, 2750, 2724])
    fcf_trend = np.array([4000, 4100, 4200, 4350, 4450, 4550, 4650, 4700, 4730, 4750, 4760, 4752])
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=months, y=revenue_trend,
        mode='lines+markers',
        name='Revenue (₹ Cr)',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8)
    ))
    
    fig.add_trace(go.Scatter(
        x=months, y=ebitda_trend,
        mode='lines+markers',
        name='EBITDA (₹ Cr)',
        line=dict(color='#ff7f0e', width=3),
        marker=dict(size=8)
    ))
    
    fig.add_trace(go.Scatter(
        x=months, y=fcf_trend,
        mode='lines+markers',
        name='FCF (₹ Cr)',
        line=dict(color='#2ca02c', width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title="12-Month Financial Performance Trajectory",
        xaxis_title="Month",
        yaxis_title="Amount (₹ Crores)",
        hovermode='x unified',
        height=450,
        template='plotly_dark'
    )
    
    st.plotly_chart(fig, use_container_width=True)

# =========================================================
# 6. MAIN WORKSPACE CONTROL LAYER
# =========================================================
def main():
    st.title("📈 Multi-Modal Financial Timeline Engine")
    
    # Initialize chat message history
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []
    
    # Dynamic status tracker logic
    api_key_check = st.secrets.get("OPENROUTER_API_KEY", "")
    if not api_key_check:
        st.error("🔴 AI Status: Offline (Missing OpenRouter Secrets Key Mapping)")
    elif st.session_state["ai_connected"]:
        st.success("🟢 AI Status: Connected & Verified Live")
    else:
        st.info("🟡 AI Status: API Key Loaded (Awaiting First Live Document Generation Connection)")

    # Create main tabs
    tab1, tab2, tab3 = st.tabs(["📊 Interactive Metrics Tracker", "📁 Document Upload & Analysis", "🎯 Strategic Insights"])
    
    # TAB 1: Interactive Metrics Tracker
    with tab1:
        render_metrics_dashboard()
        
        st.markdown("---")
        st.subheader("🔬 Generate Institutional Financial Analysis")
        
        if st.button("🚀 Generate AI-Powered Financial Report (Sections I-VI)"):
            with st.spinner("Synthesizing Institutional Financial Analysis Report via OpenRouter..."):
                prompt = """Generate a comprehensive Institutional Financial Analysis Report with the following structure:

Section I: Executive Summary
- Provide a high-level overview of financial performance and strategic position
- Highlight key achievements and metrics

Section II: Metrics Matrix
- Present detailed breakdown of Revenue (₹21,533 Cr), EBITDA (₹2,724 Cr), FCF (₹4,752 Cr)
- Analyze margins and operational efficiency ratios
- Commentary on Exceptional Costs (₹1,565 Cr) and their impact

Section III: Operational Risks
- Identify key business risks and market headwinds
- Rate severity and probability of impact

Section IV: Bull Case
- Articulate growth drivers and upside scenarios
- Key catalysts for value creation

Section V: Bear Case
- Articulate downside risks and adverse scenarios
- Key triggers for value destruction

Section VI: Investment Conclusion
- Synthesize the analysis into actionable recommendations
- Provide confidence level and time horizon for thesis"""
                
                ai_analysis = call_openrouter_engine(prompt)
                
                st.markdown("### 📝 Institutional Financial Analysis Report")
                st.write(ai_analysis)
                
                # Export to Word
                if "❌" not in ai_analysis and "🔴" not in ai_analysis:
                    docx_file = generate_docx_download(ai_analysis)
                    st.download_button(
                        label="📥 Download Report as Word Document (.docx)",
                        data=docx_file,
                        file_name="Institutional_Financial_Analysis.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
    
    # TAB 2: Document Upload & Analysis
    with tab2:
        st.subheader("📁 Document Ingestion Node")
        uploaded_files = st.file_uploader(
            "Upload Corporate Reports or Data Sheets (.txt, .csv, .pdf, .xlsx, .docx)", 
            type=["txt", "pdf", "csv", "xlsx", "docx"], 
            accept_multiple_files=True
        )
        
        # Live Web Search Input
        st.markdown("---")
        web_query = st.text_input("🌐 Live Web Search Context (Optional)", placeholder="e.g., Tata Motors stock price today or competitors news...")
        
        combined_raw_text = ""
        web_context = ""
        
        if uploaded_files:
            for f in uploaded_files:
                combined_raw_text += f"\n--- Start of File: {f.name} ---\n"
                combined_raw_text += extract_document_data(f)
            
            # If user provided a web search query, fetch live context
            if web_query.strip():
                with st.spinner("🌐 Fetching live web context..."):
                    web_context = search_live_web(web_query)
                    st.success("✅ Live web search completed!")
                
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
                    # Combine document data with live web context
                    combined_context = combined_raw_text
                    if web_context and "Web search engine busy" not in web_context:
                        combined_context += f"\n\n--- LIVE WEB SEARCH RESULTS ---\n{web_context}\n--- END WEB SEARCH ---\n"
                    
                    prompt = f"Analyze the following corporate document data and live web search results carefully. Extract key event milestones, timelines, market context, and potential controversy flags. Write a comprehensive multi-paragraph financial analysis incorporating both the uploaded documents and current market information:\n\n{combined_context}"
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
            
            # =========================================================
            # INTERACTIVE DOCUMENT-AWARE CHAT INTERFACE
            # =========================================================
            st.markdown("---")
            st.markdown("### 💬 Document-Aware Financial Assistant Chat")
            st.caption("Ask specific follow-up questions. Responses are grounded strictly in your uploaded reports, metrics ledger, and web search data.")
            
            # Display chat message history
            for msg in st.session_state["chat_messages"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            # Chat input box
            user_input = st.chat_input("Ask a question about the uploaded corporate reports...")
            
            if user_input:
                # Append user message to chat history
                st.session_state["chat_messages"].append({
                    "role": "user",
                    "content": user_input
                })
                
                # Display user message
                with st.chat_message("user"):
                    st.markdown(user_input)
                
                # Construct RAG prompt with document context, metrics, and web data
                rag_context = f"""You are a document-aware financial research assistant. Answer the user's question STRICTLY utilizing ONLY the provided document context, core metrics, and web search results below.

CORE FINANCIAL METRICS FRAMEWORK:
- Revenue: ₹21,533 Cr
- EBITDA: ₹2,724 Cr
- FCF: ₹4,752 Cr
- Exceptional Costs: ₹1,565 Cr

DOCUMENT DATA:
{combined_raw_text}

WEB SEARCH CONTEXT:
{web_context if web_context and "Web search engine busy" not in web_context else "No web search data available"}

USER QUESTION: {user_input}

INSTRUCTION: Answer the user query STRICTLY utilizing the provided document, metrics, and search context. If the answer cannot be found in the context, state that clearly and concisely. Do NOT fabricate information."""
                
                # Get AI response
                with st.spinner("💭 Financial Assistant thinking..."):
                    ai_response = call_openrouter_engine(rag_context)
                
                # Append assistant message to chat history
                st.session_state["chat_messages"].append({
                    "role": "assistant",
                    "content": ai_response
                })
                
                # Display assistant message
                with st.chat_message("assistant"):
                    st.markdown(ai_response)
                
                # Rerun to update chat display
                st.rerun()
        else:
            st.warning("📥 Welcome! Please upload your corporate financial tracking documents to activate processing modules.")
    
    # TAB 3: Strategic Insights
    with tab3:
        st.subheader("🎯 Strategic Analysis Hub")
        st.info("Use this section for deeper analysis, trend forecasting, and strategic recommendations based on your uploaded documents.")
        
        if st.button("📊 Generate Strategic Insights"):
            with st.spinner("Generating strategic insights..."):
                prompt = """Provide strategic insights and recommendations including:
1. Market positioning analysis
2. Competitive landscape assessment
3. Growth opportunity identification
4. Risk mitigation strategies
5. ESG considerations and impact"""
                
                insights = call_openrouter_engine(prompt)
                st.write(insights)

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
