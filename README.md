# Loblaw Bio — Miraclib Immune Cell Population Analysis

Analysis pipeline and interactive dashboard for Bob Loblaw's clinical trial
data (`cell-count.csv`), answering:

- **Part 2** — relative frequency of each immune cell population per sample
- **Part 3** — responders vs non-responders to miraclib in melanoma (PBMC samples), with boxplots and significance testing
- **Part 4** — baseline (t=0) melanoma/miraclib/PBMC subset breakdown, and the average B-cell count for melanoma male responders at t=0

## Project structure

```
.
├── cell-count.csv          # source data
├── schema.sql               # SQLite schema (subjects / samples / cell_counts)
├── load_data.py              # builds cell_counts.db from the CSV
├── analysis/
│   └── queries.py            # Part 2-4 query/analysis functions
├── dashboard/
│   └── app.py                 # Streamlit dashboard (Parts 2-4)
├── tests/
│   └── test_queries.py
├── requirements.txt
└── Makefile
```

## Database design

Three normalized tables (see `schema.sql`):

- `subjects` — one row per subject: `project`, `condition`, `age`, `sex`, `treatment`, `response`. These fields are constant across all of a subject's samples in the source data, so they're stored once per subject instead of repeated per row.
- `samples` — one row per sample: `sample_id`, `subject_id` (FK), `sample_type`, `time_from_treatment_start`.
- `cell_counts` — long/tidy format, one row per `(sample_id, population)` with the raw `count`. Using a long table instead of one column per population means adding a new cell population later needs no schema change.

## Running it

This was built and tested against **Python 3.11+** (works in GitHub Codespaces' default Python environment).

```bash
make setup      # pip install -r requirements.txt
make pipeline   # builds cell_counts.db from cell-count.csv
make dashboard  # starts the Streamlit dashboard at http://localhost:8501
```

Run tests with:

```bash
pytest -q
```

### Running steps manually

```bash
python load_data.py                 # creates cell_counts.db in the repo root
python -m analysis.queries           # prints Part 2-4 results to the console
streamlit run dashboard/app.py       # launches the dashboard
```

`load_data.py` takes an optional path argument if your CSV lives elsewhere:
`python load_data.py path/to/other.csv`.

## Dashboard

The dashboard has three tabs:

1. **Part 2 — Frequency Overview**: the full per-sample/per-population frequency table (filterable, downloadable as CSV) and an overall composition chart.
2. **Part 3 — Responders vs Non-Responders**: boxplots of relative frequency by population and response status (melanoma, miraclib, PBMC only), plus a Mann-Whitney U test table flagging which populations differ significantly (p < 0.05).
3. **Part 4 — Baseline Subset**: sample counts per project, responder/non-responder counts, sex breakdown for the baseline (t=0) melanoma/miraclib/PBMC subset, and the average B-cell count for melanoma male responders at t=0.

**Link to hosted dashboard:** _add your deployed Streamlit Community Cloud (or equivalent) URL here after deploying — e.g. `https://share.streamlit.io/<user>/<repo>/main/dashboard/app.py`._

## Statistical methodology (Part 3)

Relative frequencies (%) per population are compared between responders and
non-responders using a two-sided **Mann-Whitney U test** (rather than a
t-test), since percentage data is bounded between 0 and 100 and not
guaranteed to be normally distributed; the rank-based test avoids that
assumption. A population is flagged as significant at p < 0.05
(uncorrected for the 5 simultaneous comparisons across populations — note
this for Bob if he wants a stricter, multiple-comparison-corrected threshold
such as Bonferroni, e.g. p < 0.01).

## Part 4.3 answer

Considering melanoma male subjects across **all** sample types and
treatments, the average B-cell count for **responders** at
`time_from_treatment_start = 0` is **10206.15**.

Reproduce: `make pipeline`, then `python -m analysis.queries` (last section), or call
`analysis.queries.avg_b_cells_melanoma_male_responders_t0()`. It is also shown on the
dashboard's Part 4 tab.
