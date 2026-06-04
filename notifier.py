"""
notifier.py — Šalje Telegram poruku za svaki novi oglas.
Formatira karticu sa svim relevantnim informacijama.
"""

import logging
import requests
from storage import JobListing
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, JOB_PROFILES

logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def _format_message(job: JobListing) -> str:
    profile = JOB_PROFILES.get(job.profile, {})
    emoji   = profile.get("emoji", "📋")
    label   = profile.get("label", job.profile)

    loc_line = f"📍 {job.location}" if job.location else "📍 Lokacija nije navedena"
    sal_line = f"💰 {job.salary}" if job.salary else ""
    desc_line = f"\n_{job.description[:200]}..._" if job.description else ""

    lines = [
        f"{emoji} *{_esc(job.title)}*",
        f"🏢 {_esc(job.company)}",
        loc_line,
    ]
    if sal_line:
        lines.append(sal_line)
    lines += [
        f"🏷 {label}  |  📡 {_esc(job.source)}",
        desc_line,
        f"\n[Pogledaj oglas]({job.url})",
    ]
    return "\n".join(filter(None, lines))


def _esc(text: str) -> str:
    """Escape Markdown V2 specijalni znakovi."""
    for ch in r"_*[]()~`>#+-=|{}.!\\":
        text = text.replace(ch, f"\\{ch}")
    return text


def send_job(job: JobListing) -> bool:
    """Pošalji jednu Telegram poruku. Vrati True na uspjeh."""
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       _format_message(job),
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info(f"Telegram OK: {job.title}")
            return True
        else:
            logger.warning(f"Telegram greška {resp.status_code}: {resp.text[:200]}")
            return False
    except requests.RequestException as e:
        logger.error(f"Telegram request greška: {e}")
        return False


def send_summary(new_count: int, total_seen: int):
    """Pošalji kratki summary nakon svakog ciklusa (opcionalno)."""
    if new_count == 0:
        return   # ne uznemiravaj ako nema novosti
    text = (
        f"✅ Pronađeno *{new_count}* novih oglasa\\!\n"
        f"📊 Ukupno viđenih: {total_seen}"
    )
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       text,
        "parse_mode": "MarkdownV2",
    }, timeout=10)


def test_connection() -> bool:
    """Provjeri da li bot i chat_id rade ispravno."""
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
