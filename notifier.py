"""
notifier.py — Šalje Telegram poruku za svaki novi oglas.
Plain text format, sa jezičkim indikatorom.
"""

import logging
import requests
from storage import JobListing
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, JOB_PROFILES

logger = logging.getLogger(__name__)
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

LANGUAGE_LABELS = {
    "english_ok":       "✅ Engleski dovoljan",
    "german_preferred": "🟡 Njemački prednost (nije obavezan)",
    "german_required":  "🔴 Njemački OBAVEZAN",
    "unknown":          "❓ Jezički zahtjev nepoznat",
}


def _format_message(job: JobListing) -> str:
    profile   = JOB_PROFILES.get(job.profile, {})
    emoji     = profile.get("emoji", "📋")
    label     = profile.get("label", job.profile)
    lang_line = LANGUAGE_LABELS.get(job.language_req, "❓ Nepoznato")

    lines = [
        f"{emoji} {job.title}",
        f"🏢 {job.company}",
    ]
    if job.location:
        lines.append(f"📍 {job.location}")
    if job.salary:
        lines.append(f"💰 {job.salary}")

    lines.append(f"🗣 {lang_line}")
    lines.append(f"🏷 {label}  |  📡 {job.source}")

    if job.description:
        lines.append(f"\n{job.description[:200].strip()}...")

    lines.append(f"\n🔗 {job.url}")
    return "\n".join(lines)


def send_job(job: JobListing) -> bool:
    payload = {
        "chat_id":                  TELEGRAM_CHAT_ID,
        "text":                     _format_message(job),
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info(f"Telegram OK: {job.title}")
            return True
        logger.warning(f"Telegram greška {resp.status_code}: {resp.text[:200]}")
        return False
    except requests.RequestException as e:
        logger.error(f"Telegram request greška: {e}")
        return False


def send_summary(new_count: int, total_seen: int):
    if new_count == 0:
        return
    text = f"✅ Poslano {new_count} novih oglasa! Ukupno viđenih: {total_seen}"
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text":    text,
    }, timeout=10)


def test_connection() -> bool:
    try:
        resp = requests.get(f"{TELEGRAM_API}/getMe", timeout=5)
        if resp.status_code == 200:
            bot_name = resp.json()["result"]["username"]
            logger.info(f"Telegram bot aktivan: @{bot_name}")
            return True
        logger.error(f"Telegram getMe greška: {resp.text}")
        return False
    except Exception as e:
        logger.error(f"Telegram konekcija neuspješna: {e}")
        return False
