"""
main.py — Entry point. Pokreće scheduler i orkestrira sve module.

Lokalno:     python main.py
Railway:     automatski pokreće ovaj fajl
"""

import logging
import time
import schedule
from datetime import datetime

from config import CHECK_INTERVAL_MINUTES
from scraper import fetch_all
from storage import filter_new, seen_count, init_db
from ai_filter import filter_relevant
from notifier import send_job, send_summary, test_connection

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


# ── Glavni ciklus ─────────────────────────────────────────────────────────────

def run_cycle():
    logger.info("=" * 50)
    logger.info(f"Ciklus started @ {datetime.now().strftime('%d.%m.%Y %H:%M')}")

    # 1. Fetch sa svih portala
    all_jobs = fetch_all()
    if not all_jobs:
        logger.info("Nema fetchovanih oglasa ovaj ciklus.")
        return

    # 2. Filtriraj duplikate (već viđene)
    new_jobs = filter_new(all_jobs)
    logger.info(f"Novih (ne-viđenih): {len(new_jobs)}/{len(all_jobs)}")

    if not new_jobs:
        logger.info("Nema novih oglasa.")
        return

    # 3. AI filtriranje relevantnosti
    relevant_jobs = filter_relevant(new_jobs)
    logger.info(f"Relevantnih (AI): {len(relevant_jobs)}/{len(new_jobs)}")

    # 4. Pošalji notifikacije
    sent = 0
    for job in relevant_jobs:
        if send_job(job):
            sent += 1
        time.sleep(0.5)   # kratka pauza između poruka

    # 5. Summary poruka
    send_summary(sent, seen_count())
    logger.info(f"Ciklus završen. Poslano: {sent} notifikacija.")


# ── Startup ───────────────────────────────────────────────────────────────────

def startup():
    logger.info("Job Bot startuje...")
    init_db()

    if not test_connection():
        logger.error(
            "Telegram konekcija nije uspjela! "
            "Provjeri TELEGRAM_BOT_TOKEN i TELEGRAM_CHAT_ID u config.py"
        )
    else:
        logger.info("Telegram OK.")

    # Pokreni odmah pri startu, pa onda po rasporedu
    logger.info(f"Pokretam prvi ciklus odmah, zatim svakih {CHECK_INTERVAL_MINUTES} min...")
    run_cycle()

    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(run_cycle)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    startup()
