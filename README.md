# Immune Cell Population Analysis

This project loads clinical-trial cell counts into a normalized SQLite database,
calculates per-sample cell frequencies, compares miraclib responders with
non-responders, and presents the results in an interactive dashboard.

[Open the local dashboard](http://localhost:8501)

## Run in GitHub Codespaces

Python 3.11 or newer is recommended.

```bash
make setup
make pipeline
make dashboard
```

Codespaces will offer to open the forwarded dashboard port. Locally, visit
<http://localhost:8501>.

The pipeline creates `cell_count.db` in the repository root. The database is a
generated artifact and is excluded from Git.

## Commands

```bash
python load_data.py   # Rebuild the SQLite database from cell-count.csv
python run_analysis.py
make test
```

The required automation targets are:

- `make setup`: installs pinned Python dependencies.
- `make pipeline`: rebuilds the database and runs the responder analysis.
- `make dashboard`: starts Streamlit on port `8501`, or the port in `$PORT`.

## Database design

The schema separates projects, subjects, samples, populations, and cell counts.
`sample_cell_frequencies` is a SQL view with the required columns:

```text
sample, total_count, population, count, percentage
```

The source CSV names the clinical fields `condition` and `sex`; these correspond
to indication and gender in the task description.

## Statistical method

The responder analysis includes melanoma subjects treated with miraclib whose
sample type is PBMC. Each subject has repeated visits, so frequencies are first
averaged by subject and population. Responders and non-responders are compared
with a two-sided Mann–Whitney U test. P-values across the five populations are
adjusted with the Benjamini–Hochberg procedure, using an adjusted significance
threshold of `0.05`. Rank-biserial correlation is reported as an effect size.

These comparisons identify associations with response; they do not establish a
validated predictive model.

## Baseline subset

The dashboard reports melanoma PBMC samples collected at day 0 from subjects
treated with miraclib, including counts by project, response, and sex. It also
reports the requested day-0 average B-cell count for male melanoma responders
across all treatments and sample types.
