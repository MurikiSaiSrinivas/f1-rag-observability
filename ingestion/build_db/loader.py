"""Build the Ergast SQLite database from Phase 1 JSON files.

Walks data/raw/ergast/ and populates a normalized 9-table schema at
data/db/ergast.sqlite using the SQL in ingestion/build_db/schema.sql.

Idempotent: drops and recreates the database on each run. Total time ~3-5s
for the 6 seasons / 131 races / ~6,500 result rows.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Any

from ingestion._log import configure_build_db_logger

ERGAST_DIR = Path("data/raw/ergast")
DB_DIR = Path("data/db")
DB_PATH = DB_DIR / "ergast.sqlite"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

log = logging.getLogger("ingestion.build_db.ergast")


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _int(v: Any) -> int | None:
    """Parse to int; None for missing/empty values; None for non-numeric strings."""
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _real(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _season_dirs() -> list[Path]:
    return sorted(
        d for d in ERGAST_DIR.iterdir() if d.is_dir() and d.name.isdigit()
    )


def _round_dirs(season_dir: Path) -> list[Path]:
    return sorted(
        d for d in season_dir.iterdir() if d.is_dir() and d.name.isdigit()
    )


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------
# Per-table loaders. Order matters in build() — entities first, then races
# (which FK to circuits), then per-race results (FK to races + drivers +
# constructors), then standings.
# ----------------------------------------------------------------------------


def load_drivers(conn: sqlite3.Connection) -> int:
    """Dedupe drivers across all season drivers.json files. Latest season wins
    on conflict (Ergast occasionally tweaks driver code/number)."""
    seen: dict[str, dict] = {}
    for season_dir in _season_dirs():
        f = season_dir / "drivers.json"
        if not f.exists():
            continue
        for d in _load_json(f)["MRData"]["DriverTable"]["Drivers"]:
            seen[d["driverId"]] = d

    rows = [
        (
            d["driverId"],
            d.get("code"),
            _int(d.get("permanentNumber")),
            d["givenName"],
            d["familyName"],
            d.get("nationality"),
            d.get("dateOfBirth"),
            d.get("url"),
        )
        for d in seen.values()
    ]
    conn.executemany(
        "INSERT INTO drivers (driver_id, code, permanent_number, given_name, "
        "family_name, nationality, date_of_birth, wikipedia_url) "
        "VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


def load_constructors(conn: sqlite3.Connection) -> int:
    seen: dict[str, dict] = {}
    for season_dir in _season_dirs():
        f = season_dir / "constructors.json"
        if not f.exists():
            continue
        for c in _load_json(f)["MRData"]["ConstructorTable"]["Constructors"]:
            seen[c["constructorId"]] = c

    rows = [
        (c["constructorId"], c["name"], c.get("nationality"), c.get("url"))
        for c in seen.values()
    ]
    conn.executemany(
        "INSERT INTO constructors (constructor_id, name, nationality, wikipedia_url) "
        "VALUES (?,?,?,?)",
        rows,
    )
    return len(rows)


def load_circuits(conn: sqlite3.Connection) -> int:
    seen: dict[str, dict] = {}
    for season_dir in _season_dirs():
        f = season_dir / "circuits.json"
        if not f.exists():
            continue
        for c in _load_json(f)["MRData"]["CircuitTable"]["Circuits"]:
            seen[c["circuitId"]] = c

    rows = []
    for c in seen.values():
        loc = c.get("Location", {})
        rows.append((
            c["circuitId"],
            c["circuitName"],
            loc.get("locality"),
            loc.get("country"),
            _real(loc.get("lat")),
            _real(loc.get("long")),
            c.get("url"),
        ))
    conn.executemany(
        "INSERT INTO circuits (circuit_id, circuit_name, locality, country, "
        "latitude, longitude, wikipedia_url) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


def load_races(conn: sqlite3.Connection) -> int:
    rows = []
    for season_dir in _season_dirs():
        f = season_dir / "races.json"
        if not f.exists():
            continue
        for r in _load_json(f)["MRData"]["RaceTable"]["Races"]:
            rows.append((
                int(r["season"]),
                int(r["round"]),
                r["raceName"],
                r["date"],
                r.get("time"),
                r["Circuit"]["circuitId"],
                r.get("url"),
            ))
    conn.executemany(
        "INSERT INTO races (season, round, race_name, date, time, circuit_id, wikipedia_url) "
        "VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


def load_race_results(conn: sqlite3.Connection) -> int:
    rows = []
    for season_dir in _season_dirs():
        for round_dir in _round_dirs(season_dir):
            f = round_dir / "results.json"
            if not f.exists():
                continue
            races = _load_json(f)["MRData"]["RaceTable"]["Races"]
            if not races:
                continue
            race = races[0]
            season = int(race["season"])
            round_num = int(race["round"])
            for r in race.get("Results", []):
                time_obj = r.get("Time", {})
                fastest = r.get("FastestLap", {})
                rows.append((
                    season,
                    round_num,
                    r["Driver"]["driverId"],
                    r["Constructor"]["constructorId"],
                    _int(r.get("position")),
                    r["positionText"],
                    _real(r.get("points")) or 0.0,
                    int(r["grid"]),
                    int(r["laps"]),
                    r["status"],
                    _int(time_obj.get("millis")),
                    _int(fastest.get("rank")),
                    fastest.get("Time", {}).get("time") if fastest else None,
                ))
    conn.executemany(
        "INSERT INTO race_results (season, round, driver_id, constructor_id, "
        "position, position_text, points, grid, laps, status, time_millis, "
        "fastest_lap_rank, fastest_lap_time) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


def load_qualifying_results(conn: sqlite3.Connection) -> int:
    rows = []
    for season_dir in _season_dirs():
        for round_dir in _round_dirs(season_dir):
            f = round_dir / "qualifying.json"
            if not f.exists():
                continue
            races = _load_json(f)["MRData"]["RaceTable"]["Races"]
            if not races:
                continue
            race = races[0]
            season = int(race["season"])
            round_num = int(race["round"])
            for q in race.get("QualifyingResults", []):
                rows.append((
                    season,
                    round_num,
                    q["Driver"]["driverId"],
                    q["Constructor"]["constructorId"],
                    int(q["position"]),
                    q.get("Q1"),
                    q.get("Q2"),
                    q.get("Q3"),
                ))
    conn.executemany(
        "INSERT INTO qualifying_results (season, round, driver_id, constructor_id, "
        "position, q1, q2, q3) VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


def load_sprint_results(conn: sqlite3.Connection) -> int:
    """sprint.json is season-level and embeds SprintResults per sprint event."""
    rows = []
    for season_dir in _season_dirs():
        f = season_dir / "sprint.json"
        if not f.exists():
            continue
        for race in _load_json(f)["MRData"]["RaceTable"]["Races"]:
            season = int(race["season"])
            round_num = int(race["round"])
            for s in race.get("SprintResults", []):
                time_obj = s.get("Time", {})
                rows.append((
                    season,
                    round_num,
                    s["Driver"]["driverId"],
                    s["Constructor"]["constructorId"],
                    _int(s.get("position")),
                    s["positionText"],
                    _real(s.get("points")) or 0.0,
                    int(s["grid"]),
                    int(s["laps"]),
                    s["status"],
                    _int(time_obj.get("millis")),
                ))
    conn.executemany(
        "INSERT INTO sprint_results (season, round, driver_id, constructor_id, "
        "position, position_text, points, grid, laps, status, time_millis) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


def load_driver_standings(conn: sqlite3.Connection) -> int:
    """Ergast StandingsTable.StandingsLists[0].DriverStandings — one row per driver per season."""
    rows = []
    for season_dir in _season_dirs():
        f = season_dir / "driverstandings.json"
        if not f.exists():
            continue
        sl = _load_json(f)["MRData"]["StandingsTable"].get("StandingsLists", [])
        if not sl:
            continue
        season = int(sl[0]["season"])
        for ds in sl[0].get("DriverStandings", []):
            constructors = ds.get("Constructors", [])
            # Driver may have multiple constructors that season (mid-year switch);
            # Ergast lists them in order. Take the first as the primary team.
            constructor_id = constructors[0]["constructorId"] if constructors else None
            rows.append((
                season,
                ds["Driver"]["driverId"],
                int(ds["position"]),
                ds["positionText"],
                _real(ds.get("points")) or 0.0,
                int(ds["wins"]),
                constructor_id,
            ))
    conn.executemany(
        "INSERT INTO driver_standings (season, driver_id, position, position_text, "
        "points, wins, constructor_id) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


def load_constructor_standings(conn: sqlite3.Connection) -> int:
    rows = []
    for season_dir in _season_dirs():
        f = season_dir / "constructorstandings.json"
        if not f.exists():
            continue
        sl = _load_json(f)["MRData"]["StandingsTable"].get("StandingsLists", [])
        if not sl:
            continue
        season = int(sl[0]["season"])
        for cs in sl[0].get("ConstructorStandings", []):
            rows.append((
                season,
                cs["Constructor"]["constructorId"],
                int(cs["position"]),
                cs["positionText"],
                _real(cs.get("points")) or 0.0,
                int(cs["wins"]),
            ))
    conn.executemany(
        "INSERT INTO constructor_standings (season, constructor_id, position, position_text, "
        "points, wins) VALUES (?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


# ----------------------------------------------------------------------------
# Top-level orchestration
# ----------------------------------------------------------------------------


def build() -> None:
    log_path = configure_build_db_logger("ergast")
    print(f"[build_db] log file: {log_path}", file=sys.stderr)
    log.info("Ergast DB build started")

    DB_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
        log.info("Removed existing DB at %s", DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    log.info("Applied schema (9 tables + 7 indexes)")

    steps = [
        ("drivers", load_drivers),
        ("constructors", load_constructors),
        ("circuits", load_circuits),
        ("races", load_races),
        ("race_results", load_race_results),
        ("qualifying_results", load_qualifying_results),
        ("sprint_results", load_sprint_results),
        ("driver_standings", load_driver_standings),
        ("constructor_standings", load_constructor_standings),
    ]

    counts: dict[str, int] = {}
    for name, fn in steps:
        n = fn(conn)
        conn.commit()
        counts[name] = n
        log.info("Loaded %s: %d rows", name, n)

    conn.close()

    print("\nErgast SQLite build complete:")
    for name, n in counts.items():
        print(f"  {name:<25s} {n:>6,}")
    size_kb = DB_PATH.stat().st_size / 1024
    print(f"\n  DB path:    {DB_PATH}")
    print(f"  Size:       {size_kb:.1f} KB")
    print(f"  Total rows: {sum(counts.values()):,}")


if __name__ == "__main__":
    build()
