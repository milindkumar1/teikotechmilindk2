PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS sample_cell_frequencies;
DROP TABLE IF EXISTS analysis_results;
DROP TABLE IF EXISTS cell_counts;
DROP TABLE IF EXISTS samples;
DROP TABLE IF EXISTS subjects;
DROP TABLE IF EXISTS populations;
DROP TABLE IF EXISTS projects;

CREATE TABLE projects (
    project_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE subjects (
    subject TEXT PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(project_id),
    condition TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 0),
    sex TEXT NOT NULL CHECK (sex IN ('M', 'F')),
    treatment TEXT NOT NULL,
    response TEXT CHECK (response IN ('yes', 'no') OR response IS NULL)
);

CREATE TABLE samples (
    sample TEXT PRIMARY KEY,
    subject TEXT NOT NULL REFERENCES subjects(subject),
    sample_type TEXT NOT NULL,
    time_from_treatment_start INTEGER NOT NULL CHECK (time_from_treatment_start >= 0),
    UNIQUE (subject, sample_type, time_from_treatment_start)
);

CREATE TABLE populations (
    population TEXT PRIMARY KEY
);

CREATE TABLE cell_counts (
    sample TEXT NOT NULL REFERENCES samples(sample) ON DELETE CASCADE,
    population TEXT NOT NULL REFERENCES populations(population),
    count INTEGER NOT NULL CHECK (count >= 0),
    PRIMARY KEY (sample, population)
);

CREATE TABLE analysis_results (
    population TEXT PRIMARY KEY REFERENCES populations(population),
    responder_n INTEGER NOT NULL,
    non_responder_n INTEGER NOT NULL,
    responder_median REAL NOT NULL,
    non_responder_median REAL NOT NULL,
    median_difference REAL NOT NULL,
    u_statistic REAL NOT NULL,
    p_value REAL NOT NULL,
    adjusted_p_value REAL NOT NULL,
    rank_biserial REAL NOT NULL,
    significant INTEGER NOT NULL CHECK (significant IN (0, 1)),
    method TEXT NOT NULL
);

CREATE INDEX idx_subjects_analysis
    ON subjects(condition, treatment, response);
CREATE INDEX idx_samples_analysis
    ON samples(sample_type, time_from_treatment_start, subject);
CREATE INDEX idx_cell_counts_population
    ON cell_counts(population);

CREATE VIEW sample_cell_frequencies AS
WITH totals AS (
    SELECT sample, SUM(count) AS total_count
    FROM cell_counts
    GROUP BY sample
)
SELECT
    counts.sample,
    totals.total_count,
    counts.population,
    counts.count,
    100.0 * counts.count / NULLIF(totals.total_count, 0) AS percentage
FROM cell_counts AS counts
JOIN totals USING (sample);

