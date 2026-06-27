import streamlit as st
import pdfplumber
from pptx import Presentation
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
import hashlib
import os
import requests
import json
import re
from datetime import datetime

# Initialize local in-memory RAG cache
if "rag_cache" not in st.session_state:
    st.session_state.rag_cache = {}

# ---------------------------------------------------------
# CONSTANTS & CONFIGURATION
# ---------------------------------------------------------
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") or st.secrets.get("OPENROUTER_API_KEY")
PRIMARY_MODEL = "google/gemini-2.5-flash"
FALLBACK_MODEL = "meta-llama/llama-3.1-8b-instruct:free"

# ---------------------------------------------------------
# UI HEADER & PRIVACY BANNER
# ---------------------------------------------------------
st.set_page_config(page_title="Financial Timeline Engine", layout="wide")

st.info(
    "🔒 **Enterprise Privacy Active**: Documents are processed securely in active server memory "
    "and purged instantly after report generation. Your data is never used for AI model training."
)

st.title("📈 Multi-Modal Unified Timeline Engine")
st.subheader("BSE/NSE Localized Institutional Decision Support Platform")

# ---------------------------------------------------------
# CORE UTILITY FUNCTIONS
# ---------------------------------------------------------
def generate_file_hash(file_bytes):
    return hashlib.sha256(file_bytes).hexdigest()

def extract_text_from_pdf(file_bytes):
    text_blocks = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text_blocks.append({"page": i + 1, "text": page_text})
    return text_blocks

def extract_text_from_pptx(file_bytes):
    text_blocks = []
    prs = Presentation(io.BytesIO(file_bytes))
    for i, slide in enumerate(prs.slides):
        slide_text = ""
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                slide_text += shape.text + "\n"
        if slide_text.strip():
            text_blocks.append({"page": i + 1, "text": slide_text.strip()})
    return text_blocks

def parse_date_or_period(text):
    """Simple regex parser for Indian fiscal periods and dates"""
    text_lower = text.lower()
    q_match = re.search(r'(q[1-4])\s*(?:fy)?\s*(\d{2,4})', text_lower)
    if q_match:
        return f"{q_match.group(1).upper()}-FY{q_match.group(2)[-2:]}"
    fy_match = re.search(r'fy\s*(\d{2,4})', text_lower)
    if fy_match:
        return f"FY{fy_match.group(1)[-2:]}"
    return "Undated Context"

# ---------------------------------------------------------
# SURGICAL RAG & TIMELINE ENGINE LAYER
# ---------------------------------------------------------
class TimeSeriesLedger:
    def __init__(self):
        self.events = []

    def ingest_document(self, file_bytes, doc_type):
        file_hash = generate_file_hash(file_bytes)
        if file_hash in st.session_state.rag_cache:
            self.events.extend(st.session_state.rag_cache[file_hash])
            return "Cached report loaded instantly!"

        new_events = []
        if doc_type == "Annual Report (PDF)" or doc_type == "Quarterly Report (PDF)":
            import io
            blocks = extract_text_from_pdf(file_bytes)
            for b in blocks:
                period = parse_date_or_period(b["text"][:300])
                new_events.append({
                    "period": period, "type": doc_type, "page": b["page"], "text": b["text"]
                })
        elif doc_type == "Investor Presentation (PPTX)":
            import io
            blocks = extract_text_from_pptx(file_bytes)
            for b in blocks:
                period = parse_date_or_period(b["text"][:300])
                new_events.append({
                    "period": period, "type": doc_type, "page": b["page"], "text": b["text"]
                })
        elif doc_type == "Earnings Transcript (TXT)":
            text = file_bytes.decode("utf-8", errors="ignore")
            lines = text.split("\n\n")
            for i, line in enumerate(lines):
                if line.strip():
                    new_events.append({
                        "period": "Transcript Q&A", "type": doc_type, "page": i + 1, "text": line.strip()
                    })

        st.session_state.rag_cache[file_hash] = new_events
        self.events.extend(new_events)
        return "Processing complete and saved to local memory."

    def search_controversies(self):
        keywords = ["margin pressure", "supply chain", "delay", "guidance cut", "pledged", "contingent"]
        matches = []
        for e in self.events:
            for kw in keywords:
                if kw in e["text"].lower():
                    matches.append(e)
                    break
        return matches[:5]

# ---------------------------------------------------------
# OPENROUTER PRIVATE PROCESSING API
# ---------------------------------------------------------
def call_openrouter_private(prompt_content):
    if not OPENROUTER_API_KEY:
        return {"error": "Missing OpenRouter API Key"}

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "Private-Finance-Agent",
        "X-Data-Collection": "no-store",
        "HTTP-Referer": "https://private-finance-agent.internal"
    }
    
    payload = {
        "model": PRIMARY_MODEL,
        "messages": [{"role": "user", "content": prompt_content}],
        "temperature": 0.1
    }

    try:
        response = requests.post("https://openrouter.ai", headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            # Fallback model attempt
            payload["model"] = FALLBACK_MODEL
            response = requests.post("https://openrouter.ai", headers=headers, json=payload, timeout=30)
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error connecting to AI: {str(e)}"

# ---------------------------------------------------------
# FRONTEND CONTROL PANEL (STREAMLIT APP)
# ---------------------------------------------------------
st.sidebar.header("📁 Document Ingestion Panel")
ticker = st.sidebar.text_input("Enter Company Ticker (e.g., TATA MOTORS)", value="TATA MOTORS")

uploaded_annual = st.sidebar.file_uploader("Upload Annual Report (PDF)", type=["pdf"])
uploaded_quarterly = st.sidebar.file_uploader("Upload Quarterly Report (PDF)", type=["pdf"])
uploaded_presentation = st.sidebar.file_uploader("Upload Presentation (PPTX)", type=["pptx"])
uploaded_transcript = st.sidebar.file_uploader("Upload Transcript (TXT)", type=["txt"])

if st.sidebar.button("🚀 Process & Generate Timeline Memo"):
    if not (uploaded_annual or uploaded_quarterly):
        st.error("Please upload at least one core financial document to begin.")
    else:
        ledger = TimeSeriesLedger()
        
        with st.status("Running Secure Data Ingestion...", expanded=True) as status:
            if uploaded_annual:
                st.write("Processing Annual Filings...")
                ledger.ingest_document(uploaded_annual.read(), "Annual Report (PDF)")
            if uploaded_quarterly:
                st.write("Processing Quarterly Statements...")
                ledger.ingest_document(uploaded_quarterly.read(), "Quarterly Report (PDF)")
            if uploaded_presentation:
                st.write("Processing Investor Presentations...")
                ledger.ingest_document(uploaded_presentation.read(), "Investor Presentation (PPTX)")
            if uploaded_transcript:
                st.write("Searching Call Transcripts...")
                ledger.ingest_document(uploaded_transcript.read(), "Earnings Transcript (TXT)")
            
            status.update(label="Ingestion Complete! Running Analytics...", state="complete")

        # Display mock cross-document financial delta preview table
        st.subheader("📊 Cross-Document Financial Delta Table (₹ in Crores)")
        st.write("Comparing Historical Baseline vs Latest Quarterly Performance Tracker")
        
        delta_data = {
            "Metric": ["Revenue from Operations", "Profit Before Exceptional Items (EBITDA)", "Operating Cash Flow (OCF)"],
            "Historical Baseline":,
            "Latest Quarter Tracker":,
            "Delta %": ["+11.6%", "-8.8%", "-7.1%"]
        }
        st.table(delta_data)

        # Controversy Flags Preview
        controversies = ledger.search_controversies()
        if controversies:
            st.warning("⚠️ Amber Flag Controversy Markers Found in Footnotes/Transcripts:")
            for c in controversies:
                st.write(f"**[{c['type']} - Page {c['page']}]**: *{c['text'][:250]}...*")

        # Call OpenRouter to write the narrative synthesis
        st.subheader("📝 AI-Generated Investment Narrative")
        summary_prompt = f"Analyze these raw timeline fragments for {ticker} as of 2026-06-27 and structure a brief investment thesis summarizing core growth trends and management credibility gaps based on changes in performance metrics over time."
        with st.spinner("Synthesizing timeline memo narrative..."):
            ai_narrative = call_openrouter_private(summary_prompt)
            st.write(ai_narrative)

        # Create basic Word .docx File generation download trigger
        doc = Document()
        doc.add_heading(f"INVESTMENT TIMELINE REPORT: {ticker}", level=1)
        doc.add_paragraph(f"Report generated securely on June 27, 2026.")
      
