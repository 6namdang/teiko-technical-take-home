'''
Dashboard: shows the Part 2 - 4 results from teiko.db

run with: streamlit run dashboard.py
(teiko.db has to exist first, so run make pipeline before)
'''
import os
import sqlite3

import pandas as pd
import streamlit as st

from initial_analysis import get_frequency_table
from statistical_analysis import alpha, compare_responders, days, get_cohort, plot_boxplot
from data_subset_analysis import (count_by_project, count_by_response, count_by_sex,
                                  get_subset_samples)

db_name = "teiko.db"

st.set_page_config(page_title="Cell Count Analysis", layout="wide")

if not os.path.exists(db_name):
    st.error("teiko.db not found. Run `make pipeline` first, then reload this page.")
    st.stop()


# the database doesn't change while the dashboard runs, so load each result once
@st.cache_data
def load_frequency_table():
    connection_obj = sqlite3.connect(db_name)
    df = get_frequency_table(connection_obj)
    connection_obj.close()
    return df


@st.cache_data
def load_cohort():
    connection_obj = sqlite3.connect(db_name)
    df = get_cohort(connection_obj)
    connection_obj.close()
    return df


@st.cache_data
def load_subset():
    connection_obj = sqlite3.connect(db_name)
    samples = get_subset_samples(connection_obj)
    by_project = count_by_project(connection_obj)
    by_response = count_by_response(connection_obj)
    by_sex = count_by_sex(connection_obj)
    connection_obj.close()
    return samples, by_project, by_response, by_sex


def format_results(results):
    # readable column names for the test tables
    return results.rename(columns={
        "population": "Population",
        "responder_median": "Responders, median %",
        "non_responder_median": "Non-responders, median %",
        "U": "U",
        "p_value": "p-value",
        "p_adj": "Adjusted p",
        "significant": "Significant",
    })


# ---------- sidebar ----------
pages = {
    "Part 2": "Cell frequencies",
    "Part 3": "Response comparison",
    "Part 4": "Baseline subset",
}
with st.sidebar:
    st.markdown("### Cell Count Analysis")
    st.caption("Miraclib clinical trial")
    page = st.radio("Section", list(pages), format_func=lambda k: f"{k}  ·  {pages[k]}",
                    label_visibility="collapsed")


# ---------- Part 2 ----------
if page == "Part 2":
    st.title("Cell frequencies")

    summary = load_frequency_table()

    overview = pd.DataFrame([{
        "Samples": f"{summary['sample'].nunique():,}",
        "Populations": summary["population"].nunique(),
        "Rows": f"{len(summary):,}",
    }])
    st.table(overview, border=True, hide_index=True)

    col1, col2 = st.columns([2, 3])
    search = col1.text_input("Sample", placeholder="e.g. sample00000")
    chosen = col2.multiselect("Population", summary["population"].unique().tolist(),
                              placeholder="All populations")

    shown = summary
    if search:
        shown = shown[shown["sample"].str.contains(search.strip(), case=False)]
    if chosen:
        shown = shown[shown["population"].isin(chosen)]

    st.dataframe(
        shown, hide_index=True, width="stretch", height=520,
        column_config={
            "sample": "Sample",
            "total_count": st.column_config.NumberColumn("Total count", format="%d"),
            "population": "Population",
            "count": st.column_config.NumberColumn("Count", format="%d"),
            "percentage": st.column_config.NumberColumn("Percentage", format="%.2f%%"),
        },
    )
    st.download_button("Download CSV", shown.to_csv(index=False), "cell_frequencies.csv",
                       "text/csv")


# ---------- Part 3 ----------
elif page == "Part 3":
    st.title("Response comparison")
    st.caption("Melanoma patients on miraclib, PBMC samples. Responders vs non-responders.")

    cohort = load_cohort()
    results_by_day = {day: compare_responders(cohort[cohort["day"] == day]) for day in days}
    baseline = results_by_day[0]
    n_significant = int(baseline["significant"].sum())

    # one baseline sample per patient, so counting day 0 samples counts patients
    baseline_samples = cohort[cohort["day"] == 0]
    overview = pd.DataFrame([{
        "Responders": baseline_samples.loc[baseline_samples["response"] == "yes", "sample"].nunique(),
        "Non-responders": baseline_samples.loc[baseline_samples["response"] == "no", "sample"].nunique(),
        "Significant at baseline": f"{n_significant} of {len(baseline)}",
    }])
    st.table(overview, border=True, hide_index=True)

    if n_significant:
        names = ", ".join(baseline.loc[baseline["significant"], "population"])
        st.success(f"At baseline, {names} differ between responders and non-responders.")
    else:
        st.info("No population differs between responders and non-responders at baseline, "
                "so none of them predicts response to miraclib.")

    labels = {0: "Day 0 (baseline)", 7: "Day 7", 14: "Day 14", "all": "All days"}
    day_choice = st.segmented_control("Time point", [0, 7, 14, "all"], default=0,
                                      format_func=lambda d: labels[d])
    if day_choice is None:
        day_choice = 0

    plot_df = cohort if day_choice == "all" else cohort[cohort["day"] == day_choice]
    st.pyplot(plot_boxplot(plot_df, ""))

    if day_choice == "all":
        st.markdown("**Adjusted p-value by time point**")
        table = {labels[d]: results_by_day[d].set_index("population")["p_adj"] for d in days}
        st.dataframe(pd.DataFrame(table), width="stretch",
                     column_config={k: st.column_config.NumberColumn(format="%.4f")
                                    for k in table})
    else:
        st.markdown(f"**Results, {labels[day_choice]}**")
        st.dataframe(
            format_results(results_by_day[day_choice]), hide_index=True, width="stretch",
            column_config={
                "Responders, median %": st.column_config.NumberColumn(format="%.2f"),
                "Non-responders, median %": st.column_config.NumberColumn(format="%.2f"),
                "U": st.column_config.NumberColumn(format="%.0f"),
                "p-value": st.column_config.NumberColumn(format="%.4f"),
                "Adjusted p": st.column_config.NumberColumn(format="%.4f"),
            },
        )

    with st.expander("Method"):
        st.markdown(
            f"""
- Mann-Whitney U test for each population. The percentages aren't normally distributed.
- Each time point is tested separately, so every patient counts once per test.
- p-values are multiplied by 5 (Bonferroni) since 5 populations are tested. Significant means adjusted p < {alpha}.
- Day 0 is the one that matters for prediction. Days 7 and 14 show changes during treatment.
"""
        )


# ---------- Part 4 ----------
else:
    st.title("Baseline subset")

    samples, by_project, by_response, by_sex = load_subset()
    response_counts = dict(zip(by_response["response"], by_response["n_subjects"]))
    sex_counts = dict(zip(by_sex["sex"], by_sex["n_subjects"]))

    overview = pd.DataFrame([{
        "Samples": len(samples),
        "Responders": response_counts.get("responder", 0),
        "Non-responders": response_counts.get("non-responder", 0),
        "Male": sex_counts.get("male", 0),
        "Female": sex_counts.get("female", 0),
    }])
    st.table(overview, border=True, hide_index=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Samples per project**")
        st.dataframe(by_project, hide_index=True, width="stretch",
                     column_config={"project_id": "Project", "n_samples": "Samples"})
    with col2:
        st.markdown("**Subjects by response**")
        st.dataframe(by_response, hide_index=True, width="stretch",
                     column_config={"response": "Response", "n_subjects": "Subjects"})
    with col3:
        st.markdown("**Subjects by sex**")
        st.dataframe(by_sex, hide_index=True, width="stretch",
                     column_config={"sex": "Sex", "n_subjects": "Subjects"})

    st.markdown("**Samples**")
    st.dataframe(samples, hide_index=True, width="stretch", height=400,
                 column_config={"sample_id": "Sample", "subject_id": "Subject",
                                "project_id": "Project", "response": "Response", "sex": "Sex"})
    st.download_button("Download CSV", samples.to_csv(index=False), "baseline_subset.csv",
                       "text/csv")
