"""Ergast/Jolpica API collector — structured F1 data for seasons 2020-2025.

Fetches per-season metadata (races, drivers, constructors, circuits, standings, sprint)
and per-race results (results, qualifying). Saves raw JSON to disk and appends one
row per file to data/manifest.jsonl.

Resumable: files that already exist on disk are skipped on re-run.
Each call to `collect()` writes a fresh log file to logs/.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm import tqdm

from ingestion._log import configure_collector_logger

BASE_URL = "https://api.jolpi.ca/ergast/f1"
USER_AGENT = "F1RAGObservability/0.1 (https://github.com/saisrinivasmuriki/f1-rag-observability)"

DATA_DIR = Path("data/raw/ergast")
MANIFEST_PATH = Path("data/manifest.jsonl")

SEASONS = list(range(2020, 2026))

SEASON_ENDPOINTS = [
    "races",
    "drivers",
    "constructors",
    "circuits",
    "driverstandings",
    "constructorstandings",
    "sprint",
]

ROUND_ENDPOINTS = [
    "results",
    "qualifying",
]

THROTTLE_SECONDS = 0.3
REQUEST_TIMEOUT = 30.0

log = logging.getLogger("ingestion.collect.ergast")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def _fetch_json(url: str) -> dict[str, Any]:
    time.sleep(THROTTLE_SECONDS)
    log.debug("GET %s", url)
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


def _save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _append_manifest(record: dict[str, Any]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _record_count(data: dict[str, Any]) -> int:
    return int(data.get("MRData", {}).get("total", 0))


def _round_count(races_data: dict[str, Any]) -> int:
    return len(races_data["MRData"]["RaceTable"]["Races"])


def _collect_one(url: str, file_path: Path, manifest_record: dict[str, Any]) -> None:
    if file_path.exists():
        log.debug("Skip (exists): %s", file_path)
        return
    data = _fetch_json(url)
    _save_json(file_path, data)
    count = _record_count(data)
    manifest_record["fetched_at"] = datetime.now(timezone.utc).isoformat()
    manifest_record["record_count"] = count
    _append_manifest(manifest_record)
    log.info("Saved %s (%d records)", file_path, count)


def _collect_season(season: int) -> dict[str, Any]:
    """Fetch all per-season endpoints; return races payload to drive the round loop."""
    season_dir = DATA_DIR / str(season)

    for endpoint in SEASON_ENDPOINTS:
        url = f"{BASE_URL}/{season}/{endpoint}.json?limit=100"
        file_path = season_dir / f"{endpoint}.json"
        record = {
            "id": f"ergast/{season}/{endpoint}",
            "source": "ergast",
            "season": season,
            "endpoint": endpoint,
            "url": url,
            "file_path": str(file_path),
        }
        _collect_one(url, file_path, record)

    races_path = season_dir / "races.json"
    return json.loads(races_path.read_text(encoding="utf-8"))


def _collect_round(season: int, round_num: int) -> None:
    round_dir = DATA_DIR / str(season) / f"{round_num:02d}"
    for endpoint in ROUND_ENDPOINTS:
        url = f"{BASE_URL}/{season}/{round_num}/{endpoint}.json"
        file_path = round_dir / f"{endpoint}.json"
        record = {
            "id": f"ergast/{season}/{round_num:02d}/{endpoint}",
            "source": "ergast",
            "season": season,
            "round": round_num,
            "endpoint": endpoint,
            "url": url,
            "file_path": str(file_path),
        }
        _collect_one(url, file_path, record)


def collect(seasons: list[int] | None = None) -> None:
    """Fetch all Ergast/Jolpica data for the given seasons (default: 2020-2025)."""
    log_path = configure_collector_logger("ergast")
    target_seasons = seasons or SEASONS
    print(f"[ergast] log file: {log_path}", file=sys.stderr)
    log.info("Collector started; seasons=%s", target_seasons)

    for season in tqdm(target_seasons, desc="Seasons", unit="season"):
        log.info("Season %d: fetching season-level endpoints", season)
        races_payload = _collect_season(season)
        round_count = _round_count(races_payload)
        log.info("Season %d: %d rounds detected", season, round_count)

        for round_num in tqdm(
            range(1, round_count + 1),
            desc=f"  {season} rounds",
            leave=False,
            unit="race",
        ):
            _collect_round(season, round_num)

        log.info("Season %d: complete", season)

    log.info("Collector finished")


if __name__ == "__main__":
    collect()
