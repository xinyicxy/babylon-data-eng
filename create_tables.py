"""Scripts to create tables"""
import psycopg
import credentials


conn = psycopg.connect(
   host="pinniped.postgres.database.azure.com",
   dbname=credentials.DB_USER,
   user=credentials.DB_USER,
   password=credentials.DB_PASSWORD
)


cur_demo = conn.cursor()
cur_demo.execute("DROP TABLE IF EXISTS quality;")
cur_demo.execute("DROP TABLE IF EXISTS weekly;")
cur_demo.execute("DROP TABLE IF EXISTS demo;")
create_demo = """
CREATE TABLE demo (
    id TEXT NOT NULL PRIMARY KEY,
    name TEXT,
    state TEXT,
    address TEXT,
    zip TEXT,
    fips TEXT,
    latitude DECIMAL(8, 6),
    longitude DECIMAL(9, 6),
    type_of_hospital TEXT,
    type_of_ownership TEXT,
    emergency_service BOOLEAN
);"""
cur_demo.execute(create_demo)


cur_quality = conn.cursor()
cur_quality.execute("DROP TABLE IF EXISTS quality;")
create_quality = """
CREATE TABLE quality (
       id SERIAL PRIMARY KEY,
       hospital_id TEXT NOT NULL REFERENCES demo (id),
       date DATE NOT NULL,
       quality_score INTEGER NOT NULL,
       unique(hospital_id, date)
);
"""
cur_quality.execute(create_quality)


cur_weekly = conn.cursor()
cur_weekly.execute("DROP TABLE IF EXISTS weekly;")
create_weekly = """
CREATE TABLE weekly (
    id SERIAL PRIMARY KEY,
    hospital_id TEXT NOT NULL REFERENCES demo (id),
    collection_week DATE NOT NULL,
    adult_beds DECIMAL CHECK (adult_beds >= 0),
    adult_bed_occupied DECIMAL CHECK (adult_bed_occupied >= 0
        AND adult_bed_occupied <= adult_beds),
    pediatric_beds DECIMAL CHECK (pediatric_beds >= 0),
    pediatric_bed_occupied DECIMAL CHECK (pediatric_bed_occupied >= 0
        AND pediatric_bed_occupied <= pediatric_beds),
    icu_beds DECIMAL CHECK (icu_beds >= 0),
    icu_bed_occupied DECIMAL CHECK (icu_bed_occupied >= 0
        AND icu_bed_occupied <= icu_beds),
    beds_covid DECIMAL CHECK (beds_covid >= 0
        AND beds_covid <= (adult_bed_occupied + pediatric_bed_occupied)),
    icu_covid DECIMAL CHECK (icu_covid >= 0
        AND icu_covid <= icu_bed_occupied),
    unique(hospital_id, collection_week)
);"""
cur_weekly.execute(create_weekly)

conn.commit()
conn.close()
