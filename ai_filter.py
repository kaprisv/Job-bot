"""
ai_filter.py — Claude API filtrira oglase prema tvojim kriterijumima.
Klijent se inicijalizuje lazy (unutar funkcije) da izbjegnemo crash pri importu.
"""

import logging
from storage import JobListing
from config import JOB_PROFILES, ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)


def _get_client():
    """Lazy inicijalizacija — ne crasha app ako nema API ključa."""
    import anthropic
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _build_prompt(job: JobListing, profile_key: str) -> str:
    profile = JOB_PROFILES[profile_key]
    return f"""Ti si asistent koji filtrira oglase za posao.

MOJ PROFIL:
{profile['ai_description']}

OGLAS:
Naslov: {job.title}
Kompanija: {job.company}
Lokacija: {job.location}
Opis: {job.description[:500] if job.description else 'N/A'}

Da li ovaj oglas odgovara mom profilu?
Odgovori SAMO sa: YES ili NO
Ne objašnjavaj zašto."""


def is_relevant(job: JobListing) -> bool:
    """
    Vrati True ako AI smatra oglas relevantnim.
    Fallback na True ako API ne radi ili nema ključa.
    """
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "TVOJ_ANTHROPIC_KEY":
        logger.debug("AI filter preskočen (nema API ključa), prihvatam oglas")
        return True

    try:
        client = _get_client()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=5,
            messages=[
                {"role": "user", "content": _build_prompt(job, job.profile)}
            ],
        )
        answer = response.content[0].text.strip().upper()
        result = answer.startswith("YES")
        logger.debug(f"AI filter [{job.title}]: {answer} → {'✓' if result else '✗'}")
        return result

    except Exception as e:
        logger.warning(f"AI filter greška: {e} — prihvatam oglas")
        return True


def filter_relevant(jobs: list[JobListing]) -> list[JobListing]:
    """Filtriraj listu, vrati samo relevantne."""
    if not jobs:
        return []
    relevant = [job for job in jobs if is_relevant(job)]
    logger.info(f"AI filter: {len(relevant)}/{len(jobs)} prošlo")
    return relevant
