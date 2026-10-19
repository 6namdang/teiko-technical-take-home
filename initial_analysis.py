'''
Part 2: relative frequency of each cell population in each sample

one row per (sample, population):
sample, total_count, population, count, percentage
'''
import sqlite3

import pandas as pd

db_name = "teiko.db"
populations = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def get_frequency_table(connection_obj):
    # 1. unpivot the five population columns into one row per (sample, population)
    query = " UNION ALL ".join(
        f"SELECT sample_id AS sample, '{p}' AS population, {p} AS count FROM samples"
        for p in populations
    )
    df = pd.read_sql_query(query, connection_obj)

    # 2. total cells per sample, then each population as a percentage of that total
    df["total_count"] = df.groupby("sample")["count"].transform("sum")
    df["percentage"] = 100 * df["count"] / df["total_count"]

    # 3. keep populations in the csv's column order within each sample
    df["population"] = pd.Categorical(df["population"], categories=populations, ordered=True)
    df = df.sort_values(["sample", "population"]).reset_index(drop=True)
    df["population"] = df["population"].astype(str)

    return df[["sample", "total_count", "population", "count", "percentage"]]


if __name__ == "__main__":
    connection_obj = sqlite3.connect(db_name)
    summary = get_frequency_table(connection_obj)
    connection_obj.close()

    print(summary.to_string(index=False, float_format="%.2f"))
