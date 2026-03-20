"""
WhatsApp Chat Analyzer — Streamlit Web UI
"""
import streamlit as st
import tempfile
import os
from pathlib import Path

from wa_analyzer import parse_chat, transcribe_voices, build_timeline, analyze_conversation

st.set_page_config(page_title="WhatsApp Chat Analyzer", page_icon="💬", layout="wide")

st.title("💬 WhatsApp Chat Analyzer")
st.caption("Multilingual · English · Hebrew · Arabic")

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")
    model_size = st.selectbox(
        "Whisper model",
        ["tiny", "base", "small", "medium", "large"],
        index=2,
        help="Larger = more accurate but slower",
    )
    transcribe = st.checkbox("Transcribe voice messages", value=True)

# ── File uploads ─────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    chat_file = st.file_uploader("Upload chat export (.txt)", type=["txt"])
with col2:
    media_files = st.file_uploader(
        "Upload voice messages (optional)",
        type=["opus", "ogg", "m4a", "mp3", "aac"],
        accept_multiple_files=True,
    )

# ── Run analysis ─────────────────────────────────────────────
if chat_file and st.button("Analyze", type="primary", use_container_width=True):
    with tempfile.TemporaryDirectory() as tmp:
        # Save chat file
        chat_path = os.path.join(tmp, "chat.txt")
        with open(chat_path, "wb") as f:
            f.write(chat_file.read())

        # Save media files
        media_dir = os.path.join(tmp, "media")
        os.makedirs(media_dir, exist_ok=True)
        for mf in media_files:
            with open(os.path.join(media_dir, mf.name), "wb") as f:
                f.write(mf.read())

        with st.spinner("Parsing chat..."):
            messages = parse_chat(chat_path)

        if not messages:
            st.error("No messages found. Check your export file format.")
            st.stop()

        st.success(f"Loaded {len(messages)} messages")

        if transcribe and media_files:
            with st.spinner(f"Transcribing with Whisper ({model_size})…"):
                messages = transcribe_voices(messages, media_dir, model_size)

        timeline = build_timeline(messages)
        analysis = analyze_conversation(messages)

    # ── Results ───────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["Analysis", "Timeline", "Download"])

    with tab1:
        st.text(analysis)

    with tab2:
        st.text(timeline)

    with tab3:
        full = timeline + "\n" + analysis
        st.download_button(
            "Download full report (.txt)",
            data=full.encode("utf-8"),
            file_name="whatsapp_analysis.txt",
            mime="text/plain",
            use_container_width=True,
        )

elif not chat_file:
    st.info("Upload a WhatsApp chat export to get started.\n\n"
            "**How to export:** WhatsApp → Chat → ⋮ → More → Export chat → Without media")
