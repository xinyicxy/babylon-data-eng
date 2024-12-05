"""Emergency services page on Streamlit Dashboard."""
import os
import sys
import inspect
import json
import streamlit as st
import pydeck as pdk
import psycopg
import credentials


# Set up parent directory for module imports
currentdir = os.path.dirname(
   os.path.abspath(
       inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

# Streamlit Configurations
st.set_page_config(
   page_title="Hospital Emergency Services",
   layout="wide",
)

# Database connection
conn = psycopg.connect(
   host="pinniped.postgres.database.azure.com",
   dbname=credentials.DB_USER,
   user=credentials.DB_USER,
   password=credentials.DB_PASSWORD,
)
cur = conn.cursor()

# Map of Emergency Services
st.title("Map of Emergency Services by Hospital Location")

# Create two columns: one for filters and one for the map
filter_col, map_col = st.columns([1, 3])

# Filters Section (in the first column)
with filter_col:
    st.header("Filters")

    # State Filter
    cur.execute(
        "SELECT DISTINCT state FROM demo "
        "WHERE latitude IS NOT NULL AND longitude IS NOT NULL;"
    )
    state_options = ["All States"] + [row[0] for row in cur.fetchall()]
    selected_state = st.selectbox(
        "Select State", state_options, key="state_filter"
    )

    # ZIP Code Filter
    cur.execute(
        "SELECT DISTINCT zip FROM demo "
        "WHERE latitude IS NOT NULL AND longitude IS NOT NULL;"
    )
    zip_options = ["All ZIP Codes"] + [row[0] for row in cur.fetchall()]
    selected_zip = st.selectbox(
        "Select ZIP Code", zip_options, key="zip_filter"
    )

    # Emergency Service Filter
    emergency_only = st.checkbox(
        "Show only hospitals with emergency services",
        value=False,
        key="emergency_filter",
    )

# Build SQL Query Dynamically with Parameters
filter_conditions = []
params = []

if selected_state != "All States":
    filter_conditions.append("state = %s")
    params.append(selected_state)
if selected_zip != "All ZIP Codes":
    filter_conditions.append("zip = %s")
    params.append(selected_zip)
if emergency_only:
    filter_conditions.append("emergency_service = TRUE")

where_clause = " AND ".join(filter_conditions)
if where_clause:
    where_clause = (
        "WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND " +
        where_clause
    )
else:
    where_clause = (
        "WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
    )

# SQL Query with All Computation
query = f"""
WITH filtered_data AS (
   SELECT
       id,
       name,
       state,
       zip,
       CAST(latitude AS DOUBLE PRECISION) AS latitude,
       CAST(longitude AS DOUBLE PRECISION) AS longitude,
       CASE
           WHEN emergency_service = TRUE THEN 'Yes'
           ELSE 'No'
       END AS emergency_service_text,
       CASE
           WHEN emergency_service = TRUE THEN '[0, 255, 0]'  -- Green for Yes
           ELSE '[255, 0, 0]'  -- Red for No
       END AS color
   FROM demo
   {where_clause}
),
computed_averages AS (
   SELECT
       CAST(AVG(latitude) AS DOUBLE PRECISION) AS latitude_avg,
       CAST(AVG(longitude) AS DOUBLE PRECISION) AS longitude_avg
   FROM filtered_data
)
SELECT
   fd.id,
   fd.name,
   fd.state,
   fd.zip,
   fd.latitude,
   fd.longitude,
   fd.emergency_service_text,
   fd.color,
   ca.latitude_avg,
   ca.longitude_avg
FROM filtered_data fd
CROSS JOIN computed_averages ca;
"""

# Execute the SQL Query with parameters
cur.execute(query, params)
columns = [desc[0] for desc in cur.description]
results = cur.fetchall()

# Visualization Section (in the second column)
with map_col:
    if results:
        # Convert results to a list of dictionaries
        data = [dict(zip(columns, row)) for row in results]

        # Ensure all numeric fields are of type float and parse color
        for row in data:
            row['latitude'] = float(row['latitude'])
            row['longitude'] = float(row['longitude'])
            row['latitude_avg'] = float(row['latitude_avg'])
            row['longitude_avg'] = float(row['longitude_avg'])
            row['color'] = json.loads(row['color'])

        # Use SQL-computed averages
        latitude_avg = data[0]['latitude_avg']
        longitude_avg = data[0]['longitude_avg']

        # Create PyDeck view
        view_state = pdk.ViewState(
            latitude=latitude_avg,
            longitude=longitude_avg,
            zoom=4,
            pitch=0,
        )

        # Create PyDeck layer
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=data,
            get_position=["longitude", "latitude"],
            get_color="color",
            get_radius=10000,
            pickable=True,
        )

        # Configure PyDeck deck with tooltip
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={
                "html": "<b>Hospital:</b> {name}<br>"
                        "<b>State:</b> {state}<br>"
                        "<b>ZIP:</b> {zip}<br>"
                        "<b>Emergency Service:</b> {emergency_service_text}",
                "style": {"color": "white", "backgroundColor": "black"},
            },
        )

        # Render PyDeck map
        st.pydeck_chart(deck)

        # # Summary of Hospitals
        # st.subheader("Summary of Hospitals")
        # st.write(f"Total hospitals displayed: {len(data)}")
        # for row in data:
        #     st.write(
        #         f"Hospital: {row['name']}, State: {row['state']}, "
        #         f"ZIP: {row['zip']}, "
        #         f"Emergency Service: {row['emergency_service_text']}"
        #     )
    else:
        st.warning("No hospitals found matching the selected criteria.")
