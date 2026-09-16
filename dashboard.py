import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.cell_analysis.database import connect
from src.cell_analysis.paths import DATABASE_PATH
from src.cell_analysis.queries import (
    analysis_results,
    baseline_project_counts,
    baseline_samples,
    baseline_subject_counts,
    frequency_overview,
    male_responder_baseline_b_cell_average,
    responder_subject_frequencies,
)


POPULATION_ORDER = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
RESPONSE_LABELS = {"yes": "Responder", "no": "Non-responder"}


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame.from_records(rows)


@st.cache_data
def load_dashboard_data(database_path: str, modified_at: float) -> dict[str, object]:
    del modified_at
    with connect(Path(database_path)) as connection:
        return {
            "frequencies": _frame(frequency_overview(connection)),
            "subject_frequencies": _frame(responder_subject_frequencies(connection)),
            "statistics": _frame(analysis_results(connection)),
            "baseline": _frame(baseline_samples(connection)),
            "projects": _frame(baseline_project_counts(connection)),
            "responses": _frame(baseline_subject_counts(connection, "response")),
            "sexes": _frame(baseline_subject_counts(connection, "sex")),
            "b_cell_average": male_responder_baseline_b_cell_average(connection),
        }


def multiselect_filter(
    frame: pd.DataFrame, column: str, label: str
) -> pd.DataFrame:
    options = sorted(frame[column].dropna().unique().tolist())
    selected = st.multiselect(label, options, default=options)
    return frame[frame[column].isin(selected)]


def overview_page(frame: pd.DataFrame) -> None:
    st.subheader("Cell population frequencies")
    st.caption("Relative frequency is calculated within each biological sample.")

    with st.expander("Filters", expanded=True):
        first, second, third, fourth = st.columns(4)
        with first:
            frame = multiselect_filter(frame, "project", "Project")
        with second:
            frame = multiselect_filter(frame, "condition", "Condition")
        with third:
            frame = multiselect_filter(frame, "sample_type", "Sample type")
        with fourth:
            frame = multiselect_filter(frame, "population", "Population")
        sample_search = st.text_input("Sample ID contains")
        if sample_search:
            frame = frame[
                frame["sample"].str.contains(sample_search, case=False, regex=False)
            ]

    sample_count = frame["sample"].nunique()
    subject_count = frame["subject"].nunique()
    first, second, third = st.columns(3)
    first.metric("Samples", f"{sample_count:,}")
    second.metric("Subjects", f"{subject_count:,}")
    third.metric("Population rows", f"{len(frame):,}")

    display_columns = ["sample", "total_count", "population", "count", "percentage"]
    st.dataframe(
        frame[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "percentage": st.column_config.NumberColumn(format="%.2f%%"),
            "total_count": st.column_config.NumberColumn(format="%d"),
            "count": st.column_config.NumberColumn(format="%d"),
        },
    )
    st.download_button(
        "Download filtered frequencies",
        frame[display_columns].to_csv(index=False),
        file_name="cell_frequencies.csv",
        mime="text/csv",
    )


def responder_page(subject_frequencies: pd.DataFrame, statistics: pd.DataFrame) -> None:
    st.subheader("Miraclib response in melanoma PBMC samples")
    st.caption(
        "Each plotted value is a subject's mean frequency across available visits, "
        "so repeated samples are not treated as independent observations."
    )
    chart_data = subject_frequencies.copy()
    chart_data["response_group"] = chart_data["response"].map(RESPONSE_LABELS)
    chart_data["population"] = pd.Categorical(
        chart_data["population"], categories=POPULATION_ORDER, ordered=True
    )
    figure = px.box(
        chart_data.sort_values("population"),
        x="response_group",
        y="percentage",
        color="response_group",
        facet_col="population",
        facet_col_wrap=3,
        points="outliers",
        category_orders={
            "response_group": ["Responder", "Non-responder"],
            "population": POPULATION_ORDER,
        },
        labels={
            "response_group": "Response",
            "percentage": "Mean relative frequency (%)",
            "population": "Population",
        },
        color_discrete_map={"Responder": "#28666e", "Non-responder": "#d96c4f"},
    )
    figure.for_each_annotation(
        lambda annotation: annotation.update(text=annotation.text.split("=")[-1])
    )
    figure.update_layout(showlegend=False, height=680, margin={"t": 40})
    st.plotly_chart(figure, use_container_width=True)

    if statistics.empty:
        st.warning("Statistical results are missing. Run `make pipeline`.")
        return
    table = statistics.copy()
    table["significant"] = table["significant"].astype(bool)
    st.dataframe(
        table[
            [
                "population",
                "responder_n",
                "non_responder_n",
                "responder_median",
                "non_responder_median",
                "median_difference",
                "adjusted_p_value",
                "rank_biserial",
                "significant",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "responder_median": st.column_config.NumberColumn(format="%.3f"),
            "non_responder_median": st.column_config.NumberColumn(format="%.3f"),
            "median_difference": st.column_config.NumberColumn(format="%.3f"),
            "adjusted_p_value": st.column_config.NumberColumn(format="%.4g"),
            "rank_biserial": st.column_config.NumberColumn(format="%.3f"),
        },
    )
    significant = table.loc[table["significant"], "population"].tolist()
    if significant:
        st.success("Significant after BH adjustment: " + ", ".join(significant))
    else:
        st.info("No population is significant after BH adjustment at α = 0.05.")


def subset_page(data: dict[str, object]) -> None:
    baseline = data["baseline"]
    st.subheader("Baseline melanoma PBMC subset")
    st.caption("Miraclib-treated samples collected at day 0.")

    first, second, third = st.columns(3)
    first.metric("Samples", f"{len(baseline):,}")
    second.metric("Subjects", f"{baseline['subject'].nunique():,}")
    third.metric(
        "Male responder mean B cells",
        f"{data['b_cell_average']:,.2f}",
        help="All melanoma sample and treatment types at day 0",
    )

    project_counts = data["projects"].rename(
        columns={"project": "Project", "sample_count": "Samples"}
    )
    response_counts = data["responses"].replace(
        {"category": RESPONSE_LABELS}
    ).rename(columns={"category": "Response", "subject_count": "Subjects"})
    sex_counts = data["sexes"].replace(
        {"category": {"M": "Male", "F": "Female"}}
    ).rename(columns={"category": "Sex", "subject_count": "Subjects"})

    first, second, third = st.columns(3)
    first.markdown("**Samples by project**")
    first.dataframe(project_counts, hide_index=True, use_container_width=True)
    second.markdown("**Subjects by response**")
    second.dataframe(response_counts, hide_index=True, use_container_width=True)
    third.markdown("**Subjects by sex**")
    third.dataframe(sex_counts, hide_index=True, use_container_width=True)

    st.markdown("**Matching samples**")
    st.dataframe(baseline, hide_index=True, use_container_width=True)


def main() -> None:
    st.set_page_config(
        page_title="Loblaw Bio Cell Analysis",
        page_icon="🧬",
        layout="wide",
    )
    st.title("Loblaw Bio immune cell analysis")
    if not DATABASE_PATH.is_file():
        st.error("Database not found. Run `make pipeline` first.")
        st.stop()

    try:
        data = load_dashboard_data(str(DATABASE_PATH), DATABASE_PATH.stat().st_mtime)
    except sqlite3.DatabaseError as error:
        st.error(f"Unable to read the analysis database: {error}")
        st.stop()

    overview, response, subset = st.tabs(
        ["Frequency overview", "Responder analysis", "Baseline subset"]
    )
    with overview:
        overview_page(data["frequencies"])
    with response:
        responder_page(data["subject_frequencies"], data["statistics"])
    with subset:
        subset_page(data)


if __name__ == "__main__":
    main()
