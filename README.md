# Shipping Route Efficiency Analysis
### Dataset: Nassau Candy Distributor

A data analytics project that processes 10,194 shipment records, computes route-level KPIs, and delivers findings through an interactive Streamlit dashboard.

---

## Project Overview
This project analyses shipping route performance for a candy distributor operating 5 factories and delivering to 59 states and provinces across the US and Canada. The goal is to identify the most and least efficient routes, detect geographic bottlenecks, and compare shipping mode performance using a structured analytical pipeline.

---

## Tools and Technologies
- Python 3.8+
- Pandas
- NumPy
- Streamlit
- Plotly
- Pillow

---

## Project Structure

```
Project 1/
    Nassau Candy Distributor.csv
    Nassua Candy Logo.jpg
    Code/
        analysis.py
        dashboard.py
    outputs/
        benchmark_bottom10_routes.csv
        benchmark_top10_routes.csv
        kpi_bottleneck_states.csv
        kpi_factory_performance.csv
        kpi_factory_shipmode_pivot.csv
        kpi_orders_enriched.csv
        kpi_region_performance.csv
        kpi_route_aggregation.csv
        kpi_routes_by_ship_mode.csv
        kpi_ship_mode_performance.csv
        kpi_state_performance.csv
```

---

## How It Works

The project runs in two stages.

**Stage 1 - analysis.py**
Reads the raw CSV, cleans the data, engineers features, computes all KPIs, and saves 11 output CSV files to the outputs/ folder. This script contains all the analytical logic and must be run before the dashboard.

**Stage 2 - dashboard.py**
Loads the pre-computed CSV files and renders them as an interactive web application. No recalculation happens in the dashboard — it only visualises what analysis.py already computed.

---

## Setup and Installation

Install the required libraries:

```
pip install pandas numpy streamlit plotly pillow
```

---

## How to Run

Step 1 - Navigate to the Code folder and run the analysis pipeline:

```
cd Code
python analysis.py
```

This will generate all 11 KPI files inside the outputs/ folder.

Step 2 - Launch the dashboard:

```
streamlit run dashboard.py
```

The browser will open automatically at http://localhost:8501.

To refresh data after updating the source CSV, re-run analysis.py and reload the browser.

---

## Key Findings

- 10,194 orders analysed across 196 unique Factory-to-State routes
- Global average lead time: 178.3 days
- Overall delay rate: 24.7% (threshold: 75th percentile = 179 days)
- Standard Class shipping carries a 38.8% delay rate vs 0% for Same Day and First Class
- 6 geographic bottleneck states identified: Minnesota, Tennessee, New Jersey, Indiana, Oregon, Delaware
- Fastest route: The Other Factory to North Carolina (175.0 days, 0% delay)
- Slowest route: Lot's O' Nuts to Newfoundland and Labrador (182.0 days, 83.3% delay)

---

## Dashboard Tabs

| Tab | Description |
|-----|-------------|
| Route Efficiency Overview | KPI summary cards, Top 10 and Bottom 10 routes, efficiency scatter plot |
| Geographic Map | US choropleth map coloured by lead time, delay rate, or volume |
| Bottleneck Analysis | Quadrant chart identifying high-volume, slow-delivery states |
| Ship Mode Comparison | Box plots, heatmap, and cost-time trade-off table across 4 ship modes |
| Route Drill-Down | Order-level analysis for any specific Factory-to-State route |

---

## Data Anomaly Note

The raw dataset contained a ship date year inflation error where Ship Date years were entered 2 to 4 years ahead of the actual date. This caused raw lead times to appear as 904 to 1,642 days. The fix applied was:

```
actual_lead_time = raw_lead_time % 365
```

This recovered accurate lead times ranging from 174 to 185 days for all 10,194 records.

---

## KPIs Computed

1. Shipping Lead Time: days between order date and ship date per order
2. Average Lead Time: mean lead time per route
3. Route Volume: total shipments per route
4. Delay Frequency: percentage of shipments exceeding the 75th percentile threshold
5. Route Efficiency Score: normalised score from 0 (slowest) to 100 (fastest)
