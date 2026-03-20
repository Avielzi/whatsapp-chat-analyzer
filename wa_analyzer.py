#!/usr/bin/env python3
"""
WhatsApp Chat Analyzer + Voice Transcriber (Multilingual Edition)
=================================================================
Analyzes WhatsApp export, transcribes voice messages with Whisper,
and generates a full timeline + conversation analysis.
Supports English, Hebrew, and Arabic with automatic signal detection.

Usage:
    pip install openai-whisper
    python wa_analyzer.py --chat "path/to/chat.txt" --media "path/to/media_folder"

Requirements:
    - Python 3.9+
    - openai-whisper  (pip install openai-whisper)
    - ffmpeg          (brew install ffmpeg / apt install ffmpeg)
"""

import argparse
import re
import os
import json
from pathlib import Path
from datetime import datetime


# ─── Patterns ───────────────────────────────────────────────
# WhatsApp export format (Hebrew/LTR):
# [DD/MM/YYYY, HH:MM:SS] Name: message
# or: DD/MM/YYYY, HH:MM - Name: message
MSG_PATTERN = re.compile(
    r'[\[‎]?(\d{1,2}[./]\d{1,2}[./]\d{2,4})[,،]\s*(\d{1,2}:\d{2}(?::\d{2})?)[\]‎]?\s*[-–]\s*([^:]+):\s*(.*)',
    re.MULTILINE
)
VOICE_PATTERN = re.compile(r'<attached:\s*(.*\.(?:opus|ogg|m4a|mp3|aac))\s*>', re.IGNORECASE)
OMITTED_PATTERN = re.compile(r'(audio omitted|voice message|הודעה קולית|קובץ קולי|رسالة صوتية)', re.IGNORECASE)


def detect_language(text: str) -> str:
    """Basic language detection based on character sets."""
    hebrew_chars = len(re.findall(r'[\u0590-\u05FF]', text))
    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    
    if hebrew_chars > arabic_chars and hebrew_chars > english_chars:
        return "Hebrew"
    elif arabic_chars > hebrew_chars and arabic_chars > english_chars:
        return "Arabic"
    elif english_chars > 0:
        return "English"
    return "Unknown"


def parse_chat(txt_path: str) -> list[dict]:
    """Parse WhatsApp .txt export into list of message dicts."""
    if not os.path.exists(txt_path):
        print(f"Error: File {txt_path} not found.")
        return []

    with open(txt_path, 'r', encoding='utf-8') as f:
        raw = f.read()

    messages = []
    current = None

    for line in raw.splitlines():
        m = MSG_PATTERN.match(line)
        if m:
            if current:
                messages.append(current)
            date_str, time_str, sender, body = m.groups()
            current = {
                'date': date_str.strip(),
                'time': time_str.strip(),
                'sender': sender.strip(),
                'body': body.strip(),
                'is_voice': False,
                'voice_file': None,
                'transcript': None,
                'detected_lang': detect_language(body.strip())
            }
            # Detect voice message
            vm = VOICE_PATTERN.search(body)
            if vm:
                current['is_voice'] = True
                current['voice_file'] = vm.group(1).strip()
            elif OMITTED_PATTERN.search(body):
                current['is_voice'] = True
        elif current:
            # Continuation line
            current['body'] += '\n' + line
            current['detected_lang'] = detect_language(current['body'])

    if current:
        messages.append(current)

    return messages


def find_voice_file(filename: str, media_dir: str) -> str | None:
    """Search for voice file in media directory (handles renamed files)."""
    media_path = Path(media_dir)
    if not media_path.exists():
        return None
        
    # Exact match
    exact = media_path / filename
    if exact.exists():
        return str(exact)
    # Search by name stem
    stem = Path(filename).stem
    for ext in ['.opus', '.ogg', '.m4a', '.mp3', '.aac']:
        candidates = list(media_path.glob(f'*{stem}*{ext}'))
        if candidates:
            return str(candidates[0])
    return None


def transcribe_voices(messages: list[dict], media_dir: str, model_size: str = 'medium') -> list[dict]:
    """Transcribe all voice messages using Whisper."""
    voice_msgs = [m for m in messages if m['is_voice']]
    if not voice_msgs:
        print("No voice messages found.")
        return messages

    print(f"\n🎙️  Found {len(voice_msgs)} voice messages. Loading Whisper ({model_size})...")
    try:
        import whisper
    except ImportError:
        print("❌ Whisper not installed. Run: pip install openai-whisper")
        return messages

    try:
        model = whisper.load_model(model_size)
        print(f"✅ Whisper model '{model_size}' loaded.")
    except Exception as e:
        print(f"❌ Error loading Whisper model: {e}")
        return messages

    for i, msg in enumerate(voice_msgs, 1):
        audio_path = None
        if msg['voice_file'] and media_dir:
            audio_path = find_voice_file(msg['voice_file'], media_dir)

        if not audio_path:
            print(f"  [{i}/{len(voice_msgs)}] ⚠️  File not found: {msg.get('voice_file','unknown')} — skipping")
            msg['transcript'] = '[Voice file not found]'
            continue

        print(f"  [{i}/{len(voice_msgs)}] Transcribing: {os.path.basename(audio_path)}...")
        try:
            # Let Whisper detect the language automatically
            result = model.transcribe(audio_path, task='transcribe')
            transcript = result['text'].strip()
            msg['transcript'] = transcript
            msg['detected_lang'] = detect_language(transcript)
            print(f"          ✅ [{msg['detected_lang']}] {transcript[:80]}{'...' if len(transcript)>80 else ''}")
        except Exception as e:
            msg['transcript'] = f'[Transcription error: {e}]'
            print(f"          ❌ Error: {e}")

    return messages


def build_timeline(messages: list[dict]) -> str:
    """Build readable timeline with transcripts inline."""
    lines = []
    lines.append("=" * 60)
    lines.append("  Full Conversation Timeline with Transcripts")
    lines.append("=" * 60)

    for msg in messages:
        prefix = f"[{msg['date']} {msg['time']}] {msg['sender']} ({msg['detected_lang']})"

        if msg['is_voice']:
            transcript = msg['transcript'] or '[Not transcribed]'
            lines.append(f"\n🎙️  {prefix}:")
            lines.append(f"    📝 Transcript: {transcript}")
        else:
            body = msg['body'].strip()
            if body and body not in ['', '\u200e']:
                lines.append(f"\n💬 {prefix}:")
                lines.append(f"    {body}")

    return '\n'.join(lines)


def analyze_conversation(messages: list[dict]) -> str:
    """Generate conversation analysis with generic signal categories for EN, HE, AR."""
    senders = {}
    voice_count = 0
    total = len(messages)

    for msg in messages:
        s = msg['sender']
        senders[s] = senders.get(s, 0) + 1
        if msg['is_voice']:
            voice_count += 1

    # ── Multilingual signal categories ──────────────────────────
    SIGNALS = {
        'negative_sentiment': {
            'en': ['frustrated', 'annoying', 'terrible', 'awful', 'angry', 'hate', 'mess'],
            'he': ['מתסכל', 'תסכול', 'מעצבן', 'עצבני', 'כועס', 'כעס', 'נמאס', 'בלאגן', 'על הפנים', 'חרא', 'זבל', 'גרוע', 'איום', 'נורא'],
            'ar': ['محبط', 'مزعج', 'رهيب', 'فظيع', 'غاضب', 'أكره', 'فوضى', 'سيء', 'قرف', 'زفت']
        },
        'unsatisfied': {
            'en': ['not happy', 'disappointed', 'disappointing', 'not what i asked'],
            'he': ['לא מרוצה', 'לא אוהב', 'לא טוב', 'לא עובד', 'אכזבה', 'מאכזב'],
            'ar': ['غير راض', 'خيبة أمل', 'مخيب للآمال', 'ليس ما طلبته', 'ما عجبني']
        },
        'time_sensitive': {
            'en': ['urgent', 'asap', 'hurry', 'no time', 'late', 'deadline'],
            'he': ['דחוף', 'מהר', 'עכשיו', 'מיד', 'אין זמן', 'מאחר', 'דדליין'],
            'ar': ['عاجل', 'بسرعة', 'الآن', 'فورا', 'لا يوجد وقت', 'متأخر', 'موعد نهائي']
        },
        'clarification_needed': {
            'en': ['dont understand', 'not clear', 'confused', 'explain', 'what do you mean'],
            'he': ['לא הבנתי', 'לא ברור', 'מבולבל', 'הסבר', 'תסביר', 'מה הכוונה'],
            'ar': ['لم أفهم', 'غير واضح', 'مشوش', 'اشرح', 'ماذا تقصد', 'مش فاهم']
        },
        'system_issues': {
            'en': ['broken', 'not working', 'crashed', 'error', 'bug', 'failed'],
            'he': ['לא עובד', 'שבור', 'תקוע', 'קפא', 'קרס', 'שגיאה', 'בעיה', 'תקלה'],
            'ar': ['معطل', 'لا يعمل', 'تحطم', 'خطأ', 'خلل', 'فشل', 'مشكلة']
        },
        'uncertainty': {
            'en': ['not sure', 'maybe', 'cancel', 'doubt', 'regret'],
            'he': ['לא בטוח', 'אולי', 'חושב לבטל', 'ספק', 'חרטה'],
            'ar': ['غير متأكد', 'ربما', 'إلغاء', 'شك', 'ندم', 'مش عارف']
        },
        'positive_feedback': {
            'en': ['great', 'amazing', 'good', 'perfect', 'thanks', 'thank you', 'awesome'],
            'he': ['מעולה', 'מדהים', 'כל הכבוד', 'יפה', 'טוב', 'אחלה', 'סבבה', 'תודה'],
            'ar': ['عظيم', 'مذهل', 'جيد', 'ممتاز', 'شكرا', 'رائع', 'تمام', 'ممتاز']
        },
    }

    friction_moments = []
    for msg in messages:
        text = (msg['body'] + ' ' + (msg['transcript'] or '')).lower()
        found_categories = {}
        for category, lang_dict in SIGNALS.items():
            # Combine all words for detection regardless of detected language
            all_words = lang_dict['en'] + lang_dict['he'] + lang_dict['ar']
            hits = [w for w in all_words if w in text]
            if hits:
                found_categories[category] = hits
        if found_categories:
            friction_moments.append({
                'time': f"{msg['date']} {msg['time']}",
                'sender': msg['sender'],
                'lang': msg['detected_lang'],
                'preview': (msg['transcript'] or msg['body'])[:120],
                'categories': found_categories,
            })

    lines = []
    lines.append("\n" + "=" * 60)
    lines.append("  Multilingual Conversation Analysis")
    lines.append("=" * 60)

    lines.append(f"\n📊 Statistics:")
    lines.append(f"   Total Messages: {total}")
    lines.append(f"   Voice Messages: {voice_count}")
    for sender, count in sorted(senders.items(), key=lambda x: -x[1]):
        lines.append(f"   {sender}: {count} messages")

    lines.append(f"\n⚠️  Detected Signals ({len(friction_moments)}):")
    if friction_moments:
        negative_cats = {'negative_sentiment', 'unsatisfied', 'time_sensitive', 'clarification_needed', 'system_issues', 'uncertainty'}
        def score(fm):
            return sum(1 for c in fm['categories'] if c in negative_cats)
        
        friction_moments.sort(key=score, reverse=True)
        for fm in friction_moments[:15]:
            cats = [c for c in fm['categories'] if c in negative_cats]
            if not cats and 'positive_feedback' not in fm['categories']:
                continue
            
            lines.append(f"\n   [{fm['time']}] {fm['sender']} ({fm['lang']}):")
            lines.append(f"   \"{fm['preview']}...\"")
            for cat, hits in fm['categories'].items():
                icon = "✅" if cat == 'positive_feedback' else "🏷"
                lines.append(f"   {icon} {cat}: {', '.join(hits[:5])}")
    else:
        lines.append("   No significant signals detected.")

    # Per-sender breakdown
    sender_stats = {}
    for msg in messages:
        s = msg['sender']
        if s not in sender_stats:
            sender_stats[s] = {
                'total': 0, 'voice': 0,
                'signals': {c: 0 for c in SIGNALS},
            }
        sender_stats[s]['total'] += 1
        if msg['is_voice']:
            sender_stats[s]['voice'] += 1

    for fm in friction_moments:
        s = fm['sender']
        if s in sender_stats:
            for cat in fm['categories']:
                sender_stats[s]['signals'][cat] += 1

    lines.append(f"\n👤 Per-Sender Breakdown:")
    for sender, stats in sorted(sender_stats.items(), key=lambda x: -x[1]['total']):
        lines.append(f"\n   {sender}:")
        lines.append(f"   Messages: {stats['total']} ({stats['voice']} voice)")
        active_signals = {c: v for c, v in stats['signals'].items() if v > 0}
        if active_signals:
            for cat, count in sorted(active_signals.items(), key=lambda x: -x[1]):
                icon = "✅" if cat == 'positive_feedback' else "⚠️"
                lines.append(f"   {icon} {cat}: {count} messages")
        else:
            lines.append(f"   — No specific signals detected")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='WhatsApp Chat Analyzer + Voice Transcriber (Multilingual)')
    parser.add_argument('--chat',  required=True, help='Path to WhatsApp export .txt file')
    parser.add_argument('--media', default='',    help='Path to media folder (voice messages)')
    parser.add_argument('--model', default='medium', choices=['tiny','base','small','medium','large'],
                        help='Whisper model size (default: medium)')
    parser.add_argument('--out',   default='analysis', help='Output filename prefix (no extension)')
    parser.add_argument('--no-transcribe', action='store_true', help='Skip transcription')
    args = parser.parse_args()

    if not os.path.exists(args.chat):
        print(f"❌ Error: Chat file not found at {args.chat}")
        return

    print(f"\n📂 Reading chat: {args.chat}")
    messages = parse_chat(args.chat)
    if not messages:
        print("❌ No messages found in the chat file.")
        return
    print(f"✅ {len(messages)} messages loaded.")

    if not args.no_transcribe and args.media:
        if os.path.exists(args.media):
            messages = transcribe_voices(messages, args.media, args.model)
        else:
            print(f"⚠️  Media folder not found at {args.media}. Skipping transcription.")
    elif not args.no_transcribe and not args.media:
        print("⚠️  No media folder specified. Skipping transcription.")

    # Build outputs
    timeline = build_timeline(messages)
    analysis = analyze_conversation(messages)
    full_output = timeline + '\n' + analysis

    # Save text
    out_txt = args.out + '.txt'
    try:
        with open(out_txt, 'w', encoding='utf-8') as f:
            f.write(full_output)
        print(f"\n✅ Saved report: {out_txt}")
    except Exception as e:
        print(f"❌ Error saving text report: {e}")

    # Save JSON
    out_json = args.out + '.json'
    try:
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        print(f"✅ Saved raw data: {out_json}")
    except Exception as e:
        print(f"❌ Error saving JSON data: {e}")

    # Final summary
    print("\n" + "="*40)
    print(" Multilingual Analysis Complete")
    print("="*40)


if __name__ == '__main__':
    main()
