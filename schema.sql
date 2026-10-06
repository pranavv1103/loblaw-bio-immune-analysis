-- Loblaw Bio cell-count database schema
-- Normalized relational design:
--   subjects      : one row per patient/subject (project, condition, treatment, response, sex, age)
--   samples       : one row per biological sample, FK to subjects (sample_type, time_from_treatment_start)
--   cell_counts   : long/tidy table, one row per (sample, population) with raw count
--
-- Rationale: subject-level attributes (project, condition, treatment, sex, age, response)
-- are constant across all of a subject's samples in the source data, so they are
-- stored once per subject rather than repeated on every sample row. Cell counts are
-- stored in a long format (population, count) rather than one column per population so
-- that adding a new immune population later requires no schema change.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS cell_counts;
DROP TABLE IF EXISTS samples;
DROP TABLE IF EXISTS subjects;

CREATE TABLE subjects (
    subject_id      TEXT PRIMARY KEY,
    project          TEXT NOT NULL,
    condition        TEXT NOT NULL,
    age              INTEGER,
    sex              TEXT,
    treatment        TEXT NOT NULL,
    response         TEXT                -- 'yes' / 'no' / NULL (e.g. untreated / healthy)
);

CREATE TABLE samples (
    sample_id                  TEXT PRIMARY KEY,
    subject_id                 TEXT NOT NULL REFERENCES subjects(subject_id),
    sample_type                TEXT NOT NULL,      -- PBMC / WB
    time_from_treatment_start  INTEGER
);

CREATE TABLE cell_counts (
    sample_id   TEXT NOT NULL REFERENCES samples(sample_id),
    population  TEXT NOT NULL,      -- b_cell / cd8_t_cell / cd4_t_cell / nk_cell / monocyte
    count       INTEGER NOT NULL,
    PRIMARY KEY (sample_id, population)
);

CREATE INDEX idx_samples_subject ON samples(subject_id);
CREATE INDEX idx_cellcounts_sample ON cell_counts(sample_id);
CREATE INDEX idx_subjects_condition_treatment ON subjects(condition, treatment);
