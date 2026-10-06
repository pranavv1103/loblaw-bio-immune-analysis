"""
Basic sanity tests for analysis/queries.py.
Run with: pytest -q   (requires cell_counts.db to already exist — run
`python load_data.py` first, which `make pipeline` / `make test` does.)
"""

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analysis.queries import (  # noqa: E402
    DEFAULT_DB,
    avg_b_cells_melanoma_male_responders_t0,
    baseline_miraclib_melanoma_pbmc,
    cell_frequencies,
    responder_frequencies,
    responder_statistics,
)

pytestmark = pytest.mark.skipif(
    not Path(DEFAULT_DB).exists(), reason="cell_counts.db not built; run `python load_data.py` first"
)


@pytest.fixture
def conn():
    c = sqlite3.connect(DEFAULT_DB)
    yield c
    c.close()


def test_percentages_sum_to_100_per_sample(conn):
    df = cell_frequencies(conn)
    totals = df.groupby("sample")["percentage"].sum()
    assert (totals.round(1) == 100.0).all()


def test_frequency_table_columns(conn):
    df = cell_frequencies(conn)
    assert list(df.columns) == ["sample", "total_count", "population", "count", "percentage"]


def test_responder_frequencies_only_melanoma_pbmc_miraclib(conn):
    df = responder_frequencies(conn)
    assert (df["condition"] == "melanoma").all()
    assert (df["treatment"] == "miraclib").all()
    assert (df["sample_type"] == "PBMC").all()
    assert set(df["response"].unique()) <= {"yes", "no"}


def test_responder_statistics_has_all_populations(conn):
    df = responder_statistics(conn)
    assert set(df["population"]) == {"b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"}
    assert df["p_value"].between(0, 1).all()


def test_baseline_subset_filters_correctly(conn):
    df = baseline_miraclib_melanoma_pbmc(conn)
    assert (df["condition"] == "melanoma").all()
    assert (df["treatment"] == "miraclib").all()
    assert (df["sample_type"] == "PBMC").all()
    assert (df["time_from_treatment_start"] == 0).all()


def test_avg_b_cells_is_reasonable_float(conn):
    val = avg_b_cells_melanoma_male_responders_t0(conn)
    assert isinstance(val, float)
    assert val > 0
