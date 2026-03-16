# WhatsApp Chat Analyzer 🎙️

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![OpenAI Whisper](https://img.shields.io/badge/AI-Whisper-green.svg)](https://github.com/openai/whisper)

A powerful tool to analyze WhatsApp chat exports with automatic voice message transcription using **OpenAI Whisper**. Gain deep insights into your conversations, detect friction points, and visualize communication patterns.

Built by [Aviel.AI](https://aviel.ai)

---

## 🚀 Key Features

- **📄 Multi-Language Support**: Parse WhatsApp `.txt` exports in Hebrew, English, and other languages.
- **🎙️ Local AI Transcription**: Transcribe voice messages (`.opus`, `.m4a`, `.ogg`) locally using Whisper—no API keys or cloud uploads required.
- **🕐 Integrated Timeline**: View a full chronological history with voice transcripts embedded directly into the conversation flow.
- **⚠️ Smart Signal Detection**: Automatically identify friction, urgency, and technical issues across 7 predefined categories.
- **📊 Detailed Analytics**: Get per-sender breakdowns, message counts, and sentiment indicators.
- **💾 Flexible Export**: Save results as human-readable `.txt` reports or raw `.json` for further data processing.

---

## 🛠️ Installation

### 1. Prerequisites
Ensure you have **Python 3.9+** and **FFmpeg** installed on your system.

- **macOS**: `brew install ffmpeg`
- **Ubuntu/Debian**: `sudo apt install ffmpeg`
- **Windows**: [Download FFmpeg](https://ffmpeg.org/download.html) and add it to your PATH.

### 2. Clone & Install
```bash
git clone https://github.com/Avielzi/whatsapp-chat-analyzer.git
cd whatsapp-chat-analyzer
pip install -r requirements.txt
```

---

## 📖 How to Use

### Step 1: Export Chat from WhatsApp
1. Open the chat on your phone.
2. Tap the menu (⋮) → **More** → **Export Chat**.
3. Select **Include Media**.
4. Transfer the exported folder (containing `_chat.txt` and audio files) to your computer.

### Step 2: Run the Analyzer
```bash
python wa_analyzer.py --chat "path/to/_chat.txt" --media "path/to/media_folder" --out results
```

### Command Line Options

| Flag | Default | Description |
|------|---------|-------------|
| `--chat` | *Required* | Path to the WhatsApp `.txt` export file. |
| `--media` | *Optional* | Folder containing voice message audio files. |
| `--model` | `medium` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large`. |
| `--out` | `analysis` | Output filename prefix (without extension). |
| `--no-transcribe`| `False` | Skip AI transcription and only generate the text timeline. |

---

## 📈 Example Output

### Timeline View
```text
💬 [15/03/2026 09:13] User A:
    This is a sample text message describing a situation.

🎙️  [15/03/2026 09:22] User A:
    📝 Transcript: I am sending a voice message to test the AI transcription.

💬 [15/03/2026 09:30] User B:
    Got it! The transcription looks perfect.
```

### Sentiment & Friction Analysis
| Category | Description / Example Triggers |
|----------|-------------------------------|
| `negative_sentiment` | Frustration, difficulty, or negative feedback |
| `unsatisfied` | Expectations not met, dissatisfaction |
| `time_sensitive` | Deadlines, delays, or high urgency |
| `clarification_needed`| Confusion or requests for more information |
| `system_issues` | Technical problems, bugs, or errors |
| `uncertainty` | Doubt, potential changes, or hesitation |
| `positive_feedback` ✅ | Satisfaction, approval, or gratitude |

---

## 📂 Use Cases
- **Freelancers**: Review client communication to improve service delivery.
- **Agencies**: Analyze project history for better retrospectives.
- **Support Teams**: Identify recurring pain points in customer interactions.
- **Personal**: Archive and search through important family or group memories.

---

## 🔒 Privacy First
All processing is done **100% locally** on your machine. No chat data, audio files, or transcripts are ever sent to any server. Your privacy is our priority.

---

## 📜 License
Distributed under the **MIT License**. See `LICENSE` for more information.

---

⭐ **Found this useful?** Give us a star on GitHub!
Developed with ❤️ by [Aviel.AI](https://aviel.ai)
