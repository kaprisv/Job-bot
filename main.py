"""
main.py — Pokreće JEDAN ciklus i završava.
Railway Cron Job ga poziva po rasporedu, ne radi kontinuirano.
"""

import logging
import time
import sys

from config import CHECK_INTERVAL_MINUTES
from scraper import fetch_all
from storage import filter_new, seen_count, init_db
from ai_filter import filter_relevant
from language_check import enrich_jobs
from notifier import send_job, send_summary, test_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def run_cycle():
    logger.info("=" * 50)
    logger.info("Ciklus started")

    all_jobs = fetch_all()
    if not all_jobs:
        logger.info("Nema fetchovanih oglasa.")
        return 0

    new_jobs = filter_new(all_jobs)
    logger.info(f"Novih: {len(new_jobs)}/{len(all_jobs)}")
    if not new_jobs:
        logger.info("Nema novih oglasa.")
        return 0

    relevant_jobs = filter_relevant(new_jobs)
    logger.info(f"Relevantnih: {len(relevant_jobs)}/{len(new_jobs)}")
    if not relevant_jobs:
        return 0

    relevant_jobs = enrich_jobs(relevant_jobs)

    lang_stats = {}
    for job in relevant_jobs:
        lang_stats[job.language_req] = lang_stats.get(job.language_req, 0) + 1
    logger.info(f"Jezički status: {lang_stats}")

    sent = 0
    for job in relevant_jobs:
        if send_job(job):
            sent += 1
        time.sleep(0.5)

    send_summary(sent, seen_count())
    logger.info(f"Ciklus završen. Poslano: {sent} notifikacija.")
    return sent


if __name__ == "__main__":
    logger.info("Job Bot startuje (single-run mod)...")
    init_db()

    if not test_connection():
        logger.error("Telegram konekcija nije uspjela!")
        sys.exit(1)

    run_cycle()
    logger.info("Gotovo. Container se gasi.")
    # Proces završava — Railway container se odmah gasi
