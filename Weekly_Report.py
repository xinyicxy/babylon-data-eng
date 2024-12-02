"""Script to generate streamlit dashboard"""
import streamlit as st
import pandas as pd
import psycopg
import credentials
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import numpy as np


# Database connection
conn = psycopg.connect(
   host="pinniped.postgres.database.azure.com",
   dbname=credentials.DB_USER,
   user=credentials.DB_USER,
   password=credentials.DB_PASSWORD
)

cur = conn.cursor()

# Streamlit Configurations
st.set_page_config(
    layout="wide",
    page_title="Weekly Report",
)

st.title('Covid Hospital Data Explorer')
st.text('This is a dashboard to explore hospital data in the USA.')

# Obtain the week from dropdown bar
cur.execute("SELECT DISTINCT collection_week FROM weekly;")
results = cur.fetchall()
df = pd.DataFrame(results, columns=[desc[0] for desc in cur.description])
df.collection_week = pd.to_datetime(df.collection_week)
df = df.sort_values(by="collection_week")
# Dropdown to select a specific week
week_options = df['collection_week'].dt.strftime('%Y-%m-%d').tolist()
selected_week = st.selectbox("Select a Week", week_options)
date = datetime.strptime(selected_week, '%Y-%m-%d')


# Plot 2: Table summarizing the number of adult and pediatric beds
# available that week, the number used, and the number used by patients
# with COVID, compared to the 4 most recent weeks.
cur.execute("SELECT collection_week, sum(adult_beds) AS adult_beds, \
            sum(pediatric_beds) AS pediatric_beds, \
            sum(adult_bed_occupied)+sum(pediatric_bed_occupied) AS beds_used, \
            sum(beds_covid)+sum(icu_covid) AS beds_covid \
          FROM weekly \
          WHERE collection_week <= %s \
          GROUP BY collection_week \
          ORDER BY collection_week DESC \
          LIMIT 5;", [date])
results = cur.fetchall()
df1 = pd.DataFrame(results, columns=[desc[0] for desc in cur.description])
df1.index = [f'Week {str(i+1)}' for i in range(df1.shape[0])]
df1.columns = ['Week Collected', 'Adult beds available',
               'Pediatric beds available',
               'Total beds used',
               'COVID patients']


def highlight_first_row(row):
    if row.name == 'Week 1':  # Check if it's the first row
        return ["background-color: yellow"] * len(row)
    else:
        return [""] * len(row)


# Apply the style
styled_df = df1.style.apply(highlight_first_row, axis=1)

st.title("Table of beds availability information in recent weeks")
st.markdown(
    """
    <p style='color:yellow; font-weight:bold;'>
    * The row highlighted in yellow represents the current week.
    </p>
    """,
    unsafe_allow_html=True
)
st.dataframe(styled_df, hide_index=True)


# Plot 1: Summary of how many hospital records were loaded in the week
# selected by the user, and how that compares to previous weeks.
def fetch_weekly_data(conn, selected_week):
    query = """
    WITH weekly_data AS (
        SELECT
            collection_week,
            COUNT(*) AS hospital_records
        FROM weekly
        WHERE collection_week <= %s
        GROUP BY collection_week
    )
    SELECT
        collection_week,
        hospital_records,
        LAG(hospital_records) OVER (ORDER BY collection_week)
            AS prev_week_records,
        hospital_records - LAG(hospital_records) OVER
            (ORDER BY collection_week) AS diff,
        CASE
            WHEN LAG(hospital_records) OVER
                (ORDER BY collection_week) IS NOT NULL
            THEN ((hospital_records - LAG(hospital_records)
                OVER (ORDER BY collection_week)) * 100.0) /
                    LAG(hospital_records) OVER (ORDER BY collection_week)
            ELSE NULL
        END AS percent_change
    FROM weekly_data
    ORDER BY collection_week;
    """
    params = (selected_week,)
    return pd.read_sql_query(query, conn, params=params)


df = fetch_weekly_data(conn, selected_week)

# Create figure
fig = go.Figure()
fig.add_trace(go.Scatter(
   x=df['collection_week'],
   y=df['hospital_records'],
   mode='lines+markers',
   name='Number of Hospital Records',
   line=dict(color='blue')
))
fig.update_layout(
   title='Hospital Records over Past Weeks',
)

# Summary
selected_week_data = df[df['collection_week'] == date.date()]
selected_week_value = selected_week_data['hospital_records'].values[0]
st.subheader(f"Summary of Number of Hospital Records in Week {selected_week}")
st.write((
    f"Number of Hospital Records for the week of {selected_week}: "
    f"{selected_week_value}"
))

# Check if there is a previous week's data to compare
if not selected_week_data['prev_week_records'].isna().values[0]:
    prev_week_value = selected_week_data['prev_week_records'].values[0]
    diff = selected_week_data['diff'].values[0]
    percent_change = selected_week_data['percent_change'].values[0]

    st.write(f"Number of Hospital Records for the previous week: {int(
        prev_week_value)}")
    st.write(f"Difference from previous week: {int(diff)} records")
    st.write(f"Percentage change: {percent_change:.2f}%")
else:
    st.write("No previous week data available for comparison.")

# Create 2 columns in streamlit
left_col, right_col = st.columns(2)

# Render the plot in Streamlit
left_col.write(fig)


# Plot 3: Graph summarizing fraction of beds in use by hospital quality rating
cur.execute("SELECT quality.quality_score, \
                    sum(weekly.adult_bed_occupied)/sum(weekly.adult_beds) \
                        as bed_fraction \
                    FROM weekly INNER JOIN quality ON \
                        weekly.hospital_id = quality.hospital_id \
                WHERE weekly.collection_week = %s \
                    AND weekly.adult_bed_occupied <= weekly.adult_beds \
                    AND quality.date = ( \
                        SELECT MAX(q.date) \
                        FROM quality q \
                        WHERE q.hospital_id = weekly.hospital_id \
                            AND q.date < %s) \
                GROUP BY quality.quality_score;",
            [date, date])

results = cur.fetchall()
df = pd.DataFrame(results, columns=[desc[0] for desc in cur.description])
df.bed_fraction = df.bed_fraction.astype(float)
df.rename(columns={"quality_score": "Hospital Quality Rating",
                   "bed_fraction": "Fraction of Beds Occupied"},
          inplace=True)

fig = px.bar(df, x="Hospital Quality Rating",  y="Fraction of Beds Occupied",
             title='Fraction of Beds Occupied against Hospital Quality Rating')

left_col.write(fig)


# Plot 4: Total number of hospital beds used per week, over all time up to the
# selected week, split into all cases and COVID cases.
cur.execute("SELECT collection_week, sum(adult_beds) as total_beds, \
                    sum(beds_covid) as covid_beds \
                FROM weekly \
                WHERE collection_week <= %s \
                    AND adult_beds is not NULL \
                    AND beds_covid is not null \
                GROUP BY collection_week;",
            [date])
results = cur.fetchall()
df = pd.DataFrame(results, columns=[desc[0] for desc in cur.description])
df.total_beds = df.total_beds.astype(float)
df = df.sort_values(by="collection_week")

# Create figure
fig = go.Figure()
fig.add_trace(go.Scatter(x=df['collection_week'],
                         y=df['total_beds'],
                         mode='lines+markers',
                         name='Total Patients',
                         line=dict(color='blue')))

# Add the second trace for covid_patients on the secondary y-axis
fig.add_scatter(x=df['collection_week'],
                y=df['covid_beds'],
                mode='lines+markers',
                name='Covid Patients',
                line=dict(color='red'),
                yaxis="y2")

# Update the layout to add the secondary y-axis
fig.update_layout(
    title='Total Patients vs. Covid Patients over Time',
    xaxis=dict(title='Week'),
    yaxis=dict(title='Patients',
               range=[df.total_beds.min()-5000, df.total_beds.max()+5000],),
    yaxis2=dict(
        title='Covid Patients',
        overlaying='y',
        side='right',
        range=[df.covid_beds.min()-1000, df.covid_beds.max()+500],
    ),
)

# Show the figure
right_col.write(fig)


# Plot 5: Plot of covid icu vs non icu by quality over time
@st.cache_data
def load_data(date):
    cur.execute("WITH latest_quality AS ( \
                        SELECT \
                            B.hospital_id, \
                            B.quality_score, \
                            B.date, \
                            ROW_NUMBER() OVER (PARTITION BY B.hospital_id \
                                ORDER BY B.date DESC) AS rn \
                        FROM quality B \
                        WHERE B.date <= %s \
                    ) \
                    SELECT \
                        A.collection_week, \
                        LQ.quality_score, \
                        SUM(A.beds_covid) AS beds_covid, \
                        SUM(A.icu_covid) AS icu_covid, \
                        SUM(A.icu_covid)/SUM(A.beds_covid) AS icu_fraction \
                    FROM weekly A \
                    JOIN latest_quality LQ \
                    ON A.hospital_id = LQ.hospital_id AND LQ.rn = 1 \
                    WHERE A.collection_week <= %s \
                    GROUP BY LQ.quality_score, A.collection_week \
                    ORDER BY A.collection_week, LQ.quality_score;",
                [date, date])

    results = cur.fetchall()
    df2 = pd.DataFrame(results, columns=[desc[0] for desc in cur.description])
    df2 = df2.dropna()
    df2["collection_week"] = pd.to_datetime(df2["collection_week"])
    return df2


# Load data with caching
df2 = load_data(date)

# Streamlit title
st.subheader("COVID Beds Trends by Quality Rating")

# Dropdown for multiple selection
quality_options = df2["quality_score"].unique()
quality_options = np.append(quality_options, "Total")
selected_qualities = st.multiselect("Select Quality Scores to Display:",
                                    quality_options, default=quality_options)

# Determine if "Total" is included and remove it
if "Total" in selected_qualities:
    include_total = True
    selected_qualities.remove("Total")
else:
    include_total = False

selected_qualities = [int(item) for item in selected_qualities]

# Filter the DataFrame based on selection
filtered_df = df2[df2["quality_score"].isin(selected_qualities)]
grouped = filtered_df.groupby("quality_score")
unique_dates = sorted(filtered_df["collection_week"].unique())

# Calculate the total
total_beds_covid = (
    filtered_df.groupby("collection_week")["beds_covid"]
    .sum()
    .reset_index()
    .rename(columns={"beds_covid": "total"})
)
total_icu_covid = (
    filtered_df.groupby("collection_week")["icu_covid"]
    .sum()
    .reset_index()
    .rename(columns={"icu_covid": "total"})
)

col1, col2, col3 = st.columns(3)

# Leftmost Listing for beds_covid
fig1 = px.line(
    filtered_df,
    x="collection_week",
    y="beds_covid",
    color="quality_score",
    markers=True,
    title="COVID beds by Quality Rating over Time",
    labels={"collection_week": "Collection Week",
            "beds_covid": "COVID beds",
            "quality_score": "Quality Score"},
)
# Add the total line to the plot
if include_total:
    fig1.add_trace(
        go.Scatter(
            x=total_beds_covid["collection_week"],
            y=total_beds_covid["total"],
            mode="lines+markers",
            name="Total",
            line=dict(color="grey", dash="dash"),
        )
    )

# Move the legend to the bottom
fig1.update_layout(
    xaxis=dict(
        tickmode="array",
        tickvals=unique_dates,
        ticktext=[date.strftime("%Y-%m-%d") for date in unique_dates],
    ),
    legend=dict(
        orientation="h",  # Horizontal legend
        y=-0.2,  # Move the legend below the plot
        x=0.5,  # Center the legend
        xanchor="center",  # Horizontal alignment
        yanchor="top",  # Vertical alignment
    )
)

fig1.update_traces(hovertemplate="<b>%{y}</b>")
col1.plotly_chart(fig1)

# Center Listing for icu_covid
fig1 = px.line(
    filtered_df,
    x="collection_week",
    y="icu_covid",
    color="quality_score",
    markers=True,
    title="COVID ICU beds by Quality Rating Over Time",
    labels={"collection_week": "Collection Week",
            "icu_covid": "COVID ICU beds",
            "quality_score": "Quality Score"},
)
if include_total:
    fig1.add_trace(
        go.Scatter(
            x=total_icu_covid["collection_week"],
            y=total_icu_covid["total"],
            mode="lines+markers",
            name="Total",
            line=dict(color="grey", dash="dash"),
        )
    )

# Move the legend to the bottom
fig1.update_layout(
    xaxis=dict(
        tickmode="array",
        tickvals=unique_dates,
        ticktext=[date.strftime("%Y-%m-%d") for date in unique_dates],
    ),
    legend=dict(
        orientation="h",  # Horizontal legend
        y=-0.2,  # Move the legend below the plot
        x=0.5,  # Center the legend
        xanchor="center",  # Horizontal alignment
        yanchor="top",  # Vertical alignment
    )
)

fig1.update_traces(hovertemplate="<b>%{y}</b>")
col2.plotly_chart(fig1)

# Rightmost column: display the fraction of the icu_covid over the sum
fig2 = px.line(
    filtered_df,
    x="collection_week",
    y="icu_fraction",
    color="quality_score",
    markers=True,
    title="Fraction of COVID Patients in the ICU",
    labels={"collection_week": "Collection Week",
            "icu_fraction": "COVID ICU patients/ All COVID patients",
            "quality_score": "Quality Score"},
)
# Move the legend to the bottom
fig2.update_layout(
    xaxis=dict(
        tickmode="array",
        tickvals=unique_dates,
        ticktext=[date.strftime("%Y-%m-%d") for date in unique_dates],
    ),
    legend=dict(
        orientation="h",  # Horizontal legend
        y=-0.2,  # Move the legend below the plot
        x=0.5,  # Center the legend
        xanchor="center",  # Horizontal alignment
        yanchor="top",  # Vertical alignment
    )
)

fig2.update_traces(hovertemplate="<b>%{y:.2f}</b>")
col3.plotly_chart(fig2)


# Plot 6: Map of covid hospital beds by state
cur.execute("SELECT demo.state, sum(weekly.beds_covid) as covid_beds \
FROM weekly INNER JOIN demo ON weekly.hospital_id = demo.id \
WHERE weekly.collection_week = %s \
GROUP BY demo.state", [date])
results = cur.fetchall()
df = pd.DataFrame(results, columns=[desc[0] for desc in cur.description])
df.covid_beds = df.covid_beds.astype(float)

# Figure plotting for plot 6
fig = go.Figure(data=go.Choropleth(
    locations=df['state'],  # Spatial coordinates
    z=df['covid_beds'].astype(float),  # Data to be color-coded
    locationmode='USA-states',
    colorscale='matter',
    colorbar_title="Covid cases",
))

fig.update_layout(
    title_text='Covid Cases in US States',
    geo_scope='usa',  # limit map scope to USA
)

right_col.write(fig)
