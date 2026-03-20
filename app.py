"""
WhatsApp Chat Analyzer — Streamlit Web UI
"""
import hashlib
import hmac
import time
import os
import streamlit as st
import tempfile
from pathlib import Path

from wa_analyzer import parse_chat, transcribe_voices, build_timeline, analyze_conversation

st.set_page_config(page_title="WhatsApp Chat Analyzer", page_icon="💬", layout="wide")

# ── Auth ─────────────────────────────────────────────────────
_MAX_ATTEMPTS = 5
_LOCKOUT_SECS = 300  # 5 minutes
_SESSION_TIMEOUT = 3600  # 1 hour


def _check_auth() -> bool:
    """Return True if user is authenticated. Show login form otherwise."""
    now = time.time()

    # Session timeout
    if st.session_state.get("auth") and now - st.session_state.get("auth_time", 0) > _SESSION_TIMEOUT:
        st.session_state.pop("auth", None)
        st.info("Session expired. Please log in again.")

    if st.session_state.get("auth"):
        return True

    # Lockout
    locked_until = st.session_state.get("locked_until", 0)
    if now < locked_until:
        remaining = int(locked_until - now)
        st.error(f"Too many failed attempts. Try again in {remaining // 60}m {remaining % 60}s.")
        st.stop()

    # Login form
    st.markdown("## 🔒 Login")
    password = st.text_input("Password", type="password", key="pw_input")

    if st.button("Login", type="primary"):
        input_hash = hashlib.sha256(password.encode()).hexdigest()
        stored_hash = st.secrets.get("PASSWORD_HASH", "") or os.environ.get("PASSWORD_HASH", "")

        if stored_hash and hmac.compare_digest(input_hash, stored_hash):
            st.session_state["auth"] = True
            st.session_state["auth_time"] = now
            st.session_state["attempts"] = 0
            st.rerun()
        else:
            attempts = st.session_state.get("attempts", 0) + 1
            st.session_state["attempts"] = attempts
            remaining = _MAX_ATTEMPTS - attempts
            if attempts >= _MAX_ATTEMPTS:
                st.session_state["locked_until"] = now + _LOCKOUT_SECS
                st.session_state["attempts"] = 0
                st.error(f"Too many failed attempts. Locked for {_LOCKOUT_SECS // 60} minutes.")
            else:
                st.error(f"Wrong password. {remaining} attempt{'s' if remaining != 1 else ''} remaining.")

    return False


if not _check_auth():
    st.stop()

# ── Main App ─────────────────────────────────────────────────
st.title("💬 WhatsApp Chat Analyzer")
st.caption("Multilingual · English · Hebrew · Arabic")

# Logout button
with st.sidebar:
    st.header("Settings")
    model_size = st.selectbox(
        "Whisper model",
        ["tiny", "base", "small", "medium", "large"],
        index=2,
        help="Larger = more accurate but slower",
    )
    transcribe = st.checkbox("Transcribe voice messages", value=True)
    st.divider()
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

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
        chat_path = os.path.join(tmp, "chat.txt")
        with open(chat_path, "wb") as f:
            f.write(chat_file.read())

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
