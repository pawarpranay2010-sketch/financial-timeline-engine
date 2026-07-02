    success, result = _openrouter_request(prompt_text, PRIMARY_MODEL, system_prompt=system_prompt)
    if success:
        return result

    # Pass 2: Fallback model (retry on timeout OR any other failure)
    success, result = _openrouter_request(prompt_text, FALLBACK_MODEL, system_prompt=system_prompt)
    if success:
        return result

    if result == "TIMEOUT":
        return "ðŸ”´ AI server busy or experiencing high latency volume right now. Please tap regenerate to claim a fresh server slot link."
    return result


# ---------------------------------------------------------------------------
# Timeline extraction & parsing engine
# ---------------------------------------------------------------------------
def extract_timeline_events(ai_narrative):
    """Parses AI narrative to extract structured timeline events."""
    try:
        structuring_prompt = f"""Extract timeline events from this narrative and return as JSON array with objects containing: date (YYYY-MM-DD or YYYY-MM or YYYY), event (string), category (string), impact (string).

Narrative:
{ai_narrative}

Return ONLY valid JSON array, no markdown, no extra text."""

        success, result = _openrouter_request(structuring_prompt, PRIMARY_MODEL, temperature=0.3)
        if not success:
            return []

        # Strip markdown code fences if the model wrapped the JSON anyway
        # (this was previously missing, causing json.loads to silently
        # fail on fenced responses and always return an empty list).
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        try:
            events = json.loads(cleaned)
            return events if isinstance(events, list) else []
        except Exception:
            return []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Micro-utility document exporter (.DOCX exporter)
# ---------------------------------------------------------------------------
def generate_docx_download(text_content, timeline_data=None):
    """Compiles the generated AI analysis report into a clean Word document download stream."""
    doc = Document()

    doc.add_heading("Institutional Investment Research Memo", level=1)
    doc.add_paragraph("-" * 40)
    doc.add_heading("Executive Summary & Analysis", level=2)

    # Secure row cleaning loop to bypass oxml crashes.
    #
    # BUG FIX: the original code had a `for...else` here. A for-loop's
    # `else` clause runs whenever the loop finishes WITHOUT hitting a
    # `break` -- which was every single time, since there's no `break`
    # in the loop. That meant "No report content generated." was being
    # appended after every successful report, not just empty ones.
    # Replaced with a proper if/else on the outer content check.
    if text_content:
        clean_text_string = str(text_content)
        for line in clean_text_string.split('\n'):
            if line.strip():
                # Strip out invalid control characters safely
                sanitized_line = "".join(c for c in line if c.isprintable() or c in ['\t', '\n'])
                # Remove markdown formatting symbols
                sanitized_line = sanitized_line.replace('**', '').replace('__', '').replace('```', '')
                if sanitized_line.strip():
                    doc.add_paragraph(sanitized_line.strip())
    else:
        doc.add_paragraph("No report content generated.")

    # Add timeline section if data exists
    if timeline_data and len(timeline_data) > 0:
        doc.add_heading("Extracted Timeline Events", level=2)
        for event in timeline_data:
            date_str = event.get("date", "N/A")
            event_name = event.get("event", "N/A")
            category = event.get("category", "N/A")
            impact = event.get("impact", "N/A")

            # Sanitize timeline event strings
            date_str = "".join(c for c in str(date_str) if c.isprintable())
            event_name = "".join(c for c in str(event_name) if c.isprintable())
            category = "".join(c for c in str(category) if c.isprintable())
            impact = "".join(c for c in str(impact) if c.isprintable())

            doc.add_paragraph(f"ðŸ“… {date_str}: {event_name}", style="List Bullet")
            doc.add_paragraph(f"Category: {category} | Impact: {impact}", style="List Bullet 2")

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio


# ---------------------------------------------------------------------------
# Timeline visualization engine
# ---------------------------------------------------------------------------
def render_timeline_visualization(timeline_data):
    """Renders a simplified timeline visualization for mobile."""
    if not timeline_data or len(timeline_data) == 0:
        st.info("No timeline events extracted yet.")
        return

    st.subheader("ðŸ“Š Timeline Events")

    # Create a dataframe for display
    df_timeline = pd.DataFrame(timeline_data)

    # Display as table
    st.dataframe(df_timeline, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Main workspace control layer
# ---------------------------------------------------------------------------
def main():
    st.title("ðŸ“ˆ Financial Timeline Engine")

    # Dynamic status tracker logic
    api_key_check = st.secrets.get("OPENROUTER_API_KEY", "")
    if not api_key_check:
        st.error("ðŸ”´ AI Status: Offline (Missing OpenRouter Secrets Key Mapping)")
    elif st.session_state["ai_connected"]:
        st.success("ðŸŸ¢ AI Status: Connected & Verified Live")
    else:
        st.info("ðŸŸ¡ AI Status: API Key Loaded (Awaiting First Live Document Generation Connection)")

    # Sidebar Document Ingestion
    st.sidebar.header("ðŸ“ Document Ingestion")
    uploaded_files = st.sidebar.file_uploader(
        "Upload Financial Documents (.txt, .csv, .xlsx, .docx)",
        type=["txt", "csv", "xlsx", "docx"],
        accept_multiple_files=True
    )

    combined_raw_text = ""
    if uploaded_files:
        for f in uploaded_files:
            combined_raw_text += f"\n--- Start of File: {f.name} ---\n"
            combined_raw_text += extract_document_data(f)

    # Clean executive metric data grid view summary
    st.subheader("ðŸ“Š Ingested Data Summary")
    col1, col2 = st.columns(2)
    col1.metric(label="ðŸ“„ Files Processed", value=len(uploaded_files) if uploaded_files else 0)
    col2.metric(label="ðŸ“Š Extracted Characters", value=len(combined_raw_text))

    # Trigger Action Analysis Button Link
    st.markdown("---")
    st.subheader("ðŸ”¬ AI Analysis Engine")

    if st.button("ðŸš€ Generate Timeline Report"):
        # BUG FIX: previously there was no guard here -- clicking the
        # button with zero uploaded files would still call the AI with
        # an empty document string. Now we check up front.
        if not uploaded_files:
            st.warning("Please upload at least one financial document before generating a report.")
        else:
            with st.spinner("Processing document data and generating timeline..."):
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
                st.markdown("### ðŸ“ Generated Investment Memo")
                st.write(ai_narrative_result)

                is_error = ("âŒ" in ai_narrative_result) or ("ðŸ”´" in ai_narrative_result) or ("âš ï¸" in ai_narrative_result)

                timeline_events = []
                if not is_error:
                    # Extract timeline events
                    with st.spinner("Extracting timeline events..."):
                        timeline_events = extract_timeline_events(ai_narrative_result)
                        st.session_state["timeline_data"] = timeline_events

                    # Render timeline visualization
                    if timeline_events:
                        render_timeline_visualization(timeline_events)

                    # Render Working Document Exporter Module Download Button Link
                    docx_file_stream = generate_docx_download(ai_narrative_result, timeline_events)
                    st.download_button(
                        label="ðŸ“¥ Download as Word Document",
                        data=docx_file_stream,
                        file_name="Financial_Timeline_Investment_Memo.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                else:
                    # BUG FIX: this branch previously showed a misleading
                    # "please upload documents" message even when files
                    # WERE uploaded -- the real problem was an AI-call
                    # failure. Message corrected to reflect that.
                    st.warning("AI generation encountered an error. Please review the message above and try again.")


def check_login():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.markdown("ðŸ” Institutional Terminal Access")
        col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
        with col_l2:
            input_user = st.text_input("Username")
            input_pass = st.text_input("Password", type="password")
            if st.button("ðŸš€ Log In", use_container_width=True):
                if input_user == "admin" and input_pass == "financial_terminal_2026":
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("âŒ Invalid Credentials")
        return False
    return True


if __name__ == "__main__":
    if check_login():
        main()
