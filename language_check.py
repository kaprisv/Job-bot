"""
language_check.py — Provjerava da li oglas zahtijeva njemački jezik.

Rezultati:
  "english_ok"        — engleski je dovoljan, nema zahtjeva za njemački
  "german_preferred"  — njemački je prednost ali nije obavezan
  "german_required"   — njemački je obavezan uslov
  "unknown"           — nije moguće zaključiti (nema opisa)
"""

import re
import logging
from storage import JobListing
from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

# ── Keyword signali ───────────────────────────────────────────────────────────

# Signali da je NJEMAČKI OBAVEZAN
GERMAN_REQUIRED_PATTERNS = [
    r"\bdeutsch(kenntnisse)?\b",          # Deutschkenntnisse, Deutsch
    r"\bdeutsche sprache\b",
    r"\bgerman.*(?:required|mandatory|must|zwingend|erforderlich)\b",
    r"\b(?:required|mandatory|must).*german\b",
    r"\bmuttersprachlich\b",
    r"\bc1\b", r"\bc2\b",                 # visoki nivoi = obavezno
    r"\bsprachkenntnisse.*deutsch\b",
    r"\bdeutsch.*(?:b2|c1|c2|fließend|verhandlungssicher|konversationssicher)\b",
    r"\b(?:b2|c1|c2|fließend).*deutsch\b",
    r"\bverhandlungssicher.*deutsch\b",
    r"\barbeitssprache.*deutsch\b",
    r"\bdeutsch.*arbeitssprache\b",
]

# Signali da je NJEMAČKI PREDNOST (nije obavezan)
GERMAN_PREFERRED_PATTERNS = [
    r"\bgerman.*(?:preferred|advantage|plus|beneficial|von vorteil|wünschenswert)\b",
    r"\b(?:preferred|advantage|plus|beneficial).*german\b",
    r"\bdeutsch.*(?:von vorteil|wünschenswert|optional|plus)\b",
    r"\bgerman skills? (?:are )?(?:a )?plus\b",
    r"\bbasic german\b",
    r"\ba1\b", r"\ba2\b", r"\bb1\b",      # niži nivoi = nije kritično
]

# Eksplicitni signali da je ENGLESKI DOVOLJAN
ENGLISH_OK_PATTERNS = [
    r"\benglish.*(?:required|mandatory|working language|only)\b",
    r"\b(?:working|business|fluent).*english\b",
    r"\bworking language.*english\b",
    r"\benglish.*working language\b",
    r"\bno german\b",
    r"\bgerman not required\b",
    r"\bteam.*english\b",
    r"\binternational team\b",             # međunarodni timovi obično engleski
    r"\bmulticultural\b",
]


def _check_keywords(text: str) -> str:
    """Brza provjera keyword patterna. Vrati status ili None ako nije jasan."""
    text_lower = text.lower()

    # Provjeri engleski OK prvi (eksplicitna potvrda)
    for pattern in ENGLISH_OK_PATTERNS:
        if re.search(pattern, text_lower):
            return "english_ok"

    # Provjeri obavezni njemački
    for pattern in GERMAN_REQUIRED_PATTERNS:
        if re.search(pattern, text_lower):
            # Dvostruka provjera: da li postoji i "preferred" modifikator?
            for pref in GERMAN_PREFERRED_PATTERNS:
                if re.search(pref, text_lower):
                    return "german_preferred"
            return "german_required"

    # Provjeri opcioni njemački
    for pattern in GERMAN_PREFERRED_PATTERNS:
        if re.search(pattern, text_lower):
            return "german_preferred"

    return None   # nije jasno iz keywordsa


def _check_ai(job: JobListing) -> str:
    """AI provjera za slučajeve kada keyword filter nije siguran."""
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "TVOJ_ANTHROPIC_KEY":
        return "unknown"

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        prompt = f"""Analiziraj oglas za posao i odgovori na jedno pitanje:
Da li ovaj posao zahtijeva znanje njemačkog jezika?

Oglas:
Naslov: {job.title}
Lokacija: {job.location}
Opis: {job.description[:600]}

Odgovori SAMO jednom od ova 4 odgovora (ništa drugo):
- ENGLISH_OK        (engleski je dovoljan, nema zahtjeva za njemački)
- GERMAN_PREFERRED  (njemački je prednost ali nije obavezan)
- GERMAN_REQUIRED   (njemački je obavezan uslov za posao)
- UNKNOWN           (ne može se zaključiti iz dostupnih podataka)"""

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )

        answer = response.content[0].text.strip().upper()

        mapping = {
            "ENGLISH_OK":       "english_ok",
            "GERMAN_PREFERRED": "german_preferred",
            "GERMAN_REQUIRED":  "german_required",
            "UNKNOWN":          "unknown",
        }
        result = mapping.get(answer, "unknown")
        logger.debug(f"AI jezička provjera [{job.title[:40]}]: {answer} → {result}")
        return result

    except Exception as e:
        logger.warning(f"AI jezička provjera greška: {e}")
        return "unknown"


def check_language(job: JobListing) -> str:
    """
    Kombinirani keyword + AI check.
    Vrati jedan od: english_ok | german_preferred | german_required | unknown
    """
    if not job.description and not job.location:
        return "unknown"

    combined = f"{job.title} {job.location} {job.description}"

    # 1. Pokušaj keyword filter (brzo, besplatno)
    keyword_result = _check_keywords(combined)
    if keyword_result is not None:
        logger.debug(f"Keyword jezička provjera [{job.title[:40]}]: {keyword_result}")
        return keyword_result

    # 2. Ako je lokacija Austrija/Njemačka/Švicarska i nema jasnog signala — pošalji AI
    dach_locations = ["wien", "graz", "klagenfurt", "austria", "deutschland",
                      "münchen", "berlin", "zürich", "schweiz"]
    is_dach = any(loc in combined.lower() for loc in dach_locations)

    if is_dach:
        return _check_ai(job)

    # 3. Za Balkan bez signala — vjerovatno engleski OK
    return "english_ok"


def enrich_jobs(jobs: list[JobListing]) -> list[JobListing]:
    """Dodaj language_req svim oglasima."""
    for job in jobs:
        job.language_req = check_language(job)
    return jobs
