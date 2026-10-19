'''
Part 4: data subset analysis

melanoma PBMC samples at baseline (time_from_treatment_start = 0)
from patients treated with miraclib

then among these samples:
- how many samples from each project
- how many subjects were responders / non-responders
- how many subjects were males / females
'''
import sqlite3

import pandas as pd

db_name = "teiko.db"

# the subset we are looking at, reused in every query below
subset = """
    SELECT s.sample_id, s.subject_id, sub.project_id, sub.response, sub.sex
    FROM samples s
    JOIN subjects sub ON s.subject_id = sub.subject_id
    WHERE sub.condition = 'melanoma'
      AND sub.treatment = 'miraclib'
      AND s.sample_type = 'PBMC'
      AND s.time_from_treatment_start = 0
"""


def get_subset_samples(connection_obj):
    return pd.read_sql_query(subset + " ORDER BY s.sample_id", connection_obj)


def count_by_project(connection_obj):
    # every project is listed, even the ones with 0 samples
    return pd.read_sql_query(f"""
        SELECT p.project_id, COUNT(x.sample_id) AS n_samples
        FROM projects p
        LEFT JOIN ({subset}) x ON x.project_id = p.project_id
        GROUP BY p.project_id
        ORDER BY p.project_id
    """, connection_obj)


def count_by_response(connection_obj):
    # count subjects, not samples
    df = pd.read_sql_query(f"""
        SELECT response, COUNT(DISTINCT subject_id) AS n_subjects
        FROM ({subset})
        GROUP BY response
        ORDER BY response
    """, connection_obj)
    # any other value is shown as it is, and missing response as "missing"
    df["response"] = df["response"].map(
        lambda r: {"yes": "responder", "no": "non-responder"}.get(r, r) if pd.notna(r) else "missing"
    )
    return df


def count_by_sex(connection_obj):
    df = pd.read_sql_query(f"""
        SELECT sex, COUNT(DISTINCT subject_id) AS n_subjects
        FROM ({subset})
        GROUP BY sex
        ORDER BY sex
    """, connection_obj)
    # any other value is shown as it is
    df["sex"] = df["sex"].map(lambda s: {"M": "male", "F": "female"}.get(s, s))
    return df


if __name__ == "__main__":
    connection_obj = sqlite3.connect(db_name)

    samples = get_subset_samples(connection_obj)
    print(f"melanoma, miraclib, PBMC, baseline samples: {len(samples)}")
    print(samples.to_string(index=False))
    print()

    print("samples per project:")
    print(count_by_project(connection_obj).to_string(index=False))
    print()

    print("subjects by response:")
    print(count_by_response(connection_obj).to_string(index=False))
    print()

    print("subjects by sex:")
    print(count_by_sex(connection_obj).to_string(index=False))

    connection_obj.close()
