import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "TVOJ_TOKEN_OVDJE")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "TVOJ_CHAT_ID_OVDJE")
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY",  "")

CHECK_INTERVAL_MINUTES = 30

DB_PATH = os.getenv("DB_PATH", "data/jobs.db")

TARGET_LOCATIONS = [
    "remote", "beograd", "novi sad", "podgorica",
    "slovenija", "ljubljana", "klagenfurt", "graz", "wien", "beč", "austria",
]

JOB_PROFILES = {
    "junior_dev": {
        "label": "Junior developer",
        "emoji": "💻",
        "keywords": [
            "junior developer", "junior programmer", "junior programer",
            "software engineer entry", "frontend junior", "backend junior",
            "python junior", "javascript junior", "web developer junior",
            "junior php", "junior java", "trainee developer", "pripravnik programer",
            "entry level developer", "junior web", "junior software",
        ],
        "ai_description": (
            "Tražim junior programersku poziciju (do 2 godine iskustva). "
            "Prihvatam: web development, backend, frontend, full-stack, "
            "Python, JavaScript, PHP, Java. "
            "NE prihvatam: senior pozicije, QA/testing, data science, "
            "devops bez coding-a, internship bez plate."
        ),
    },
    "network_medior": {
        "label": "Network / Sysadmin medior",
        "emoji": "🌐",
        "keywords": [
            "network engineer", "network administrator", "mrežni administrator",
            "system administrator", "sysadmin", "it administrator",
            "noc engineer", "network technician", "cisco", "ccna",
            "infrastructure engineer", "it support medior", "network specialist",
            "systems engineer", "linux administrator", "it operations",
        ],
        "ai_description": (
            "Tražim networking ili sysadmin poziciju, medior nivo (2-5 god. iskustva). "
            "Prihvatam: network engineer, sysadmin, IT admin, NOC, infrastruktura, Cisco. "
            "NE prihvatam: help desk level 1, junior IT support bez network komponente."
        ),
    },
}

# RSS feedovi su uklonjeni jer HelloWorld /feed/ vraća blog, ne oglase
RSS_FEEDS = []

SCRAPE_TARGETS = [
    {
        "name": "HelloWorld.rs",
        "url":  "https://helloworld.rs/oglasi",
        "type": "helloworld",
        "profiles": ["junior_dev", "network_medior"],
    },
    {
        "name": "Infostud — developer",
        "url":  "https://poslovi.infostud.com/oglasi-za-posao/developer",
        "type": "infostud",
        "profiles": ["junior_dev"],
    },
    {
        "name": "Infostud — network",
        "url":  "https://poslovi.infostud.com/oglasi-za-posao/network-administrator",
        "type": "infostud",
        "profiles": ["network_medior"],
    },
    {
        "name": "MojPosao — developer",
        "url":  "https://www.mojposao.net/pretraga-poslova?q=developer",
        "type": "mojposao",
        "profiles": ["junior_dev"],
    },
    {
        "name": "MojPosao — sysadmin",
        "url":  "https://www.mojposao.net/pretraga-poslova?q=sysadmin",
        "type": "mojposao",
        "profiles": ["network_medior"],
    },
    {
        "name": "karriere.at — IT Graz/Wien",
        "url":  "https://www.karriere.at/jobs?keywords=IT+administrator&locations=Wien%2CGraz%2CKlagenfurt",
        "type": "karriere_at",
        "profiles": ["junior_dev", "network_medior"],
    },
]
