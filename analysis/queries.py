"""
analysis/queries.py

All analytical queries for Parts 2-4 of Bob's request, built on top of the
SQLite database produced by load_data.py. Pure functions that take a
sqlite3 connection (or db path) and return pandas DataFrames, so they can be
reused by the dashboard, by tests, or from a plain Python REPL.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "cell_counts.db"

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def get_connection(db_path: Path | str = DEFAULT_DB) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


# ---------------------------------------------------------------------------
# Part 2: relative frequency summary table
# ---------------------------------------------------------------------------

def cell_frequencies(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    One row per (sample, population):
      sample, total_count, population, count, percentage
    """
    counts = pd.read_sql_query(
        "SELECT sample_id AS sample, population, count FROM cell_counts", conn
    )
    totals = counts.groupby("sample")["count"].sum().rename("total_count")
    df = counts.merge(totals, on="sample")
    df["percentage"] = (df["count"] / df["total_count"] * 100).round(4)
    return df[["sample", "total_count", "population", "count", "percentage"]].sort_values(
        ["sample", "population"]
    ).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Part 3: responders vs non-responders (melanoma, miraclib, PBMC)
# ---------------------------------------------------------------------------

def responder_frequencies(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Relative frequencies restricted to melanoma patients treated with miraclib,
    PBMC samples only, labeled with response (yes/no).
    """
    freq = cell_frequencies(conn)

    meta = pd.read_sql_query(
        """
        SELECT s.sample_id AS sample, s.sample_type, su.condition, su.treatment, su.response
        FROM samples s
        JOIN subjects su ON su.subject_id = s.subject_id
        WHERE su.condition = 'melanoma'
          AND su.treatment = 'miraclib'
          AND s.sample_type = 'PBMC'
          AND su.response IS NOT NULL
        """,
        conn,
    )

    out = freq.merge(meta, on="sample", how="inner")
    return out


def responder_statistics(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    For each population, Mann-Whitney U test comparing responders vs
    non-responders relative frequency (%). Returns population, n_responder,
    n_non_responder, median_responder, median_non_responder, p_value,
    significant (p < 0.05).
    """
    df = responder_frequencies(conn)
    rows = []
    for pop in POPULATIONS:
        sub = df[df["population"] == pop]
        resp = sub[sub["response"] == "yes"]["percentage"]
        nonresp = sub[sub["response"] == "no"]["percentage"]
        if len(resp) > 0 and len(nonresp) > 0:
            u_stat, p_value = stats.mannwhitneyu(resp, nonresp, alternative="two-sided")
        else:
            u_stat, p_value = float("nan"), float("nan")
        rows.append(
            {
                "population": pop,
                "n_responder": len(resp),
                "n_non_responder": len(nonresp),
                "median_responder_pct": round(resp.median(), 3) if len(resp) else None,
                "median_non_responder_pct": round(nonresp.median(), 3) if len(nonresp) else None,
                "u_statistic": round(u_stat, 3) if pd.notna(u_stat) else None,
                "p_value": round(p_value, 5) if pd.notna(p_value) else None,
                "significant_p<0.05": bool(p_value < 0.05) if pd.notna(p_value) else False,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Part 4: baseline melanoma PBMC miraclib subset
# ---------------------------------------------------------------------------

def baseline_miraclib_melanoma_pbmc(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    All melanoma PBMC samples at baseline (time_from_treatment_start = 0)
    from subjects treated with miraclib. One row per sample, with subject metadata.
    """
    return pd.read_sql_query(
        """
        SELECT s.sample_id AS sample, s.sample_type, s.time_from_treatment_start,
               su.subject_id, su.project, su.condition, su.treatment, su.response, su.sex, su.age
        FROM samples s
        JOIN subjects su ON su.subject_id = s.subject_id
        WHERE su.condition = 'melanoma'
          AND su.treatment = 'miraclib'
          AND s.sample_type = 'PBMC'
          AND s.time_from_treatment_start = 0
        """,
        conn,
    )


def baseline_subset_breakdown(conn: sqlite3.Connection) -> dict:
    """
    For the baseline melanoma/miraclib/PBMC subset (Part 4.1), returns:
      - samples_per_project: DataFrame(project, n_samples)
      - responders_vs_non: DataFrame(response, n_subjects)
      - sex_breakdown: DataFrame(sex, n_subjects)
    Subject counts are de-duplicated by subject_id (a subject could in theory
    contribute more than one baseline sample; here each contributes one row
    per sample but is counted once per subject for responder/sex breakdowns).
    """
    df = baseline_miraclib_melanoma_pbmc(conn)

    samples_per_project = (
        df.groupby("project")["sample"].nunique().reset_index(name="n_samples")
    )

    subjects = df.drop_duplicates(subset="subject_id")
    responders_vs_non = (
        subjects.groupby("response")["subject_id"].nunique().reset_index(name="n_subjects")
    )
    sex_breakdown = (
        subjects.groupby("sex")["subject_id"].nunique().reset_index(name="n_subjects")
    )

    return {
        "samples_per_project": samples_per_project,
        "responders_vs_non": responders_vs_non,
        "sex_breakdown": sex_breakdown,
    }


def avg_b_cells_melanoma_male_responders_t0(conn: sqlite3.Connection) -> float:
    """
    Considering melanoma males of ALL sample and treatment types, the average
    number of B cells for responders at time_from_treatment_start = 0.
    Returns a float rounded to 2 decimals.
    """
    query = """
        SELECT cc.count AS b_cell_count
        FROM cell_counts cc
        JOIN samples s ON s.sample_id = cc.sample_id
        JOIN subjects su ON su.subject_id = s.subject_id
        WHERE cc.population = 'b_cell'
          AND su.condition = 'melanoma'
          AND su.sex = 'M'
          AND su.response = 'yes'
          AND s.time_from_treatment_start = 0
    """
    df = pd.read_sql_query(query, conn)
    return round(df["b_cell_count"].mean(), 2)


if __name__ == "__main__":
    conn = get_connection()
    print("=== Part 2: cell frequencies (head) ===")
    print(cell_frequencies(conn).head(), "\n")

    print("=== Part 3: responder statistics ===")
    print(responder_statistics(conn), "\n")

    print("=== Part 4.1/4.2: baseline subset breakdown ===")
    breakdown = baseline_subset_breakdown(conn)
    for k, v in breakdown.items():
        print(f"-- {k} --")
        print(v, "\n")

    print("=== Part 4.3: avg B cells, melanoma males, responders, t=0 ===")
    print(avg_b_cells_melanoma_male_responders_t0(conn))

    conn.close()
