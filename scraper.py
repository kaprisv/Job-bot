"""
scraper.py — Fetch i parse job listinga sa svih portala.
Svaki portal ima svoju funkciju. RSS je najbrži i najpouzdaniji.
"""

import time
import random
import logging
import feedparser
import requests
from bs4 import BeautifulSoup
from storage import JobListing
from config import RSS_FEEDS, SCRAPE_TARGETS, JOB_PROFILES, TARGET_LOCATIONS

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ── Pomoćne funkcije ─────────────────────────────────────────────────────────

def _polite_sleep():
    """Pauza između zahtjeva da ne bi blokirali IP."""
    time.sleep(random.uniform(1.5, 3.5))


def _location_ok(text: str) -> bool:
    """Vrati True ako lokacija odgovara nekom od ciljanih mjesta (ili je Remote)."""
    text_lower = text.lower()
    return any(loc in text_lower for loc in TARGET_LOCATIONS)


def _keyword_match(text: str, profile_key: str) -> bool:
    """Provjeri da li naslov/opis sadrži neku od ključnih reči profila."""
    text_lower = text.lower()
    keywords = JOB_PROFILES[profile_key]["keywords"]
    return any(kw.lower() in text_lower for kw in keywords)


def _get(url: str) -> requests.Response | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        return resp
    except requests.RequestException as e:
        logger.warning(f"Fetch greška [{url}]: {e}")
        return None


# ── RSS (HelloWorld i sl.) ───────────────────────────────────────────────────

def fetch_rss_feed(feed_cfg: dict) -> list[JobListing]:
    logger.info(f"RSS: {feed_cfg['name']}")
    feed = feedparser.parse(feed_cfg["url"])
    results = []

    for entry in feed.entries:
        title = entry.get("title", "")
        url   = entry.get("link", "")
        desc  = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()
        combined = f"{title} {desc}"

        for profile_key in feed_cfg["profiles"]:
            if _keyword_match(combined, profile_key):
                results.append(JobListing(
                    title=title.strip(),
                    company=entry.get("author", "N/A"),
                    location=entry.get("tags", [{}])[0].get("term", "") if entry.get("tags") else "",
                    url=url,
                    description=desc[:400],
                    source=feed_cfg["name"],
                    profile=profile_key,
                ))
                break  # ne dodaj isti oglas dva puta ako prolazi oba profila

    logger.info(f"  → {len(results)} oglasa pronađeno")
    return results


# ── Infostud ─────────────────────────────────────────────────────────────────

def fetch_infostud(target: dict) -> list[JobListing]:
    logger.info(f"Scraping: {target['name']}")
    resp = _get(target["url"])
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # Infostud koristi .oglas-item ili .job-item — provjeri DevTools ako se promijeni
    cards = soup.select(".oglas-item, .job-item, article.listing")

    if not cards:
        # Fallback: pokušaj generički
        cards = soup.select("[class*='oglas'], [class*='job-card'], [class*='listing']")

    for card in cards:
        title_el   = card.select_one("h2, h3, .title, .oglas-title, .job-title")
        company_el = card.select_one(".company, .firma, .employer")
        loc_el     = card.select_one(".location, .lokacija, .place")
        link_el    = card.select_one("a[href]")

        if not title_el or not link_el:
            continue

        title    = title_el.get_text(strip=True)
        company  = company_el.get_text(strip=True) if company_el else "N/A"
        location = loc_el.get_text(strip=True) if loc_el else ""
        href     = link_el["href"]
        url      = href if href.startswith("http") else "https://poslovi.infostud.com" + href

        combined = f"{title} {location}"
        if not _location_ok(combined) and "remote" not in combined.lower():
            continue

        for profile_key in target["profiles"]:
            if _keyword_match(title, profile_key):
                results.append(JobListing(
                    title=title,
                    company=company,
                    location=location,
                    url=url,
                    source=target["name"],
                    profile=profile_key,
                ))
                break

    _polite_sleep()
    logger.info(f"  → {len(results)} oglasa pronađeno")
    return results


# ── MojPosao ─────────────────────────────────────────────────────────────────

def fetch_mojposao(target: dict) -> list[JobListing]:
    logger.info(f"Scraping: {target['name']}")
    resp = _get(target["url"])
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    cards = soup.select(".job-result, .search-result-item, [class*='position']")

    for card in cards:
        title_el   = card.select_one(".title, h2, h3, .job-title")
        company_el = card.select_one(".company-name, .employer, .company")
        loc_el     = card.select_one(".location, .city, .place")
        link_el    = card.select_one("a[href]")

        if not title_el or not link_el:
            continue

        title    = title_el.get_text(strip=True)
        company  = company_el.get_text(strip=True) if company_el else "N/A"
        location = loc_el.get_text(strip=True) if loc_el else ""
        href     = link_el["href"]
        url      = href if href.startswith("http") else "https://www.mojposao.net" + href

        combined = f"{title} {location}"
        if not _location_ok(combined):
            continue

        for profile_key in target["profiles"]:
            if _keyword_match(title, profile_key):
                results.append(JobListing(
                    title=title,
                    company=company,
                    location=location,
                    url=url,
                    source=target["name"],
                    profile=profile_key,
                ))
                break

    _polite_sleep()
    logger.info(f"  → {len(results)} oglasa pronađeno")
    return results


# ── karriere.at ──────────────────────────────────────────────────────────────

def fetch_karriere_at(target: dict) -> list[JobListing]:
    logger.info(f"Scraping: {target['name']}")
    resp = _get(target["url"])
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    cards = soup.select(".m-jobsListItem, [class*='jobsListItem'], article[class*='job']")

    for card in cards:
        title_el   = card.select_one("h2, h3, .jobTitle, [class*='title']")
        company_el = card.select_one(".company, [class*='company'], [class*='employer']")
        loc_el     = card.select_one(".location, [class*='location']")
        link_el    = card.select_one("a[href]")

        if not title_el or not link_el:
            continue

        title    = title_el.get_text(strip=True)
        company  = company_el.get_text(strip=True) if company_el else "N/A"
        location = loc_el.get_text(strip=True) if loc_el else ""
        href     = link_el["href"]
        url      = href if href.startswith("http") else "https://www.karriere.at" + href

        for profile_key in target["profiles"]:
            if _keyword_match(title, profile_key):
                results.append(JobListing(
                    title=title,
                    company=company,
                    location=location,
                    url=url,
                    source=target["name"],
                    profile=profile_key,
                ))
                break

    _polite_sleep()
    logger.info(f"  → {len(results)} oglasa pronađeno")
    return results


# ── Glavni entry point ────────────────────────────────────────────────────────

SCRAPER_MAP = {
    "infostud":   fetch_infostud,
    "mojposao":   fetch_mojposao,
    "karriere_at": fetch_karriere_at,
}


def fetch_all() -> list[JobListing]:
    """Pozovi sve izvore i vrati kombinovanu listu."""
    all_jobs: list[JobListing] = []

    for feed_cfg in RSS_FEEDS:
        try:
            all_jobs.extend(fetch_rss_feed(feed_cfg))
        except Exception as e:
            logger.error(f"RSS greška [{feed_cfg['name']}]: {e}")

    for target in SCRAPE_TARGETS:
        scraper_fn = SCRAPER_MAP.get(target["type"])
        if scraper_fn:
            try:
                all_jobs.extend(scraper_fn(target))
            except Exception as e:
                logger.error(f"Scraper greška [{target['name']}]: {e}")

    logger.info(f"Ukupno fetchovano: {len(all_jobs)} oglasa")
    return all_jobs
