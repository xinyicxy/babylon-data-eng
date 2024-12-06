"""Upload the hospital quality dataset"""
import sys
import pandas as pd
import psycopg
import credentials
from datetime import datetime

# Getting values from command line argument
if len(sys.argv) < 3:
    raise ValueError("Provide the date of data and pathname of file to read")

date = sys.argv[1]
filepath = sys.argv[2]

# Reading dataframe
df = pd.read_csv(filepath)
names_dict = {'Facility ID': "hospital_id",
              'Hospital Type': "type_of_hospital",
              'Hospital Ownership': "type_of_ownership",
              'Emergency Services': "emergency_service",
              'Hospital overall rating': "quality_score"}
df.rename(columns=names_dict, inplace=True)

# Cleaning data for Unique hospital id
df = df[df['hospital_id'].str.match(r'^\d{6}$')]
df = df.dropna(subset=['hospital_id'])
df = df.drop_duplicates(subset=['hospital_id'])

# Convert float("NaN") type to python None type
df = df.replace({float("NaN"): None})

# Cleaning data to add to quality table
df_quality = df[["hospital_id", "quality_score"]]
df_quality = df_quality[df_quality.quality_score != 'Not Available']
df_quality.quality_score = df_quality.quality_score.astype(int)

date = datetime.strptime(date, "%Y-%m-%d").date()
df_quality["date"] = date

list_quality = [(row.hospital_id, row.date,  row.quality_score) for row in
                df_quality.itertuples(index=False)]

# Opening connection to database
conn = psycopg.connect(
   host="pinniped.postgres.database.azure.com",
   dbname=credentials.DB_USER,
   user=credentials.DB_USER,
   password=credentials.DB_PASSWORD
)

cur = conn.cursor()

# Writing into "demo" database
try:

    cur.executemany("""
       INSERT INTO demo (id, type_of_hospital, type_of_ownership, \
                    emergency_service)
       VALUES (%s, %s, %s, %s)
       ON CONFLICT (id)
       DO UPDATE SET
           type_of_hospital = EXCLUDED.type_of_hospital,
           type_of_ownership = EXCLUDED.type_of_ownership,
           emergency_service = EXCLUDED.emergency_service;
       """, [
           (row.hospital_id, row.type_of_hospital, row.type_of_ownership,
            row.emergency_service)
           for row in df.itertuples(index=False)
       ])

    # Print the result
    print(f"{cur.rowcount} rows have been inserted or updated" +
          " in the database \"demo\".")

except Exception as err:
    # Stop transaction in case of error, prints current rowcount
    print(err, " at row ", cur.rowcount)
else:
    conn.commit()


# Writing into the "quality" database
try:
    cur.executemany("""INSERT INTO quality (hospital_id, date, quality_score)
                    VALUES (%s, %s, cast(%s as integer))
                    ON CONFLICT (hospital_id, date) DO NOTHING;""",
                    list_quality)
    rowcount = cur.rowcount
    print(rowcount, " rows have been inserted into database \"quality\".")

except Exception as err:
    # Stops transaction in case of error, prints current rowcount
    rowcount = cur.rowcount
    print(err, " at row ", rowcount)
else:
    conn.commit()


conn.close()
