# babylon-data-eng

# **Hospital Data Management Scripts**

This project consists of Python scripts to manage and populate a PostgreSQL database with the HHS dataset and Quality dataset. The database consists of three tables:


1. **`demo`**: Stores hospital information.
2. **`weekly`**: Tracks weekly hospital bed usage statistics.
3. **`quality`**: Captures hospital quality scores.

The scripts handle table creation and data insertion from structured CSV files, ensuring data consistency and proper relationships between the tables.

---

## **Prerequisites**
1. **Python Libraries**:
   - Ensure the following libraries are installed:
     - `pandas`
     - `psycopg`
     - `re`
     - `sys`
     - `datetime`
     - `streamlit`
     - `pydeck`
     - `plotly`
     - `matplotlib`
   - Install these using:
     ```bash
     pip install pandas psycopg re sys datetime streamlit pydeck plotly matplotlib
     ```

2. **Database Credentials File**:
   - Create a file called `credentials.py` in the same directory as the scripts.
   - This file should contain your database credentials:
     ```python
     DB_USER = "your_database_username"
     DB_PASSWORD = "your_database_password"
     ```
   - Replace `your_database_username` and `your_database_password` with the actual PostgreSQL credentials.

3. **Database Setup**:
   - Ensure your PostgreSQL instance is running and accessible.
   - The database should match the schema created by `create_tables.py`.

4. **CSV Files**:
   - Ensure the input CSV files adhere to the required structure and naming conventions for hospital data and quality scores.

---

## **Database Schema**

The PostgreSQL database consists of **three tables**:

### 1. **`demo` Table**
Stores basic information about hospitals.

| Column Name        | Data Type    | Description                         |
|--------------------|--------------|-------------------------------------|
| `id`               | TEXT         | Unique identifier for the hospital. |
| `name`             | TEXT         | Hospital name.                      |
| `state`            | TEXT         | State where the hospital is located.|
| `address`          | TEXT         | Hospital address.                   |
| `zip`              | TEXT         | ZIP code.                           |
| `fips`             | TEXT         | FIPS code for geographic information.|
| `latitude`         | DECIMAL(8,6) | Geographic latitude.                |
| `longitude`        | DECIMAL(9,6) | Geographic longitude.               |
| `type_of_hospital` | TEXT         | Type of the hospital.               |
| `type_of_ownership`| TEXT         | Ownership type.                     |
| `emergency_service`| BOOLEAN      | Whether emergency services are provided.|

### 2. **`weekly` Table**
Stores weekly bed usage statistics for hospitals.

| Column Name            | Data Type    | Description                          |
|------------------------|--------------|--------------------------------------|
| `id`                   | SERIAL       | Primary key for the table.           |
| `hospital_id`          | TEXT         | Foreign key referencing `demo.id`.   |
| `collection_week`      | DATE         | Date of the data collection week.    |
| `adult_beds`           | DECIMAL      | Average number of adult beds.        |
| `adult_bed_occupied`   | DECIMAL      | Average occupied adult beds.         |
| `pediatric_beds`       | DECIMAL      | Average number of pediatric beds.    |
| `pediatric_bed_occupied`| DECIMAL     | Average occupied pediatric beds.     |
| `icu_beds`             | DECIMAL      | Average number of ICU beds.          |
| `icu_bed_occupied`     | DECIMAL      | Average occupied ICU beds.           |
| `beds_covid`           | DECIMAL      | Average beds used by COVID-19 cases. |
| `icu_covid`            | DECIMAL      | Average ICU beds used by COVID-19 cases.|

### 3. **`quality` Table**
Stores hospital quality scores.

| Column Name       | Data Type    | Description                          |
|-------------------|--------------|--------------------------------------|
| `id`              | SERIAL       | Primary key for the table.           |
| `hospital_id`     | TEXT         | Foreign key referencing `demo.id`.   |
| `date`            | DATE         | Date of the quality score record.    |
| `quality_score`   | INTEGER      | Hospital quality score.              |

---

## **Scripts Overview**

### 1. **`create_tables.py`**
This script creates the **three tables**: `demo`, `weekly`, and `quality`. It ensures the database is ready to ingest hospital data by:
- Dropping existing tables if they exist.
- Creating new tables with the appropriate schema and relationships.

Run this script **before** loading any data.

### 2. **`load-hhs.py`**
This script:
- Loads hospital data from an HHS dataset CSV.
- Inserts data into the `demo` and `weekly` tables.
- Handles duplicate entries using the `ON CONFLICT` clause to update existing records.

### 3. **`load-quality.py`**
This script:
- Loads hospital quality score data from a CSV.
- Inserts the data into the `quality` table.
- Updates the `demo` table with hospital details if new hospitals are found.

### **4. Weekly_Report.py**
This script generates an **interactive weekly report** using Streamlit. The report provides detailed visualizations and insights about hospital utilization and COVID-19 impact. Below are the **seven visualizations** included in the report:

1. **Summary of Hospital Records Over Time**:
   - A line chart showing the total number of hospital records loaded for the selected week and previous weeks.
   - Includes a comparison of the selected week's data against the prior week with percentage changes.

2. **Hospital Beds Availability Summary**:
   - A table summarizing the total number of adult and pediatric beds available during the selected week, the number used, and the number occupied by COVID patients.
   - The table also shows comparisons to the 4 most recent weeks.

3. **Fraction of Beds Occupied by Hospital Quality Rating**:
   - A bar chart comparing the fraction of beds in use across hospitals grouped by quality ratings.
   - Fraction is calculated as:
     ```
     Fraction = (Adult Beds Occupied + Pediatric Beds Occupied) / (Total Adult Beds + Total Pediatric Beds)
     ```
   - Useful for analyzing how bed usage varies between high-quality and low-quality hospitals.

4. **Total and COVID-Specific Bed Usage Trends**:
   - A line chart displaying trends over time in the total number of hospital beds used (all cases) and the number used by COVID patients.
   - Provides an overview of hospital utilization trends up to the selected week.

5. **Hospital Utilization by Quality Rating Over Time**:
   - A time-series plot of total hospital utilization categorized by quality ratings.
   - Shows how usage trends vary between high-quality and low-quality hospitals over multiple weeks.

6. **COVID ICU vs Non-ICU Beds by Quality Rating**:
   - A line plot showing the fraction of COVID beds in ICUs compared to non-ICU beds, grouped by quality ratings.
   - Highlights the distribution of critical care resources.

7. **Geographic Visualizations**:
   - **COVID Hospital Beds by State**:
     - A choropleth map displaying the total number of hospital beds occupied by COVID patients, grouped by state.
   - **Emergency Services by Hospital Location**:
     - A map showing hospital locations across states, categorized by the availability of emergency services.

---

## **Usage**

### Step 1: Create Tables
Run `create_tables.py` to set up the database schema:
```bash
python create_tables.py
```

### Step 2: Load HHS dataset 
Run `load-hhs.py` to set up the database schema:
```bash
python load-hhs.py <path_to_hhs_dataset.csv>
```

### Step 3: Load Quality dataset 
Run `load-quality.py` to set up the database schema:
```bash
python load-quality.py <YYYY-MM-DD> <path_to_quality_dataset.csv>
```

### Step 3: Run the Weekly Report**
To generate the interactive report, run the following command:
```bash
streamlit run Weekly_Report.py
```


