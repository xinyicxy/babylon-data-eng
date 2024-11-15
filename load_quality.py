"""Load the hospital quality dataset"""
import sys
import pandas as pd
import psycopg
import credentials
from datetime import datetime

# Reading dataframe
if len(sys.argv) < 3:
    # Getting number of lines from command line argument
    raise ValueError("Provide the date of data and pathname of file to read")

date = sys.argv[1]
filepath = sys.argv[2]
# Read file into a list

df = pd.read_csv(filepath)
names_dict = {'Facility ID': "hospital_id",
              'Hospital Type': "type_of_hospital",
              'Hospital Ownership': "type_of_ownership",
              'Emergency Services': "emergency_service",
              'Hospital overall rating': "quality_score"}
df.rename(columns=names_dict, inplace=True)

# Cleaning data to add to demographics table


# Cleaning data to add to quality table
df_quality = df[["hospital_id", "quality_score"]]
df_quality = df_quality[df_quality.quality_score != 'Not Available']
df_quality.quality_score = df_quality.quality_score.astype(int)

date = datetime.strptime(date, "%Y-%m-%d").date()
df_quality["date"] = date

list_quality = [(row.hospital_id, row.date,  row.quality_score) for row in
                df_quality.itertuples(index=False)]
# list_quality = df_quality.to_list()

# print(list_quality)


# Reading into database
conn = psycopg.connect(
   host="pinniped.postgres.database.azure.com",
   dbname=credentials.DB_USER,
   user=credentials.DB_USER,  
   password=credentials.DB_PASSWORD
)









cur = conn.cursor()
try:
    cur.executemany("INSERT INTO quality (hospital_id, date, quality_score) \
                    VALUES (%s, %s, cast(%s as integer))", list_quality)
    rowcount = cur.rowcount
    print(rowcount, " rows have been inserted into database quality")

except Exception as err:
    rowcount = cur.rowcount
    print(err, " at row ", rowcount)







conn.commit()
conn.close()



