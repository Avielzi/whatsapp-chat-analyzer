#!/usr/bin/env python3
"""
WhatsApp Chat Analyzer + Voice Transcriber
==========================================
מנתח ייצוא WhatsApp, מתמלל הקלטות קוליות עם Whisper,
ומייצר טיימליין מלא + ניתוח שיחה.

שימוש:
    pip install openai-whisper
    python wa_analyzer.py --chat "path/to/chat.txt" --media "path/to/media_folder"

דרישות:
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
OMITTED_PATTERN = re.compile(r'(audio omitted|voice message|הודעה קולית|קובץ קולי)', re.IGNORECASE)


def parse_chat(txt_path: str) -> list[dict]:
    """Parse WhatsApp .txt export into list of message dicts."""
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

    if current:
        messages.append(current)

    return messages


def find_voice_file(filename: str, media_dir: str) -> str | None:
    """Search for voice file in media directory (handles renamed files)."""
    media_path = Path(media_dir)
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
    # Return any audio file by index (fallback — not reliable)
    return None


def transcribe_voices(messages: list[dict], media_dir: str, model_size: str = 'medium') -> list[dict]:
    """Transcribe all voice messages using Whisper."""
    voice_msgs = [m for m in messages if m['is_voice']]
    if not voice_msgs:
        print("לא נמצאו הודעות קוליות.")
        return messages

    print(f"\n🎙️  נמצאו {len(voice_msgs)} הודעות קוליות. טוען Whisper ({model_size})...")
    try:
        import whisper
    except ImportError:
        print("❌ Whisper לא מותקן. הרץ: pip install openai-whisper")
        return messages

    model = whisper.load_model(model_size)
    print(f"✅ מודל Whisper '{model_size}' נטען.")

    for i, msg in enumerate(voice_msgs, 1):
        audio_path = None
        if msg['voice_file'] and media_dir:
            audio_path = find_voice_file(msg['voice_file'], media_dir)

        if not audio_path:
            # Try to find any unmatched audio file by position
            print(f"  [{i}/{len(voice_msgs)}] ⚠️  קובץ לא נמצא: {msg.get('voice_file','unknown')} — דילוג")
            msg['transcript'] = '[קובץ קולי — לא נמצא]'
            continue

        print(f"  [{i}/{len(voice_msgs)}] מתמלל: {os.path.basename(audio_path)}...")
        try:
            result = model.transcribe(audio_path, language='he', task='transcribe')
            transcript = result['text'].strip()
            msg['transcript'] = transcript
            print(f"          ✅ {transcript[:80]}{'...' if len(transcript)>80 else ''}")
        except Exception as e:
            msg['transcript'] = f'[שגיאת תמלול: {e}]'
            print(f"          ❌ שגיאה: {e}")

    return messages


def build_timeline(messages: list[dict]) -> str:
    """Build readable timeline with transcripts inline."""
    lines = []
    lines.append("=" * 60)
    lines.append("  טיימליין שיחה מלא עם תמלולים")
    lines.append("=" * 60)

    for msg in messages:
        prefix = f"[{msg['date']} {msg['time']}] {msg['sender']}"

        if msg['is_voice']:
            transcript = msg['transcript'] or '[לא תומלל]'
            lines.append(f"\n🎙️  {prefix}:")
            lines.append(f"    📝 תמלול: {transcript}")
        else:
            body = msg['body'].strip()
            if body and body not in ['', '\u200e']:
                lines.append(f"\n💬 {prefix}:")
                lines.append(f"    {body}")

    return '\n'.join(lines)


def analyze_conversation(messages: list[dict]) -> str:
    """Generate conversation analysis for future client reference."""
    senders = {}
    voice_count = 0
    total = len(messages)

    for msg in messages:
        s = msg['sender']
        senders[s] = senders.get(s, 0) + 1
        if msg['is_voice']:
            voice_count += 1

    # Find frustration indicators in text + transcripts
    # ── Multi-category signal bank ──────────────────────────
    SIGNALS = {
        'תסכול': [
            # עברית ישירה
            'מתסכל', 'תסכול', 'מעצבן', 'עצבני', 'כועס', 'כעס',
            'נמאס', 'נמאס לי', 'מאוס', 'בא לי לזרוק',
            'לא יכול', 'אין לי כוח', 'עייפתי', 'נלאיתי',
            'מספיק', 'די', 'זהו', 'נגמר', 'אין סבלנות',
            # סלנג ישראלי
            'בלאגן', 'על הפנים', 'אל הפנים', 'חרא', 'זבל',
            'גרוע', 'גרועה', 'איום', 'נורא', 'סוס מת',
            'חבל על הזמן', 'חבל', 'ביטול',
            # ביטויים עמומים של כעס
            'וואלה לא', 'מה זה', 'מה הסיפור', 'מה קורה פה',
            'לא יאמן', 'לא יכול להיות', 'זה לא יכול להיות',
        ],
        'אי_שביעות_רצון': [
            'לא מרוצה', 'לא אוהב', 'לא טוב', 'לא עובד',
            'לא מתאים', 'לא מה שרציתי', 'לא מה שביקשתי',
            'ציפיתי', 'לא ציפיתי', 'אכזבה', 'מאכזב',
            'גרוע ממה', 'פחות ממה', 'לא הבנת', 'לא הבנתי',
            'פספסת', 'לא זה', 'לא ככה',
        ],
        'לחץ_זמן': [
            'דחוף', 'מהר', 'עכשיו', 'מיד', 'אין זמן',
            'לוקח זמן', 'מאחר', 'אחרי', 'כבר שבוע', 'כבר חודש',
            'נמשך', 'ממשיך', 'לא נגמר', 'מתי זה יגמר',
            'להספיק', 'ספיק', 'לא מספיק',
        ],
        'בלבול_ותקשורת': [
            'לא הבנתי', 'לא ברור', 'מבולבל', 'מבולבלת',
            'לא הסברת', 'הסבר', 'תסביר', 'מה הכוונה',
            'איפה', 'מה זה', 'לא רואה', 'לא מוצא',
            'אי אפשר', 'לא ניתן', 'לא נגיש',
        ],
        'בעיות_טכניות': [
            'לא עובד', 'שבור', 'תקוע', 'קפא', 'קרס',
            'שגיאה', 'בעיה', 'תקלה', 'לא נטען', 'לא נפתח',
            'לא רואים', 'לא מוצג', 'נעלם', 'נמחק',
            'וורדפרס', 'אלמנטור', 'לא מצליח לערוך',
        ],
        'חרטה_וספק': [
            'לא בטוח', 'אולי', 'אולי לא', 'חושב לבטל',
            'לא יודע', 'ספק', 'חרטה', 'מתחרט',
            'אם הייתי יודע', 'לא היה שווה', 'בזבוז',
            'היה עדיף', 'פשוט לא', 'בכלל לא',
        ],
        'אישור_וחיובי': [
            # חיובי — לאתר גם רגעים טובים
            'מעולה', 'מדהים', 'כל הכבוד', 'יפה', 'טוב',
            'אחלה', 'סבבה', 'בסדר גמור', 'ממש טוב',
            'אהבתי', 'מוצלח', 'מושלם', 'תודה רבה',
            'שמח', 'מרוצה', 'מסכים', 'אשר', 'מאשר',
        ],
        'english_frustration': [
            # אנגלית
            "can't", "cannot", "doesn't work", "not working",
            "frustrated", "annoying", "terrible", "awful",
            "waste of time", "useless", "broken", "confused",
            "don't understand", "what is this", "seriously",
            "come on", "really?", "ridiculous",
        ],
    }
    friction_moments = []
    for msg in messages:
        text = (msg['body'] + ' ' + (msg['transcript'] or '')).lower()
        found_categories = {}
        for category, words in SIGNALS.items():
            hits = [w for w in words if w in text]
            if hits:
                found_categories[category] = hits
        if found_categories:
            friction_moments.append({
                'time': f"{msg['date']} {msg['time']}",
                'sender': msg['sender'],
                'preview': (msg['transcript'] or msg['body'])[:120],
                'categories': found_categories,
            })

    lines = []
    lines.append("\n" + "=" * 60)
    lines.append("  ניתוח שיחה — לשימוש עם לקוחות עתידיים")
    lines.append("=" * 60)

    lines.append(f"\n📊 סטטיסטיקות:")
    lines.append(f"   סה\"כ הודעות: {total}")
    lines.append(f"   הודעות קוליות: {voice_count}")
    for sender, count in sorted(senders.items(), key=lambda x: -x[1]):
        lines.append(f"   {sender}: {count} הודעות")

    lines.append(f"\n⚠️  נקודות חיכוך ({len(friction_moments)}):")
    if friction_moments:
        # Sort: negative categories first
        negative_cats = {'תסכול','אי_שביעות_רצון','לחץ_זמן','בלבול_ותקשורת','בעיות_טכניות','חרטה_וספק','english_frustration'}
        def score(fm):
            return sum(1 for c in fm['categories'] if c in negative_cats)
        friction_moments.sort(key=score, reverse=True)
        for fm in friction_moments[:12]:
            cats = [c for c in fm['categories'] if c in negative_cats]
            if not cats:
                continue
            lines.append(f"\n   [{fm['time']}] {fm['sender']}:")
            lines.append(f"   \"{fm['preview']}\"")
            for cat in cats:
                lines.append(f"   🏷  {cat}: {', '.join(fm['categories'][cat][:4])}")
    else:
        lines.append("   לא זוהו נקודות חיכוך.")

    # Positive moments
    positive = [fm for fm in friction_moments if 'אישור_וחיובי' in fm['categories']]
    lines.append(f"\n✅ רגעי אישור / חיובי ({len(positive)}):")
    for pm in positive[:5]:
        lines.append(f"   [{pm['time']}] {pm['sender']}: \"{pm['preview'][:80]}\"")


    # Per-sender breakdown
    sender_stats = {}
    for msg in messages:
        s = msg['sender']
        if s not in sender_stats:
            sender_stats[s] = {
                'total': 0, 'voice': 0,
                'friction': {c: 0 for c in SIGNALS},
            }
        sender_stats[s]['total'] += 1
        if msg['is_voice']:
            sender_stats[s]['voice'] += 1

    for fm in friction_moments:
        s = fm['sender']
        if s in sender_stats:
            for cat in fm['categories']:
                if cat in sender_stats[s]['friction']:
                    sender_stats[s]['friction'][cat] += 1

    lines.append(f"\n👤 ניתוח לפי שולח:")
    for sender, stats in sorted(sender_stats.items(), key=lambda x: -x[1]['total']):
        lines.append(f"\n   {sender}:")
        lines.append(f"   הודעות: {stats['total']} (מתוכן {stats['voice']} קוליות)")
        active_friction = {c: v for c, v in stats['friction'].items()
                          if v > 0 and c != 'אישור_וחיובי'}
        positive_count = stats['friction'].get('אישור_וחיובי', 0)
        if active_friction:
            for cat, count in sorted(active_friction.items(), key=lambda x: -x[1]):
                lines.append(f"   ⚠️  {cat}: {count} הודעות")
        if positive_count:
            lines.append(f"   ✅ חיובי/אישור: {positive_count} הודעות")
        if not active_friction and not positive_count:
            lines.append(f"   — ללא סיגנלים מיוחדים")


    lines.append("   (מבוסס על ניתוח השיחה — יש להשלים ידנית)")
    lines.append("   1. ___")
    lines.append("   2. ___")
    lines.append("   3. ___")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='WhatsApp Chat Analyzer + Voice Transcriber')
    parser.add_argument('--chat',  required=True, help='נתיב לקובץ .txt של WhatsApp export')
    parser.add_argument('--media', default='',    help='נתיב לתיקיית המדיה (הקלטות)')
    parser.add_argument('--model', default='medium', choices=['tiny','base','small','medium','large'],
                        help='גודל מודל Whisper (ברירת מחדל: medium)')
    parser.add_argument('--out',   default='analysis', help='שם קובץ פלט (ללא סיומת)')
    parser.add_argument('--no-transcribe', action='store_true', help='דלג על תמלול')
    args = parser.parse_args()

    print(f"\n📂 קורא שיחה: {args.chat}")
    messages = parse_chat(args.chat)
    print(f"✅ {len(messages)} הודעות נטענו.")

    if not args.no_transcribe and args.media:
        messages = transcribe_voices(messages, args.media, args.model)
    elif not args.no_transcribe and not args.media:
        print("⚠️  לא צוינה תיקיית מדיה — תמלול ידני נדרש לפי הטיימליין.")

    # Build outputs
    timeline = build_timeline(messages)
    analysis = analyze_conversation(messages)
    full_output = timeline + '\n' + analysis

    # Save text
    out_txt = args.out + '.txt'
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write(full_output)
    print(f"\n✅ נשמר: {out_txt}")

    # Save JSON (raw data for further processing)
    out_json = args.out + '.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    print(f"✅ נשמר: {out_json}")

    # Print summary to screen
    print(full_output)


if __name__ == '__main__':
    main()
