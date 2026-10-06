#!/usr/bin/env python3
"""
load_data.py

Initializes a SQLite database (cell_counts.db) in the repository root using
schema.sql, then loads every row of cell-count.csv into the normalized
subjects / samples / cell_counts tables.

Usage:
    python load_data.py [path/to/cell-count.csv]

If no path is given, it defaults to "cell-count.csv" in the repository root.
Safe to re-run: the database is rebuilt from scratch each time.
"""

import csv
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_CSV = ROOT / "cell-count.csv"
SCHEMA_PATH = ROOT / "schema.sql"
DB_PATH = Path(os.environ.get("CELL_DB", ROOT / "cell_counts.db"))

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def init_db(conn: sqlite3.Connection) -> None:
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())


def load_csv(conn: sqlite3.Connection, csv_path: Path) -> None:
    cur = conn.cursor()
    seen_subjects = set()

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            subject_id = row["subject"]

            if subject_id not in seen_subjects:
                cur.execute(
                    """
                    INSERT INTO subjects (subject_id, project, condition, age, sex, treatment, response)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(subject_id) DO NOTHING
                    """,
                    (
                        subject_id,
                        row["project"],
                        row["condition"],
                        int(row["age"]) if row["age"] not in ("", None) else None,
                        row["sex"],
                        row["treatment"],
                        row["response"] if row["response"] else None,
                    ),
                )
                seen_subjects.add(subject_id)

            cur.execute(
                """
                INSERT INTO samples (sample_id, subject_id, sample_type, time_from_treatment_start)
                VALUES (?, ?, ?, ?)
                """,
                (
                    row["sample"],
                    subject_id,
                    row["sample_type"],
                    int(row["time_from_treatment_start"])
                    if row["time_from_treatment_start"] not in ("", None)
                    else None,
                ),
            )

            for pop in POPULATIONS:
                cur.execute(
                    "INSERT INTO cell_counts (sample_id, population, count) VALUES (?, ?, ?)",
                    (row["sample"], pop, int(row[pop])),
                )

    conn.commit()


def main_build(csv_path: Path) -> None:
    if not csv_path.exists():
        print(f"ERROR: CSV file not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        load_csv(conn, csv_path)
    finally:
        conn.close()

    n_subjects = sqlite3.connect(DB_PATH).execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
    n_samples = sqlite3.connect(DB_PATH).execute("SELECT COUNT(*) FROM samples").fetchone()[0]
    n_counts = sqlite3.connect(DB_PATH).execute("SELECT COUNT(*) FROM cell_counts").fetchone()[0]
    print(f"Database created at {DB_PATH}")
    print(f"  subjects:    {n_subjects}")
    print(f"  samples:     {n_samples}")
    print(f"  cell_counts: {n_counts}")


def main() -> None:
    main_build(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV)


if __name__ == "__main__":
    main()
