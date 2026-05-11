"""Wikipedia article collector — race summaries, driver bios, constructor pages, circuit pages.

Walks previously-collected Ergast files for Wikipedia URLs, dedupes across seasons,
and fetches each article via the MediaWiki API (using the wikipedia-api wrapper).
Saves cleaned plaintext to data/raw/wikipedia/{category}/{slug}.txt and appends one
row per article to data/manifest.jsonl.

Resumable: existing files are skipped on re-run.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import wikipediaapi
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm import tqdm

from ingestion._log import configure_collector_logger

USER_AGENT = "F1RAGObservability/0.1 (https://github.com/saisrinivasmuriki/f1-rag-observability)"
LANGUAGE = "en"

ERGAST_DATA_DIR = Path("data/raw/ergast")
DATA_DIR = Path("data/raw/wikipedia")
MANIFEST_PATH = Path("data/manifest.jsonl")

THROTTLE_SECONDS = 1.0

log = logging.getLogger("ingestion.collect.wikipedia")


@dataclass(frozen=True)
class Article:
    """One Wikipedia article we plan to fetch."""

    url: str
    category: str  # "races" | "drivers" | "constructors" | "circuits"
    slug: str
    title_hint: str  # human-readable, for logs only


def _normalize_url(url: str) -> str:
    """Force https and strip trailing slash so http/https variants dedupe."""
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    return url.rstrip("/")


def _slugify(text: str) -> str:
    text = text.lower().replace(" ", "_")
    text = re.sub(r"[^a-z0-9_]+", "", text)
    return text or "untitled"


def _slug_from_url(url: str) -> str:
    path = urlparse(url).path
    title = unquote(path.rsplit("/", 1)[-1])
    return _slugify(title)


def _title_from_url(url: str) -> str:
    """Extract the article title (underscored, URL-decoded) from a Wikipedia URL."""
    path = urlparse(url).path
    return unquote(path.rsplit("/", 1)[-1])


def _gather_articles() -> list[Article]:
    """Walk all Ergast files; extract Wikipedia URLs; dedupe across seasons."""
    seen: dict[str, Article] = {}

    for races_file in sorted(ERGAST_DATA_DIR.glob("*/races.json")):
        data = json.loads(races_file.read_text(encoding="utf-8"))
        for race in data["MRData"]["RaceTable"]["Races"]:
            if "url" in race:
                race_url = _normalize_url(race["url"])
                if race_url not in seen:
                    seen[race_url] = Article(
                        url=race_url,
                        category="races",
                        slug=_slug_from_url(race_url),
                        title_hint=race["raceName"],
                    )
            else:
                log.debug("Skip race (no url): %s", race.get("raceName"))

            circuit = race.get("Circuit", {})
            if "url" in circuit:
                circuit_url = _normalize_url(circuit["url"])
                if circuit_url not in seen:
                    seen[circuit_url] = Article(
                        url=circuit_url,
                        category="circuits",
                        slug=circuit["circuitId"],
                        title_hint=circuit["circuitName"],
                    )
            else:
                log.debug("Skip circuit (no url): %s", circuit.get("circuitId"))

    for drivers_file in sorted(ERGAST_DATA_DIR.glob("*/drivers.json")):
        data = json.loads(drivers_file.read_text(encoding="utf-8"))
        for driver in data["MRData"]["DriverTable"]["Drivers"]:
            if "url" not in driver:
                log.debug("Skip driver (no url): %s", driver.get("driverId"))
                continue
            driver_url = _normalize_url(driver["url"])
            if driver_url not in seen:
                seen[driver_url] = Article(
                    url=driver_url,
                    category="drivers",
                    slug=driver["driverId"],
                    title_hint=f"{driver['givenName']} {driver['familyName']}",
                )

    for constructors_file in sorted(ERGAST_DATA_DIR.glob("*/constructors.json")):
        data = json.loads(constructors_file.read_text(encoding="utf-8"))
        for constructor in data["MRData"]["ConstructorTable"]["Constructors"]:
            if "url" not in constructor:
                log.debug("Skip constructor (no url): %s", constructor.get("constructorId"))
                continue
            constructor_url = _normalize_url(constructor["url"])
            if constructor_url not in seen:
                seen[constructor_url] = Article(
                    url=constructor_url,
                    category="constructors",
                    slug=constructor["constructorId"],
                    title_hint=constructor["name"],
                )

    return list(seen.values())


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def _fetch_page(wiki: wikipediaapi.Wikipedia, title: str) -> wikipediaapi.WikipediaPage | None:
    time.sleep(THROTTLE_SECONDS)
    log.debug("GET wikipedia/%s", title)
    page = wiki.page(title)
    if not page.exists():
        return None
    return page


def _append_manifest(record: dict[str, Any]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def collect() -> None:
    """Fetch all Wikipedia articles referenced from Ergast data."""
    log_path = configure_collector_logger("wikipedia")
    print(f"[wikipedia] log file: {log_path}", file=sys.stderr)
    log.info("Collector started")

    articles = _gather_articles()
    log.info("Discovered %d unique articles to fetch", len(articles))

    wiki = wikipediaapi.Wikipedia(user_agent=USER_AGENT, language=LANGUAGE)

    fetched = 0
    skipped_existing = 0
    not_found = 0

    for article in tqdm(articles, desc="Wikipedia articles", unit="page"):
        file_path = DATA_DIR / article.category / f"{article.slug}.txt"
        if file_path.exists():
            skipped_existing += 1
            log.debug("Skip (exists): %s", file_path)
            continue

        title = _title_from_url(article.url)
        page = _fetch_page(wiki, title)
        if page is None:
            not_found += 1
            log.warning("Not found: %s (url=%s)", title, article.url)
            continue

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(page.text, encoding="utf-8")
        char_count = len(page.text)

        _append_manifest({
            "id": f"wikipedia/{article.category}/{article.slug}",
            "source": "wikipedia",
            "category": article.category,
            "title": page.title,
            "url": article.url,
            "file_path": str(file_path),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "char_count": char_count,
        })
        fetched += 1
        log.info("Saved %s (%d chars)", file_path, char_count)

    log.info(
        "Collector finished: fetched=%d, skipped=%d, not_found=%d",
        fetched,
        skipped_existing,
        not_found,
    )


if __name__ == "__main__":
    collect()
