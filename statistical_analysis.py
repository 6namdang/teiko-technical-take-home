'''
Part 3: responders vs non-responders

melanoma patients on miraclib, PBMC samples only
compare the relative frequency of each cell population between
response = yes and response = no

- boxplot for each population (saved to boxplot_responders.png)
- Mann-Whitney U test per population, Bonferroni corrected

the main test uses day 0 (baseline) samples only:
- to predict response we can only use what we know before treatment
- each subject has one sample per time point, so every subject counts once
day 7 and day 14 are tested the same way to see what changes during treatment
'''
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import mannwhitneyu

db_name = "teiko.db"
populations = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
days = [0, 7, 14]
alpha = 0.05


def get_cohort(connection_obj):
    # melanoma + miraclib + PBMC samples, one row per (sample, population)
    query = " UNION ALL ".join(
        f"""SELECT s.sample_id AS sample, s.time_from_treatment_start AS day,
                   sub.response, '{p}' AS population, s.{p} AS count
            FROM samples s
            JOIN subjects sub ON s.subject_id = sub.subject_id
            WHERE sub.condition = 'melanoma'
              AND sub.treatment = 'miraclib'
              AND s.sample_type = 'PBMC'
              AND sub.response IN ('yes', 'no')"""
        for p in populations
    )
    df = pd.read_sql_query(query, connection_obj)

    # relative frequency of each population in its sample (same as part 2)
    df["total_count"] = df.groupby("sample")["count"].transform("sum")
    df["percentage"] = 100 * df["count"] / df["total_count"]
    return df


def plot_boxplot(df, title):
    fig, axes = plt.subplots(1, len(populations), figsize=(18, 5))
    for ax, p in zip(axes, populations):
        yes = df.loc[(df["population"] == p) & (df["response"] == "yes"), "percentage"]
        no = df.loc[(df["population"] == p) & (df["response"] == "no"), "percentage"]
        box = ax.boxplot([yes, no], patch_artist=True, widths=0.6,
                         medianprops={"color": "black"})
        for patch, color in zip(box["boxes"], ["#4C78A8", "#B0B7C3"]):
            patch.set_facecolor(color)
        ax.set_xticks([1, 2], ["responders", "non-responders"])
        ax.set_title(p)
        ax.set_ylabel("relative frequency (%)")
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(title)
    fig.tight_layout()
    return fig


def compare_responders(df):
    # Mann-Whitney U per population: non-parametric, so we don't have to assume
    # the percentages are normal. 5 tests at once, so multiply p-values by 5
    # (Bonferroni) to avoid false positives
    results = []
    for p in populations:
        yes = df.loc[(df["population"] == p) & (df["response"] == "yes"), "percentage"]
        no = df.loc[(df["population"] == p) & (df["response"] == "no"), "percentage"]
        stat, p_value = mannwhitneyu(yes, no, alternative="two-sided")
        p_adj = min(p_value * len(populations), 1.0)
        results.append({
            "population": p,
            "responder_median": yes.median(),
            "non_responder_median": no.median(),
            "U": stat,
            "p_value": p_value,
            "p_adj": p_adj,
            "significant": p_adj < alpha,
        })
    return pd.DataFrame(results)


if __name__ == "__main__":
    connection_obj = sqlite3.connect(db_name)
    df = get_cohort(connection_obj)
    connection_obj.close()

    n_yes = df.loc[df["response"] == "yes", "sample"].nunique()
    n_no = df.loc[df["response"] == "no", "sample"].nunique()
    print(f"samples: {n_yes} responders, {n_no} non-responders\n")

    # boxplot, one panel per population (all time points together)
    fig = plot_boxplot(df, "Melanoma, miraclib, PBMC: responders vs non-responders")
    fig.savefig("boxplot_responders.png", dpi=150)
    print("boxplot saved to boxplot_responders.png\n")

    # tests, separately for each time point
    significant_by_day = {}
    for day in days:
        day_df = df[df["day"] == day]
        results = compare_responders(day_df)

        n_yes = day_df.loc[day_df["response"] == "yes", "sample"].nunique()
        n_no = day_df.loc[day_df["response"] == "no", "sample"].nunique()
        label = "baseline, main test" if day == 0 else "during treatment"
        print(f"day {day} ({label}): {n_yes} responders, {n_no} non-responders")
        print(results.to_string(index=False, float_format="%.4g"))
        print()

        significant_by_day[day] = results.loc[results["significant"], "population"].tolist()

    # conclusion
    if significant_by_day[0]:
        print(f"at baseline, these populations differ between responders and non-responders "
              f"(adjusted p < {alpha}): {', '.join(significant_by_day[0])}")
    else:
        print(f"at baseline, no population differs between responders and non-responders "
              f"(adjusted p < {alpha}), so none of them predicts response to miraclib")

    for day in [7, 14]:
        if significant_by_day[day]:
            print(f"day {day}: significant difference in {', '.join(significant_by_day[day])}")
        else:
            print(f"day {day}: no significant difference after correction")
