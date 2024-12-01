"""Emergency services page on Streamlit Dashboard"""
import streamlit as st
import pydeck as pdk
import pandas as pd
import psycopg
import os
import sys
import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import credentials


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
   password=credentials.DB_PASSWORD
)
cur = conn.cursor()

# Plot 7: Map of emergency services by hospital location/ state
# Function to fetch demo data
def fetch_demo_data(conn):
   query = """
   SELECT
       id,
       name,
       state,
       zip,
       latitude,
       longitude,
       emergency_service
   FROM demo
   WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
   """
   return pd.read_sql_query(query, conn)


# Streamlit app
st.title("Map of Emergency Services by Hospital Location")
st.text('This page explores the emergency services available in hospitals\
 in the US')


df = fetch_demo_data(conn)



# Map emergency_service to readable values and color codes
df['emergency_service_text'] = df['emergency_service'].map({True: "Yes", False: "No"})
df['color'] = df['emergency_service'].map({True: [0, 255, 0], False: [255, 0, 0]})  # Green for Yes, Red for No


# Sidebar Filters
st.sidebar.header("Filters")


# State Filter
state_options = ["All States"] + sorted(df['state'].unique().tolist())
selected_state = st.sidebar.selectbox("Select State", state_options)


if selected_state != "All States":
   df = df[df['state'] == selected_state]


# ZIP Code Filter
zip_options = ["All ZIP Codes"] + sorted(df['zip'].unique().tolist())
selected_zip = st.sidebar.selectbox("Select ZIP Code", zip_options)


if selected_zip != "All ZIP Codes":
   df = df[df['zip'] == selected_zip]


# Emergency Service Filter
emergency_only = st.sidebar.checkbox("Show only hospitals with emergency services", value=False)


if emergency_only:
   df = df[df['emergency_service_text'] == "Yes"]


# Map visualization with PyDeck
st.subheader("Hospital Locations Map")
view_state = pdk.ViewState(
   latitude=df['latitude'].mean(),
   longitude=df['longitude'].mean(),
   zoom=4,
   pitch=0
)


# Define layers for PyDeck
layer = pdk.Layer(
   "ScatterplotLayer",
   data=df,
   get_position=["longitude", "latitude"],
   get_color="color",
   get_radius=10000, 
   pickable=True
)


# Configure the PyDeck map with tooltip including ZIP code
deck = pdk.Deck(
   layers=[layer],
   initial_view_state=view_state,
   tooltip={
       "html": "<b>Hospital:</b> {name}<br>"
               "<b>State:</b> {state}<br>"
               "<b>ZIP:</b> {zip}<br>"
               "<b>Emergency Service:</b> {emergency_service_text}",
       "style": {"color": "white", "backgroundColor": "black"},
   }
)


# Render the map in Streamlit
st.pydeck_chart(deck)


# Summary of Hospitals
st.subheader("Summary of Hospitals")
st.write(f"Total hospitals displayed: {len(df)}")
st.write(df[['name', 'state', 'zip', 'emergency_service_text']])



conn.close()