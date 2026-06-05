"""
scraper.py — Fetch i parse job listinga sa svih portala.
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
}


def _polite_sleep():
    time.sleep(random.uniform(1.5, 3.0))


def _location_ok(text: str) -> bool:
    text_lower = text.lower()
    return any(loc in text_lower for loc in TARGET_LOCATIONS)


def _keyword_match(text: str, profile_key: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in JOB_PROFILES[profile_key]["keywords"])


def _get(url: str) -> requests.Response | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        return resp
    except requests.RequestException as e:
        logger.warning(f"Fetch greška [{url}]: {e}")
        return None


# ── HelloWorld ────────────────────────────────────────────────────────────────
# URL: /oglasi-za-posao  (potvrđeno 200)
# Selektori: a.__ga4_job_title (naslov+link), a.__ga4_job_company (kompanija)

def fetch_helloworld(target: dict) -> list[JobListing]:
    logger.info(f"Scraping: {target['name']}")
    resp = _get(target["url"])
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    title_links = soup.select("a.__ga4_job_title")
    logger.info(f"  Oglasi nađeni: {len(title_links)}")

    for title_el in title_links:
        title = title_el.get_text(strip=True)
        href  = title_el.get("href", "")
        url   = href if href.startswith("http") else "https://www.helloworld.rs" + href

        # Kompanija je sibling link u istom parent div-u
        parent  = title_el.find_parent("div")
        company_el = parent.select_one("a.__ga4_job_company") if parent else None
        company    = company_el.get_text(strip=True) if company_el else "N/A"

        # Lokacija nije eksplicitno u listi, koristimo prazan string
        # (HelloWorld pretežno SRB/remote, jezički check radi na opisu)
        location = ""

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


# ── Zaposli.me ────────────────────────────────────────────────────────────────
# URL: /oglasi-za-posao?keyword=...  (potvrđeno 200, vraća 10 oglasa po stranici)
# Selektori: a[href*='/posao/'] (link+naslov u h3), h6 (kompanija), li[1] (lokacija)

def fetch_zaposli(target: dict) -> list[JobListing]:
    logger.info(f"Scraping: {target['name']}")
    resp = _get(target["url"])
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    posao_links = soup.find_all("a", href=lambda h: h and "/posao/" in h)
    logger.info(f"  Oglasi nađeni: {len(posao_links)}")

    seen_urls = set()
    for link in posao_links:
        href = link.get("href", "")
        url  = "https://zaposli.me" + href if not href.startswith("http") else href

        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Kartica: parent div sa d-sm-flex klasom
        card = link.find_parent("div", class_=lambda c: c and "d-sm-flex" in " ".join(c if c else []))
        parent = card.find_parent("div") if card else link.find_parent("div")

        h3  = parent.select_one("h3") if parent else None
        h6  = parent.select_one("h6") if parent else None
        lis = parent.select("li")     if parent else []

        title   = h3.get_text(strip=True) if h3 else link.get_text(strip=True)
        company = h6.get_text(strip=True) if h6 else "N/A"
        # li[0] = datum, li[1] = lokacija, li[2] = ističe
        location = lis[1].get_text(strip=True) if len(lis) > 1 else ""

        if not title:
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


# ── LinkedIn RSS ──────────────────────────────────────────────────────────────
# LinkedIn blokira scraping — koristimo RSS feed koji je javno dostupan
# bez autentifikacije za generičke pretrage.

def fetch_linkedin(target: dict) -> list[JobListing]:
    logger.info(f"RSS: {target['name']}")
    try:
        feed = feedparser.parse(target["url"])
    except Exception as e:
        logger.warning(f"LinkedIn RSS greška: {e}")
        return []

    results = []
    logger.info(f"  RSS entries: {len(feed.entries)}")

    for entry in feed.entries:
        title   = entry.get("title", "").strip()
        url     = entry.get("link", "")
        summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()
        company = entry.get("author", "N/A")
        # LinkedIn RSS location je često u title kao "Naslov - Kompanija - Lokacija"
        parts    = title.split(" - ")
        location = parts[-1].strip() if len(parts) >= 3 else ""

        combined = f"{title} {location} {summary}"
        if not _location_ok(combined) and "remote" not in combined.lower():
            continue

        for profile_key in target["profiles"]:
            if _keyword_match(combined, profile_key):
                results.append(JobListing(
                    title=parts[0].strip() if parts else title,
                    company=parts[1].strip() if len(parts) >= 2 else company,
                    location=location,
                    url=url,
                    description=summary[:400],
                    source=target["name"],
                    profile=profile_key,
                ))
                break

    logger.info(f"  → {len(results)} oglasa pronađeno")
    return results


# ── Infostud ──────────────────────────────────────────────────────────────────

def fetch_infostud(target: dict) -> list[JobListing]:
    logger.info(f"Scraping: {target['name']}")
    resp = _get(target["url"])
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # Infostud koristi div.search-job-card (potvrđeno inspkcijom)
    cards = soup.select("div.search-job-card")
    logger.info(f"  Kartice nađene: {len(cards)}")

    for card in cards:
        title_el = card.select_one("h2")
        link_el  = card.select_one("a[href*='/posao/']")

        if not title_el or not link_el:
            continue

        title = title_el.get_text(strip=True)
        url   = link_el["href"]
        if not url.startswith("http"):
            url = "https://poslovi.infostud.com" + url

        # P tagovi: [0]=kompanija, [1]=lokacija, [2] ili [3]=opis
        p_tags   = [p.get_text(strip=True) for p in card.select("p") if p.get_text(strip=True)]
        company  = p_tags[0] if len(p_tags) > 0 else "N/A"
        location = p_tags[1] if len(p_tags) > 1 else ""
        desc     = p_tags[3] if len(p_tags) > 3 else p_tags[2] if len(p_tags) > 2 else ""

        # Lokacija filter — Infostud je regionalan, prihvati sve iz Srbije + remote
        combined = f"{title} {location} {desc}"
        if not _location_ok(combined) and "remote" not in combined.lower():
            # Ako lokacija nije eksplicitno navedena kao ciljna, preskočimo
            # Ali ako nema lokacije u tekstu, prihvati (može biti remote)
            if location and not _location_ok(location):
                continue

        for profile_key in target["profiles"]:
            if _keyword_match(title, profile_key):
                results.append(JobListing(
                    title=title,
                    company=company,
                    location=location,
                    url=url,
                    description=desc[:400],
                    source=target["name"],
                    profile=profile_key,
                ))
                break

    _polite_sleep()
    logger.info(f"  → {len(results)} oglasa pronađeno")
    return results


# ── MojPosao ──────────────────────────────────────────────────────────────────

def fetch_mojposao(target: dict) -> list[JobListing]:
    logger.info(f"Scraping: {target['name']}")
    resp = _get(target["url"])
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    cards = soup.select(".job-result, .search-result-item, [class*='position'], [class*='job-card']")

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


# ── karriere.at ───────────────────────────────────────────────────────────────

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


# ── Dispatcher ────────────────────────────────────────────────────────────────

SCRAPER_MAP = {
    "helloworld":  fetch_helloworld,
    "zaposli":     fetch_zaposli,
    "linkedin":    fetch_linkedin,
    "infostud":    fetch_infostud,
    "mojposao":    fetch_mojposao,
    "karriere_at": fetch_karriere_at,
}


def fetch_all() -> list[JobListing]:
    all_jobs: list[JobListing] = []

    for target in SCRAPE_TARGETS:
        scraper_fn = SCRAPER_MAP.get(target["type"])
        if scraper_fn:
            try:
                all_jobs.extend(scraper_fn(target))
            except Exception as e:
                logger.error(f"Scraper greška [{target['name']}]: {e}")

    logger.info(f"Ukupno fetchovano: {len(all_jobs)} oglasa")
    return all_jobs
