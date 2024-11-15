"""Import HHS dataset"""
import sys
import pandas as pd
import psycopg
import re
import credentials

# Load hhs dataset
file_path = str(sys.argv[1])
df = pd.read_csv(file_path)

# Unique hospital id
df = df[df['hospital_pk'].str.match(r'^\d{6}$')]
df = df.dropna(subset=['hospital_pk', 'collection_week'])
df = df.drop_duplicates(subset=['hospital_pk'])
# Collection date
df['collection_week'] = pd.to_datetime(df['collection_week'])

# Columns for weekly table
cols = ['all_adult_hospital_beds_7_day_avg',
        'all_adult_hospital_inpatient_bed_occupied_7_day_avg',
        'all_pediatric_inpatient_beds_7_day_avg',
        'all_pediatric_inpatient_bed_occupied_7_day_avg',
        'total_icu_beds_7_day_avg',
        'icu_beds_used_7_day_avg',
        'inpatient_beds_used_covid_7_day_avg',
        'staffed_icu_adult_patients_confirmed_covid_7_day_avg']
df[cols] = df[cols].where(df[cols] >= 0, None)

# Weekly table copy
df1 = df[['hospital_pk', 'collection_week'] + cols].copy()

# Columns for demo table
cols_demo = [
        'hospital_name',
        'address',
        'zip',
        'fips_code',
        'state',
        'geocoded_hospital_address'
]

# Demo table copy
df2 = df[['hospital_pk'] + cols_demo].copy()


def extract_lat_long(geo_address):
    """Extracting Latitude and Longitude information
    Parameters
    ----------
    geo_address: tuple of form (long, lat)

    Returns
    -------
    pd.Series([float, float])
    """
    if geo_address == "NA":
        return pd.Series([None, None])
    elif pd.notna(geo_address): 
        match = re.match(r'POINT \(([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)\)',
                         geo_address)
        if match:
            longitude, latitude = map(float, match.groups())
            return pd.Series([latitude, longitude])
    # Return None if geo_address is NaN or doesn't match the format
    return pd.Series([None, None])


# Apply the function to the geocoded_hospital_address column
df2[['latitude', 'longitude']] = df2['geocoded_hospital_address'].apply(
    extract_lat_long)

# Rename the fips column
df2 = df2.rename(columns={'fips_code': 'fips'})

# Read data into tables
conn = psycopg.connect(
   host="pinniped.postgres.database.azure.com",
   dbname=credentials.DB_USER,
   user=credentials.DB_USER,
   password=credentials.DB_PASSWORD
)

# Insert into demo table
cur_demo = conn.cursor()
# Covert the dataset to list of tuples for batch insert
demo = [(row.hospital_pk, row.hospital_name, row.state,
         row.address, row.zip,
         row.fips, row.latitude, row.longitude,) for row in df2.itertuples(
             index=False)]
try:
    # Update the demographics information when we see the same hospital id
    cur_demo.executemany(
        "INSERT INTO demo"
        "(id, name, state, address, zip, fips, latitude, longitude)"
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        "ON CONFLICT (id) DO UPDATE SET "
        "name = EXCLUDED.name,"
        "state = EXCLUDED.state,"
        "address = EXCLUDED.address,"
        "zip = EXCLUDED.zip,"
        "fips = EXCLUDED.fips,"
        "latitude = EXCLUDED.latitude,"
        "longitude = EXCLUDED.longitude;",
        demo
    )
    # Print the number of rows inserted
    rowcount = cur_demo.rowcount
    print(rowcount, " rows have been inserted into database quality")

except Exception as err:
    rowcount = cur_demo.rowcount
    print(err, " at row ", rowcount)

# Insert into weekly table
cur_weekly = conn.cursor()
weekly = [(row.hospital_pk,
           row.collection_week,
           row.all_adult_hospital_beds_7_day_avg,
           row.all_adult_hospital_inpatient_bed_occupied_7_day_avg,
           row.all_pediatric_inpatient_beds_7_day_avg,
           row.all_pediatric_inpatient_bed_occupied_7_day_avg,
           row.total_icu_beds_7_day_avg,
           row.icu_beds_used_7_day_avg,
           row.inpatient_beds_used_covid_7_day_avg,
           row.staffed_icu_adult_patients_confirmed_covid_7_day_avg
           ) for row in df1.itertuples(index=False)]

try:
    cur_weekly.executemany(
        "INSERT INTO weekly"
        "(hospital_id, collection_week, adult_beds, adult_bed_occupied, \
            pediatric_beds, pediatric_bed_occupied, icu_beds, icu_bed_occupied, \
                beds_covid, icu_covid)"
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        weekly
    )
    rowcount = cur_weekly.rowcount
    print(rowcount, " rows have been inserted into database quality")

except Exception as err:
    rowcount = cur_weekly.rowcount
    print(err, " at row ", rowcount)

conn.commit()
conn.close()
