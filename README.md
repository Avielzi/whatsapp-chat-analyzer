# WhatsApp Chat Analyzer 🎙️

Analyze WhatsApp chat exports with automatic voice message transcription using Whisper.

Built by [Aviel.AI](https://aviel.ai)

## Features

- 📄 Parse WhatsApp `.txt` exports (Hebrew + English + any language)
- 🎙️ Transcribe voice messages locally using OpenAI Whisper (no API key needed)
- 🕐 Full timeline — sender · timestamp · content, voice transcripts inline
- ⚠️ Friction detection across 7 signal categories
- 👤 Per-sender breakdown (works with group chats too)
- 💾 Outputs: readable `.txt` + raw `.json`

## Installation

```bash
pip install openai-whisper

# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

## Usage

**Step 1 — Export from WhatsApp:**
Open chat → ⋮ → More → Export Chat → **With Media**
You'll get a folder with `chat.txt` + all `.opus` audio files.

**Step 2 — Run:**
```bash
python wa_analyzer.py --chat "chat.txt" --media "./WhatsApp Chat" --out analysis
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--chat` | required | Path to WhatsApp `.txt` export |
| `--media` | optional | Folder containing voice message files |
| `--model` | `medium` | Whisper model size: `tiny` `base` `small` `medium` `large` |
| `--out` | `analysis` | Output filename (no extension) |
| `--no-transcribe` | `False` | Skip transcription, output timeline only |

### Output example

```
============================================================
  Full Conversation Timeline
============================================================

💬 [15/03/2026 09:13] User A:
    This is a sample text message describing a situation.

🎙️  [15/03/2026 09:22] User A:
    📝 Transcript: This is a sample transcription of a voice message.

💬 [15/03/2026 09:30] User B:
    This is a sample response or update.

============================================================
  Conversation Analysis
============================================================

📊 Stats:
   Total messages: 50
   Voice messages: 10
   User A: 30 messages
   User B: 20 messages

⚠️  Friction moments (5):
   [09:13] User A: "Sample message with a friction signal..."
   🏷  frustration: [signal_word]

✅ Positive moments (3):
   [09:30] User B: "Sample positive feedback message"

👤 Per-sender breakdown:
   User A:
   Messages: 30 (10 voice)
   ⚠️  frustration: 4 messages
   ✅ positive: 1 message

   User B:
   Messages: 20 (0 voice)
   — No negative signals detected
```

## Signal Categories

| Category | Example triggers |
|----------|-----------------|
| `frustration` | mess, annoying, can't, fed up, exhausted |
| `dissatisfaction` | not happy, disappointing, not what I asked |
| `time_pressure` | urgent, taking too long, already a week |
| `confusion` | not clear, don't understand, can't find |
| `technical_issues` | broken, not working, crashed, error |
| `doubt_regret` | not sure, thinking of canceling, waste |
| `positive` ✅ | great, approved, happy, thank you |

## Use Cases

- **Freelancers** — review client conversations to improve communication
- **Agencies** — analyze project history before retrospectives
- **Support teams** — identify recurring friction patterns
- **Sales** — understand where deals stall

## Whisper Model Guide

| Model | Speed | Accuracy | VRAM |
|-------|-------|----------|------|
| `tiny` | fastest | lower | ~1GB |
| `base` | fast | decent | ~1GB |
| `small` | moderate | good | ~2GB |
| `medium` | slower | great | ~5GB |
| `large` | slowest | best | ~10GB |

For Hebrew, `medium` or `large` recommended.

## Privacy

All processing is **100% local**. No data is sent anywhere.  
Add your export folder to `.gitignore` — never commit real chat data.

## License

MIT © [Aviel.AI](https://aviel.ai)
