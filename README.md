# Loblaw Bio: Miraclib Immune Cell Population Analysis

This repo holds the analysis pipeline and interactive dashboard for Bob Loblaw's clinical trial data (`cell-count.csv`). It answers three questions:

- **Part 2:** what share of each sample is made up of each immune cell population?
- **Part 3:** do melanoma patients on miraclib who respond differ from those who don't (PBMC samples only)?
- **Part 4:** what does the baseline (t=0) melanoma/miraclib/PBMC subset look like, and what is the average B-cell count for melanoma male responders at t=0?

**Link to hosted dashboard:** https://loblaw-bio-immune.streamlit.app/

## Project structure

```
.
├── cell-count.csv          # source data
├── schema.sql              # SQLite schema (subjects / samples / cell_counts)
├── load_data.py            # builds cell_counts.db from the CSV
├── analysis/
│   └── queries.py          # Part 2-4 query and analysis functions
├── dashboard/
│   └── app.py              # Streamlit dashboard (Parts 2-4)
├── tests/
│   └── test_queries.py
├── requirements.txt
└── Makefile
```

## Database design

There are three normalized tables (see `schema.sql`):

- `subjects`: one row per subject (`project`, `condition`, `age`, `sex`, `treatment`, `response`). These fields never change across a subject's samples, so they are stored once instead of being repeated on every row.
- `samples`: one row per sample (`sample_id`, `subject_id` as a foreign key, `sample_type`, `time_from_treatment_start`).
- `cell_counts`: long format, one row per `(sample_id, population)` holding the raw `count`. A long table means a new cell population can be added later without changing the schema, and per-population queries stay simple.

## How to run it

Tested with Python 3.11 and newer, and it works in the default GitHub Codespaces environment.

```bash
make setup      # pip install -r requirements.txt
make pipeline   # builds cell_counts.db from cell-count.csv
make dashboard  # starts the Streamlit dashboard at http://localhost:8501
```

Run the tests with:

```bash
pytest -q
```

If you prefer to run the steps by hand:

```bash
python load_data.py              # creates cell_counts.db in the repo root
python -m analysis.queries       # prints the Part 2-4 results to the console
streamlit run dashboard/app.py   # launches the dashboard
```

`load_data.py` rebuilds the database from scratch each time, so it is safe to re-run. It also accepts an optional CSV path: `python load_data.py path/to/other.csv`.

## Dashboard

The dashboard reads from the SQLite database, not the raw CSV, and has three tabs:

1. **Part 2, Frequency Overview:** the full per-sample, per-population frequency table (filterable, with CSV download) and a chart of the average composition.
2. **Part 3, Responders vs Non-Responders:** boxplots of relative frequency by population and response (melanoma, miraclib, PBMC only), a Mann-Whitney U test table, and a one-line plain-English summary of what differs.
3. **Part 4, Baseline Subset:** samples per project, responder and non-responder counts, and sex counts for the baseline subset, plus the average B-cell metric from Part 4.3.

## Statistical methodology (Part 3)

Relative frequencies (%) are compared between responders and non-responders with a two-sided **Mann-Whitney U test**. Percentages are bounded between 0 and 100 and may not be normally distributed, so a rank-based test is safer than a t-test.

With 993 responder samples and 975 non-responder samples, only **cd4_t_cell** is significant at p < 0.05 (p = 0.0133). The closest other population is b_cell at p = 0.0557.

These p-values are **not corrected for multiple comparisons** across the 5 populations. A Bonferroni correction would use a threshold of 0.05 / 5 = 0.01, and cd4_t_cell (p = 0.0133) would no longer be significant under it. Treat the cd4_t_cell result as a lead worth following up, not a firm finding.

## Part 4.3 answer

For melanoma males across **all** sample types and treatments, the average B-cell count for **responders** at `time_from_treatment_start = 0` is **10206.15**.

To reproduce it, run `make pipeline`, then `python -m analysis.queries` and look at the last section. You can also call `analysis.queries.avg_b_cells_melanoma_male_responders_t0()`. The same number appears on the dashboard's Part 4 tab.
