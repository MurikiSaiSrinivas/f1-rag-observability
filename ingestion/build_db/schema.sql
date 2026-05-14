-- F1 RAG Observability — Ergast SQLite schema
--
-- Built from data/raw/ergast/ JSON files by ingestion/build_db/loader.py.
-- 9 tables, normalized. Composite primary keys use natural Ergast identifiers
-- (driver_id, constructor_id, circuit_id, (season, round)) rather than
-- surrogate INTEGER keys — keeps queries debuggable and avoids extra JOINs.
--
-- The query-time connection opens this DB in read-only mode (mode=ro) so even
-- LLM-hallucinated DDL/DML against this database fails harmlessly.

-- ============================================================
-- ENTITY MASTERS
-- ============================================================

CREATE TABLE drivers (
    driver_id        TEXT PRIMARY KEY,           -- Ergast: "max_verstappen"
    code             TEXT,                        -- e.g., "VER"
    permanent_number INTEGER,                     -- career number, e.g., 1, 33
    given_name       TEXT NOT NULL,
    family_name      TEXT NOT NULL,
    nationality      TEXT,                        -- "Dutch", "British", etc.
    date_of_birth    TEXT,                        -- YYYY-MM-DD
    wikipedia_url    TEXT
);

CREATE TABLE constructors (
    constructor_id   TEXT PRIMARY KEY,           -- Ergast: "red_bull", "mercedes"
    name             TEXT NOT NULL,
    nationality      TEXT,
    wikipedia_url    TEXT
);

CREATE TABLE circuits (
    circuit_id       TEXT PRIMARY KEY,           -- Ergast: "monaco", "bahrain"
    circuit_name     TEXT NOT NULL,
    locality         TEXT,                        -- city
    country          TEXT,
    latitude         REAL,
    longitude        REAL,
    wikipedia_url    TEXT
);

-- ============================================================
-- RACE CALENDAR
-- ============================================================

CREATE TABLE races (
    season           INTEGER NOT NULL,
    round            INTEGER NOT NULL,
    race_name        TEXT NOT NULL,               -- "Bahrain Grand Prix"
    date             TEXT NOT NULL,               -- YYYY-MM-DD
    time             TEXT,                         -- HH:MM:SSZ (UTC), may be NULL
    circuit_id       TEXT NOT NULL REFERENCES circuits(circuit_id),
    wikipedia_url    TEXT,
    PRIMARY KEY (season, round)
);

-- ============================================================
-- PER-RACE RESULTS
-- One row per (race, driver). status is free text ("Finished",
-- "+1 Lap", "Engine", "Accident", "Brakes", ...).
-- position is INTEGER (NULL for retirements); position_text is the
-- Ergast literal ("1", "R" for retired, "D" disqualified, etc.).
-- ============================================================

CREATE TABLE race_results (
    season           INTEGER NOT NULL,
    round            INTEGER NOT NULL,
    driver_id        TEXT NOT NULL REFERENCES drivers(driver_id),
    constructor_id   TEXT NOT NULL REFERENCES constructors(constructor_id),
    position         INTEGER,
    position_text    TEXT NOT NULL,
    points           REAL NOT NULL,
    grid             INTEGER NOT NULL,
    laps             INTEGER NOT NULL,
    status           TEXT NOT NULL,
    time_millis      INTEGER,                     -- winner: full race time; others: gap; NULL for DNF
    fastest_lap_rank INTEGER,
    fastest_lap_time TEXT,                        -- "1:30.123"
    PRIMARY KEY (season, round, driver_id),
    FOREIGN KEY (season, round) REFERENCES races(season, round)
);

CREATE TABLE qualifying_results (
    season           INTEGER NOT NULL,
    round            INTEGER NOT NULL,
    driver_id        TEXT NOT NULL REFERENCES drivers(driver_id),
    constructor_id   TEXT NOT NULL REFERENCES constructors(constructor_id),
    position         INTEGER NOT NULL,
    q1               TEXT,                         -- "1:30.123", may be NULL
    q2               TEXT,
    q3               TEXT,
    PRIMARY KEY (season, round, driver_id),
    FOREIGN KEY (season, round) REFERENCES races(season, round)
);

CREATE TABLE sprint_results (
    season           INTEGER NOT NULL,
    round            INTEGER NOT NULL,
    driver_id        TEXT NOT NULL REFERENCES drivers(driver_id),
    constructor_id   TEXT NOT NULL REFERENCES constructors(constructor_id),
    position         INTEGER,
    position_text    TEXT NOT NULL,
    points           REAL NOT NULL,
    grid             INTEGER NOT NULL,
    laps             INTEGER NOT NULL,
    status           TEXT NOT NULL,
    time_millis      INTEGER,
    PRIMARY KEY (season, round, driver_id),
    FOREIGN KEY (season, round) REFERENCES races(season, round)
);

-- ============================================================
-- END-OF-SEASON STANDINGS
-- Precomputed by Ergast; handles edge cases like half-points for
-- shortened races. Use these for "who was champion?" style questions.
-- ============================================================

CREATE TABLE driver_standings (
    season           INTEGER NOT NULL,
    driver_id        TEXT NOT NULL REFERENCES drivers(driver_id),
    position         INTEGER NOT NULL,
    position_text    TEXT NOT NULL,
    points           REAL NOT NULL,
    wins             INTEGER NOT NULL,
    constructor_id   TEXT REFERENCES constructors(constructor_id),  -- primary team that season; NULL if driver switched
    PRIMARY KEY (season, driver_id)
);

CREATE TABLE constructor_standings (
    season           INTEGER NOT NULL,
    constructor_id   TEXT NOT NULL REFERENCES constructors(constructor_id),
    position         INTEGER NOT NULL,
    position_text    TEXT NOT NULL,
    points           REAL NOT NULL,
    wins             INTEGER NOT NULL,
    PRIMARY KEY (season, constructor_id)
);

-- ============================================================
-- INDEXES — cover the SQL-generator's common access patterns
-- ============================================================

CREATE INDEX idx_race_results_driver         ON race_results(driver_id, season);
CREATE INDEX idx_race_results_constructor    ON race_results(constructor_id, season);
CREATE INDEX idx_race_results_position       ON race_results(position);
CREATE INDEX idx_qualifying_results_driver   ON qualifying_results(driver_id, season);
CREATE INDEX idx_sprint_results_driver       ON sprint_results(driver_id, season);
CREATE INDEX idx_races_circuit               ON races(circuit_id);
CREATE INDEX idx_driver_standings_position   ON driver_standings(position);
