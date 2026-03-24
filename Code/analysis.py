"""
Nassau Candy Distributor — Analytical Methodology Pipeline
============================================================
Layer 1 + 2: Full analysis, feature engineering, KPI computation
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV  = BASE_DIR.parent / "Nassau Candy Distributor.csv"
OUTPUT_DIR = BASE_DIR.parent / "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

SEP = "\n" + "=" * 65

PRODUCT_FACTORY = {
    "Wonka Bar - Nutty Crunch Surprise":  "Lot's O' Nuts",
    "Wonka Bar - Fudge Mallows":          "Lot's O' Nuts",
    "Wonka Bar -Scrumdiddlyumptious":     "Lot's O' Nuts",
    "Wonka Bar - Milk Chocolate":         "Wicked Choccy's",
    "Wonka Bar - Triple Dazzle Caramel":  "Wicked Choccy's",
    "Laffy Taffy":                        "Sugar Shack",
    "SweeTARTS":                          "Sugar Shack",
    "Nerds":                              "Sugar Shack",
    "Fun Dip":                            "Sugar Shack",
    "Fizzy Lifting Drinks":               "Sugar Shack",
    "Everlasting Gobstopper":             "Secret Factory",
    "Lickable Wallpaper":                 "Secret Factory",
    "Wonka Gum":                          "Secret Factory",
    "Hair Toffee":                        "The Other Factory",
    "Kazookles":                          "The Other Factory",
}

SHIP_MODE_ORDER = ["Same Day", "First Class", "Second Class", "Standard Class"]

def save(df, filename, label):
    path = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(path, index=False)
    print(f"  ✅  Saved → {path}  ({len(df):,} rows)")

def log(title):
    print(f"{SEP}\n  {title}\n{'=' * 65}")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 1 — DATA LOADING
# ═════════════════════════════════════════════════════════════════════════════
log("STEP 1 — DATA LOADING")

df_raw = pd.read_csv(INPUT_CSV)
print(f"\n  Rows loaded   : {len(df_raw):,}")
print(f"  Columns       : {df_raw.shape[1]}")
print(f"  Column names  : {df_raw.columns.tolist()}")
print(f"\n  First 3 rows:")
print(df_raw.head(3).to_string())


# ═════════════════════════════════════════════════════════════════════════════
# STEP 2 — DATA CLEANING & VALIDATION
# ═════════════════════════════════════════════════════════════════════════════
log("STEP 2 — DATA CLEANING & VALIDATION")

df = df_raw.copy()

print("\n  [2a] Missing values per column:")
missing = df.isnull().sum()
print("  None — dataset is complete." if not missing.any() else missing[missing > 0])

print("\n  [2b] Parsing date columns (day-first format)...")
df["Order Date"] = pd.to_datetime(df["Order Date"], dayfirst=True)
df["Ship Date"]  = pd.to_datetime(df["Ship Date"],  dayfirst=True)
print(f"  Order Date range : {df['Order Date'].min().date()}  →  {df['Order Date'].max().date()}")
print(f"  Ship Date range  : {df['Ship Date'].min().date()}  →  {df['Ship Date'].max().date()}")

raw_lt = (df["Ship Date"] - df["Order Date"]).dt.days
print(f"\n  [2c] Raw lead time stats:")
print(raw_lt.describe().round(1).to_string())
print("""
  ⚠  ANOMALY: Raw lead times cluster at ~908, ~1273, ~1638 days (365-day gaps).
     Ship Date year is inflated by 2-4 years in the source data.
     FIX: actual_lead_time = raw_lead_time % 365
""")

df["Lead Time"] = raw_lt % 365
before = len(df)
df = df[df["Lead Time"] > 0].copy()
print(f"  [2d] Fixed lead time range : {df['Lead Time'].min()} – {df['Lead Time'].max()} days")
print(f"  [2e] Invalid records removed : {before - len(df)}")

print("\n  [2f] Negative value check:")
for col in ["Sales", "Units", "Gross Profit", "Cost"]:
    n = (df[col] < 0).sum()
    print(f"       {col:15s}: {n} {'✅' if n == 0 else '❌'}")

for col in ["City", "State/Province", "Region", "Country/Region"]:
    df[col] = df[col].str.strip()

print(f"\n  ✅  Clean dataset: {len(df):,} rows")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 3 — FEATURE ENGINEERING
# ═════════════════════════════════════════════════════════════════════════════
log("STEP 3 — FEATURE ENGINEERING")

df["Factory"]      = df["Product Name"].map(PRODUCT_FACTORY)
df["Route_State"]  = df["Factory"] + "  →  " + df["State/Province"]
df["Route_Region"] = df["Factory"] + "  →  " + df["Region"]
df["Order Year"]   = df["Order Date"].dt.year
df["Order Month"]  = df["Order Date"].dt.to_period("M").astype(str)
df["Order Quarter"]= df["Order Date"].dt.to_period("Q").astype(str)

print(f"\n  Factory mapping:")
print(df["Factory"].value_counts().to_string())
print(f"\n  Unique Factory→State routes  : {df['Route_State'].nunique()}")
print(f"  Unique Factory→Region routes : {df['Route_Region'].nunique()}")
print(f"\n  Ship Mode distribution:")
print(df["Ship Mode"].value_counts().to_string())
print(f"\n  ✅  Features added. Dataset now has {df.shape[1]} columns.")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 4 — KPI COMPUTATION
# ═════════════════════════════════════════════════════════════════════════════
log("STEP 4 — KPI COMPUTATION")

# KPI 1: Shipping Lead Time — df["Lead Time"] (per order)
print(f"\n  KPI 1 — Shipping Lead Time per order:")
print(df["Lead Time"].describe().round(2).to_string())

# KPI 4: Delay Frequency
delay_threshold = df["Lead Time"].quantile(0.75)
df["Is_Delayed"] = (df["Lead Time"] > delay_threshold).astype(int)
print(f"\n  KPI 4 — Delay Frequency:")
print(f"           Threshold (P75) : {delay_threshold:.0f} days")
print(f"           Delayed         : {df['Is_Delayed'].sum():,} of {len(df):,} ({100*df['Is_Delayed'].mean():.1f}%)")

# KPI 5: Route Efficiency Score (0=slowest, 100=fastest)
min_lt, max_lt = df["Lead Time"].min(), df["Lead Time"].max()
df["Efficiency_Score"] = (100 * (1 - (df["Lead Time"] - min_lt) / (max_lt - min_lt))).round(2)
print(f"\n  KPI 5 — Efficiency Score range: {df['Efficiency_Score'].min():.0f} – {df['Efficiency_Score'].max():.0f}")

save(df, "kpi_orders_enriched.csv", "Enriched order-level dataset")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 5 — ROUTE DEFINITION & AGGREGATION
# ═════════════════════════════════════════════════════════════════════════════
log("STEP 5 — ROUTE DEFINITION & AGGREGATION")

route_agg = (
    df.groupby(["Factory", "State/Province", "Region", "Route_State", "Route_Region"])
    .agg(
        Route_Volume        = ("Lead Time",         "count"),
        Avg_Lead_Time       = ("Lead Time",         "mean"),
        Median_Lead_Time    = ("Lead Time",         "median"),
        Lead_Time_Std_Dev   = ("Lead Time",         "std"),
        Lead_Time_Min       = ("Lead Time",         "min"),
        Lead_Time_Max       = ("Lead Time",         "max"),
        Delayed_Shipments   = ("Is_Delayed",        "sum"),
        Delay_Frequency_Pct = ("Is_Delayed",        lambda x: round(100 * x.mean(), 2)),
        Avg_Efficiency_Score= ("Efficiency_Score",  "mean"),
        Total_Sales         = ("Sales",             "sum"),
        Avg_Gross_Profit    = ("Gross Profit",      "mean"),
        Total_Units         = ("Units",             "sum"),
    )
    .reset_index()
)

for col in ["Avg_Lead_Time","Median_Lead_Time","Lead_Time_Std_Dev","Avg_Efficiency_Score"]:
    route_agg[col] = route_agg[col].round(2)

route_agg = route_agg.sort_values("Avg_Lead_Time").reset_index(drop=True)
route_agg["Efficiency_Rank"] = route_agg["Avg_Lead_Time"].rank(method="min").astype(int)

print(f"\n  Total unique routes : {len(route_agg)}")
save(route_agg, "kpi_route_aggregation.csv", "Route-level KPI aggregation")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 6 — EFFICIENCY BENCHMARKING
# ═════════════════════════════════════════════════════════════════════════════
log("STEP 6 — EFFICIENCY BENCHMARKING")

cols_show = ["Efficiency_Rank","Route_State","Avg_Lead_Time","Avg_Efficiency_Score",
             "Delay_Frequency_Pct","Route_Volume"]

top10 = route_agg.head(10).copy()
bot10 = route_agg.tail(10).sort_values("Avg_Lead_Time", ascending=False).copy()

print("\n  TOP 10 MOST EFFICIENT ROUTES:")
print(top10[cols_show].to_string(index=False))
print("\n  BOTTOM 10 LEAST EFFICIENT ROUTES:")
print(bot10[cols_show].to_string(index=False))

top10.to_csv(os.path.join(OUTPUT_DIR, "benchmark_top10_routes.csv"), index=False)
bot10.to_csv(os.path.join(OUTPUT_DIR, "benchmark_bottom10_routes.csv"), index=False)
print(f"\n  ✅  Saved top10 and bottom10 benchmark files.")

mode_route_frames = []
for mode in SHIP_MODE_ORDER:
    mode_df = df[df["Ship Mode"] == mode]
    mr = (
        mode_df.groupby("Route_State")
        .agg(
            Route_Volume        = ("Lead Time", "count"),
            Avg_Lead_Time       = ("Lead Time", "mean"),
            Delay_Frequency_Pct = ("Is_Delayed", lambda x: round(100 * x.mean(), 2)),
            Avg_Efficiency_Score= ("Efficiency_Score", "mean"),
        )
        .reset_index()
        .sort_values("Avg_Lead_Time")
    )
    mr["Ship_Mode"]     = mode
    mr["Avg_Lead_Time"] = mr["Avg_Lead_Time"].round(2)
    mode_route_frames.append(mr)

save(pd.concat(mode_route_frames, ignore_index=True),
     "kpi_routes_by_ship_mode.csv", "Route rankings per ship mode")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 7 — GEOGRAPHIC BOTTLENECK ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════
log("STEP 7 — GEOGRAPHIC BOTTLENECK ANALYSIS")

state_agg = (
    df.groupby(["State/Province", "Region"])
    .agg(
        Route_Volume        = ("Lead Time", "count"),
        Avg_Lead_Time       = ("Lead Time", "mean"),
        Lead_Time_Std_Dev   = ("Lead Time", "std"),
        Delay_Frequency_Pct = ("Is_Delayed", lambda x: round(100 * x.mean(), 2)),
        Total_Sales         = ("Sales", "sum"),
        Avg_Efficiency_Score= ("Efficiency_Score", "mean"),
    )
    .reset_index()
)
for col in ["Avg_Lead_Time","Lead_Time_Std_Dev","Avg_Efficiency_Score"]:
    state_agg[col] = state_agg[col].round(2)

vol_p60 = state_agg["Route_Volume"].quantile(0.60)
lt_p60  = state_agg["Avg_Lead_Time"].quantile(0.60)
state_agg["Is_Bottleneck"] = (
    (state_agg["Route_Volume"]  >= vol_p60) &
    (state_agg["Avg_Lead_Time"] >= lt_p60)
).astype(int)

bottlenecks = (
    state_agg[state_agg["Is_Bottleneck"] == 1]
    .sort_values("Avg_Lead_Time", ascending=False)
    .reset_index(drop=True)
)

region_agg = (
    df.groupby("Region")
    .agg(
        Route_Volume        = ("Lead Time", "count"),
        Avg_Lead_Time       = ("Lead Time", "mean"),
        Lead_Time_Std_Dev   = ("Lead Time", "std"),
        Delay_Frequency_Pct = ("Is_Delayed", lambda x: round(100 * x.mean(), 2)),
        Total_Sales         = ("Sales", "sum"),
        Avg_Efficiency_Score= ("Efficiency_Score", "mean"),
    )
    .reset_index()
    .sort_values("Avg_Lead_Time", ascending=False)
)
for col in ["Avg_Lead_Time","Lead_Time_Std_Dev","Avg_Efficiency_Score"]:
    region_agg[col] = region_agg[col].round(2)

print(f"\n  Bottleneck states identified: {len(bottlenecks)}")
print(bottlenecks[["State/Province","Region","Route_Volume",
                    "Avg_Lead_Time","Delay_Frequency_Pct"]].to_string(index=False))

save(state_agg,   "kpi_state_performance.csv",  "State-level KPIs")
save(region_agg,  "kpi_region_performance.csv", "Region-level KPIs")
save(bottlenecks, "kpi_bottleneck_states.csv",  "Bottleneck states")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 8 — SHIP MODE PERFORMANCE ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════
log("STEP 8 — SHIP MODE PERFORMANCE ANALYSIS")

mode_agg = (
    df.groupby("Ship Mode")
    .agg(
        Route_Volume        = ("Lead Time",        "count"),
        Avg_Lead_Time       = ("Lead Time",        "mean"),
        Median_Lead_Time    = ("Lead Time",        "median"),
        Lead_Time_Std_Dev   = ("Lead Time",        "std"),
        Delay_Frequency_Pct = ("Is_Delayed",       lambda x: round(100 * x.mean(), 2)),
        Avg_Efficiency_Score= ("Efficiency_Score", "mean"),
        Avg_Sales           = ("Sales",            "mean"),
        Total_Sales         = ("Sales",            "sum"),
        Avg_Cost            = ("Cost",             "mean"),
        Avg_Gross_Profit    = ("Gross Profit",     "mean"),
        Avg_Units           = ("Units",            "mean"),
    )
    .reset_index()
)
mode_agg["Ship Mode"] = pd.Categorical(
    mode_agg["Ship Mode"], categories=SHIP_MODE_ORDER, ordered=True
)
mode_agg = mode_agg.sort_values("Ship Mode").reset_index(drop=True)
for col in ["Avg_Lead_Time","Median_Lead_Time","Lead_Time_Std_Dev",
            "Avg_Efficiency_Score","Avg_Sales","Avg_Cost","Avg_Gross_Profit"]:
    mode_agg[col] = mode_agg[col].round(2)

print("\n  Ship Mode Summary:")
print(mode_agg[["Ship Mode","Avg_Lead_Time","Delay_Frequency_Pct",
                 "Route_Volume","Avg_Cost","Avg_Gross_Profit"]].to_string(index=False))

pivot = df.pivot_table(
    values="Lead Time", index="Factory", columns="Ship Mode", aggfunc="mean"
).round(2)
pivot = pivot.reindex(columns=[c for c in SHIP_MODE_ORDER if c in pivot.columns])

save(mode_agg,         "kpi_ship_mode_performance.csv",   "Ship mode KPI summary")
save(pivot.reset_index(),"kpi_factory_shipmode_pivot.csv","Factory × Ship Mode pivot")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 9 — FACTORY-LEVEL KPI SUMMARY
# ═════════════════════════════════════════════════════════════════════════════
log("STEP 9 — FACTORY-LEVEL KPI SUMMARY")

factory_agg = (
    df.groupby("Factory")
    .agg(
        Route_Volume        = ("Lead Time",        "count"),
        Unique_States       = ("State/Province",   "nunique"),
        Unique_Routes       = ("Route_State",      "nunique"),
        Avg_Lead_Time       = ("Lead Time",        "mean"),
        Lead_Time_Std_Dev   = ("Lead Time",        "std"),
        Delay_Frequency_Pct = ("Is_Delayed",       lambda x: round(100 * x.mean(), 2)),
        Avg_Efficiency_Score= ("Efficiency_Score", "mean"),
        Total_Sales         = ("Sales",            "sum"),
        Avg_Gross_Profit    = ("Gross Profit",     "mean"),
    )
    .reset_index()
    .sort_values("Avg_Lead_Time")
)
for col in ["Avg_Lead_Time","Lead_Time_Std_Dev","Avg_Efficiency_Score","Avg_Gross_Profit"]:
    factory_agg[col] = factory_agg[col].round(2)

print("\n  Factory Performance (fastest → slowest):")
print(factory_agg.to_string(index=False))
save(factory_agg, "kpi_factory_performance.csv", "Factory-level KPI summary")


# ═════════════════════════════════════════════════════════════════════════════
# DONE
# ═════════════════════════════════════════════════════════════════════════════
log("ANALYSIS COMPLETE")
print(f"""
  All output files saved to: {OUTPUT_DIR}/

  ┌─────────────────────────────────────────┐
  │  Next step: run the dashboard           │
  │  > streamlit run dashboard.py           │
  │  Then open http://localhost:8501        │
  └─────────────────────────────────────────┘
""")
