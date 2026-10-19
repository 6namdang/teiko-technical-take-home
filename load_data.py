'''
projects table
project_id

subjects table
subject_id
project_id FK --> projects table
condition
age
sex
treatment
response

samples table
sample_id
subject_id FK --> subjects table
sample_type
time_from_treatment_start
b_cell
cd8_t_cell
cd4_t_cell
nk_cell
monocyte
'''
import csv
import sqlite3

db_name = "teiko.db"
#connect to a db, or create one if not exist
connection_obj = sqlite3.connect(db_name)
connection_obj.execute("PRAGMA foreign_keys = ON")
cursor = connection_obj.cursor()

# 1. create the tables
query = """

    CREATE TABLE projects (
        project_id TEXT PRIMARY KEY
    );

    CREATE TABLE subjects (
        subject_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(project_id),
        condition TEXT NOT NULL,
        age INTEGER NOT NULL,
        sex TEXT NOT NULL,
        treatment TEXT NOT NULL,
        response TEXT
    );

    CREATE TABLE samples (
        sample_id TEXT PRIMARY KEY,
        subject_id TEXT NOT NULL REFERENCES subjects(subject_id),
        sample_type TEXT NOT NULL,
        time_from_treatment_start INTEGER NOT NULL,
        b_cell INTEGER NOT NULL,
        cd8_t_cell INTEGER NOT NULL,
        cd4_t_cell INTEGER NOT NULL,
        nk_cell INTEGER NOT NULL,
        monocyte INTEGER NOT NULL
    );
"""
cursor.executescript(query)
print("Tables are Ready")

# 2. seed the tables from the csv
with open("cell-count.csv", newline="") as f:
    for row in csv.DictReader(f):
        cursor.execute(
            "INSERT OR IGNORE INTO projects VALUES (?)",
            (row["project"],),
        )
        cursor.execute(
            "INSERT OR IGNORE INTO subjects VALUES (?, ?, ?, ?, ?, ?, ?)",
            (row["subject"], row["project"], row["condition"], int(row["age"]),
             row["sex"], row["treatment"], row["response"] or None),
        )
        cursor.execute(
            "INSERT INTO samples VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (row["sample"], row["subject"], row["sample_type"],
             int(row["time_from_treatment_start"]),
             int(row["b_cell"]), int(row["cd8_t_cell"]), int(row["cd4_t_cell"]),
             int(row["nk_cell"]), int(row["monocyte"])),
        )

connection_obj.commit()
print("Data is Loaded")
connection_obj.close()
