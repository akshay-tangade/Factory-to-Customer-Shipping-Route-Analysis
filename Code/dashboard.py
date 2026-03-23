"""
Nassau Candy Distributor — Shipping Route Efficiency Dashboard
===============================================================
"""

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
OUTPUT_DIR = "../outputs"

FACTORY_COORDS = {
    "Lot's O' Nuts":     {"lat": 32.881893, "lon": -111.768036},
    "Wicked Choccy's":   {"lat": 32.076176, "lon":  -81.088371},
    "Sugar Shack":       {"lat": 48.119140, "lon":  -96.181150},
    "Secret Factory":    {"lat": 41.446333, "lon":  -90.565487},
    "The Other Factory": {"lat": 35.117500, "lon":  -89.971107},
}

SHIP_MODE_ORDER = ["Same Day", "First Class", "Second Class", "Standard Class"]

STATE_ABBREV = {
    "Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA",
    "Colorado":"CO","Connecticut":"CT","Delaware":"DE","Florida":"FL","Georgia":"GA",
    "Hawaii":"HI","Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS",
    "Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD","Massachusetts":"MA",
    "Michigan":"MI","Minnesota":"MN","Mississippi":"MS","Missouri":"MO","Montana":"MT",
    "Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM",
    "New York":"NY","North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK",
    "Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI","South Carolina":"SC",
    "South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT",
    "Virginia":"VA","Washington":"WA","West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY",
    "District of Columbia":"DC",
}

REGION_COLORS = {
    "Interior": "#636EFA", "Atlantic": "#EF553B",
    "Gulf":     "#00CC96", "Pacific":  "#AB63FA"
}

# ─────────────────────────────────────────────────────────────────────────────
# LOAD PRE-COMPUTED KPI OUTPUTS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def load_all():
    def load(f):
        return pd.read_csv(f"{OUTPUT_DIR}/{f}")

    orders = load("kpi_orders_enriched.csv")
    orders["Order Date"] = pd.to_datetime(orders["Order Date"])
    orders["Ship Date"]  = pd.to_datetime(orders["Ship Date"])

    return (
        orders,
        load("kpi_route_aggregation.csv"),
        load("benchmark_top10_routes.csv"),
        load("benchmark_bottom10_routes.csv"),
        load("kpi_routes_by_ship_mode.csv"),
        load("kpi_state_performance.csv"),
        load("kpi_region_performance.csv"),
        load("kpi_bottleneck_states.csv"),
        load("kpi_ship_mode_performance.csv"),
        load("kpi_factory_shipmode_pivot.csv"),
        load("kpi_factory_performance.csv"),
    )

try:
    (orders, routes, top10, bot10, by_mode,
     states, regions, bottlenecks, ship_modes,
     fac_pivot, factories) = load_all()
except FileNotFoundError:
    st.error("❌  Output files not found. Please run `python analysis.py` first.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE SETUP
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nassau Candy — Shipping Intelligence",
    page_icon="🍬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .kpi-box  { background:#1a1f2e; border-radius:10px; padding:18px 22px;
                text-align:center; border:1px solid #2d3550; }
    .kpi-val  { font-size:1.9rem; font-weight:700; color:#636EFA; }
    .kpi-lbl  { font-size:.80rem; color:#9aa3bf; margin-top:5px;
                text-transform:uppercase; letter-spacing:.05em; }
    .src-note { background:#1e2538; border-left:3px solid #636EFA;
                padding:10px 16px; border-radius:4px;
                font-size:.85rem; color:#9aa3bf; margin-bottom:12px; }
</style>
""", unsafe_allow_html=True)

# ── Page header with logo ─────────────────────────────────────────────────────
from PIL import Image as _Image
_col_logo, _col_title = st.columns([1, 5])
with _col_logo:
    try:
        _logo = _Image.open("../Nassua Candy Logo.jpg")
        st.image(_logo, width=130)
    except Exception:
        pass
with _col_title:
    st.markdown("## Nassau Candy Distributor")
    st.markdown("##### Shipping Route Efficiency Intelligence Dashboard")
st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR FILTERS
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    # ── Logo ─────────────────────────────────────────────────────────────────
    from PIL import Image
    try:
        logo = Image.open("../Nassua Candy Logo.jpg")
        st.image(logo, use_container_width=True)
    except Exception:
        st.title("🍬 Nassau Candy")
    st.caption("Shipping Route Efficiency Dashboard")
    st.markdown("---")
    st.subheader("Filters")
    st.caption("Filters apply to the Route Drill-Down tab only.")

    min_date  = orders["Order Date"].min().date()
    max_date  = orders["Order Date"].max().date()
    date_range = st.date_input("Order Date Range",
                               value=(min_date, max_date),
                               min_value=min_date, max_value=max_date)
    start_date, end_date = date_range if len(date_range) == 2 else (min_date, max_date)

    sel_regions   = st.multiselect("Region",
                                   sorted(orders["Region"].unique()),
                                   default=sorted(orders["Region"].unique()))
    sel_modes     = st.multiselect("Ship Mode", SHIP_MODE_ORDER, default=SHIP_MODE_ORDER)
    sel_factories = st.multiselect("Factory",
                                   sorted(orders["Factory"].dropna().unique()),
                                   default=sorted(orders["Factory"].dropna().unique()))

    lt_threshold = st.slider(
        "Delay Threshold (days)",
        int(orders["Lead Time"].min()),
        int(orders["Lead Time"].max()),
        int(orders["Lead Time"].quantile(0.75)),
        help="Shipments above this are flagged delayed in the Drill-Down tab.",
    )
    st.markdown("---")
    st.caption("Re-run `python analysis.py` to refresh KPI data.")

# Filtered orders — only used in drill-down tab
filtered = orders[
    (orders["Order Date"].dt.date >= start_date) &
    (orders["Order Date"].dt.date <= end_date)   &
    (orders["Region"].isin(sel_regions))         &
    (orders["Ship Mode"].isin(sel_modes))        &
    (orders["Factory"].isin(sel_factories))
].copy()
filtered["Is_Delayed"] = (filtered["Lead Time"] > lt_threshold).astype(int)

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊  Route Efficiency Overview",
    "🗺️  Geographic Map",
    "🚨  Bottleneck Analysis",
    "🚚  Ship Mode Comparison",
    "🔍  Route Drill-Down",
])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — ROUTE EFFICIENCY OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("Route Efficiency Overview")
    # st.markdown('<div class="src-note">📂 Source: kpi_route_aggregation.csv · benchmark_top10_routes.csv · benchmark_bottom10_routes.csv</div>', unsafe_allow_html=True)

    # KPI cards
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, val, lbl in [
        (c1, f"{int(routes['Route_Volume'].sum()):,}",          "Total Shipments"),
        (c2, f"{routes['Avg_Lead_Time'].mean():.1f} days",      "Avg Lead Time"),
        (c3, f"{routes['Delay_Frequency_Pct'].mean():.1f}%",    "Avg Delay Rate"),
        (c4, f"{len(routes)}",                                   "Unique Routes"),
        (c5, f"{routes['Avg_Efficiency_Score'].mean():.1f}/100", "Avg Efficiency Score"),
    ]:
        col.markdown(
            f'<div class="kpi-box"><div class="kpi-val">{val}</div>'
            f'<div class="kpi-lbl">{lbl}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)

    # Top 10 / Bottom 10
    l, r = st.columns(2)
    with l:
        st.subheader("🏆 Top 10 Most Efficient Routes")
        fig = px.bar(
            top10.sort_values("Avg_Lead_Time"),
            x="Avg_Lead_Time", y="Route_State", orientation="h",
            color="Avg_Lead_Time", color_continuous_scale="RdYlGn_r",
            text="Avg_Lead_Time",
            labels={"Avg_Lead_Time": "Avg Lead Time (days)", "Route_State": ""},
        )
        fig.update_traces(texttemplate="%{text:.1f}d", textposition="outside")
        fig.update_layout(height=400, showlegend=False, coloraxis_showscale=False,
                          yaxis=dict(autorange="reversed"),
                          margin=dict(l=5, r=40, t=5, b=5))
        st.plotly_chart(fig, use_container_width=True)

    with r:
        st.subheader("⚠️ Bottom 10 Least Efficient Routes")
        fig2 = px.bar(
            bot10.sort_values("Avg_Lead_Time", ascending=False),
            x="Avg_Lead_Time", y="Route_State", orientation="h",
            color="Avg_Lead_Time", color_continuous_scale="RdYlGn_r",
            text="Avg_Lead_Time",
            labels={"Avg_Lead_Time": "Avg Lead Time (days)", "Route_State": ""},
        )
        fig2.update_traces(texttemplate="%{text:.1f}d", textposition="outside")
        fig2.update_layout(height=400, showlegend=False, coloraxis_showscale=False,
                           yaxis=dict(autorange="reversed"),
                           margin=dict(l=5, r=40, t=5, b=5))
        st.plotly_chart(fig2, use_container_width=True)

    # Lead Time Variability
    st.subheader("Lead Time Variability — Top 20 Routes by Volume")
    st.caption("Std Dev of lead time: higher = less predictable delivery")
    top20 = routes.nlargest(20, "Route_Volume").sort_values("Lead_Time_Std_Dev", ascending=False)
    fig_v = px.bar(
        top20, x="Lead_Time_Std_Dev", y="Route_State", orientation="h",
        color="Avg_Lead_Time", color_continuous_scale="RdYlGn_r",
        text="Lead_Time_Std_Dev",
        labels={"Lead_Time_Std_Dev": "Std Dev (days)", "Avg_Lead_Time": "Avg LT", "Route_State": ""},
    )
    fig_v.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig_v.update_layout(height=540, yaxis=dict(autorange="reversed"),
                        margin=dict(l=5, r=40, t=10, b=5))
    st.plotly_chart(fig_v, use_container_width=True)

    # Efficiency Score scatter
    st.subheader("Route Efficiency Score vs. Volume")
    fig_s = px.scatter(
        routes, x="Route_Volume", y="Avg_Efficiency_Score",
        size="Route_Volume", color="Delay_Frequency_Pct",
        hover_name="Route_State", color_continuous_scale="RdYlGn_r",
        labels={"Route_Volume": "Total Shipments",
                "Avg_Efficiency_Score": "Efficiency Score (0–100)",
                "Delay_Frequency_Pct": "Delay Rate %"},
    )
    fig_s.update_layout(height=420)
    st.plotly_chart(fig_s, use_container_width=True)

    # Top/Bottom 10 by Ship Mode
    st.subheader("Top & Bottom 10 Routes by Ship Mode")
    mode_sel = st.selectbox("Select Ship Mode", SHIP_MODE_ORDER, key="tab1_mode")
    mode_routes = by_mode[by_mode["Ship_Mode"] == mode_sel].sort_values("Avg_Lead_Time")

    ml, mr = st.columns(2)
    with ml:
        st.markdown(f"**🏆 Top 10 — {mode_sel}**")
        fg = px.bar(mode_routes.head(10),
                    x="Avg_Lead_Time", y="Route_State", orientation="h",
                    color="Avg_Lead_Time", color_continuous_scale="RdYlGn_r",
                    text="Avg_Lead_Time",
                    labels={"Avg_Lead_Time": "Avg Lead Time (days)", "Route_State": ""})
        fg.update_traces(texttemplate="%{text:.1f}d", textposition="outside")
        fg.update_layout(height=380, showlegend=False, coloraxis_showscale=False,
                         yaxis=dict(autorange="reversed"), margin=dict(l=5, r=30, t=5, b=5))
        st.plotly_chart(fg, use_container_width=True)
    with mr:
        st.markdown(f"**⚠️ Bottom 10 — {mode_sel}**")
        fg2 = px.bar(mode_routes.tail(10).sort_values("Avg_Lead_Time", ascending=False),
                     x="Avg_Lead_Time", y="Route_State", orientation="h",
                     color="Avg_Lead_Time", color_continuous_scale="RdYlGn_r",
                     text="Avg_Lead_Time",
                     labels={"Avg_Lead_Time": "Avg Lead Time (days)", "Route_State": ""})
        fg2.update_traces(texttemplate="%{text:.1f}d", textposition="outside")
        fg2.update_layout(height=380, showlegend=False, coloraxis_showscale=False,
                          yaxis=dict(autorange="reversed"), margin=dict(l=5, r=30, t=5, b=5))
        st.plotly_chart(fg2, use_container_width=True)

    # Full route table
    with st.expander("📋 Full Route Leaderboard — All Routes"):
        st.dataframe(
            routes[["Efficiency_Rank","Route_State","Route_Volume","Avg_Lead_Time",
                     "Median_Lead_Time","Lead_Time_Std_Dev","Avg_Efficiency_Score",
                     "Delay_Frequency_Pct","Total_Sales","Avg_Gross_Profit"]]
            .rename(columns={
                "Efficiency_Rank":"Rank","Route_State":"Route","Route_Volume":"Shipments",
                "Avg_Lead_Time":"Avg LT (d)","Median_Lead_Time":"Median LT (d)",
                "Lead_Time_Std_Dev":"LT Std Dev","Avg_Efficiency_Score":"Eff. Score",
                "Delay_Frequency_Pct":"Delay %","Total_Sales":"Total Sales ($)",
                "Avg_Gross_Profit":"Avg Profit ($)",
            })
            .style
            .background_gradient(subset=["Avg LT (d)"], cmap="RdYlGn_r")
            .background_gradient(subset=["Eff. Score"],  cmap="RdYlGn")
            .background_gradient(subset=["Delay %"],     cmap="Reds")
            .format({"Total Sales ($)": "${:,.0f}", "Avg Profit ($)": "${:.2f}",
                     "Avg LT (d)": "{:.1f}",        "Eff. Score": "{:.1f}",
                     "Delay %": "{:.1f}%"}),
            use_container_width=True, height=420,
        )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — GEOGRAPHIC MAP
# ═════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("Geographic Shipping Performance Map")
    # st.markdown('<div class="src-note">📂 Source: kpi_state_performance.csv · kpi_region_performance.csv</div>', unsafe_allow_html=True)

    states["State_Code"] = states["State/Province"].map(STATE_ABBREV)

    map_metric = st.radio(
        "Select Map Metric",
        ["Avg_Lead_Time", "Delay_Frequency_Pct", "Route_Volume"],
        format_func=lambda x: {
            "Avg_Lead_Time":        "Average Lead Time (days)",
            "Delay_Frequency_Pct":  "Delay Rate (%)",
            "Route_Volume":         "Total Shipments",
        }[x],
        horizontal=True,
    )
    metric_label = {"Avg_Lead_Time":"Avg Lead Time (days)",
                    "Delay_Frequency_Pct":"Delay Rate (%)","Route_Volume":"Total Shipments"}[map_metric]

    fig_map = px.choropleth(
        states.dropna(subset=["State_Code"]),
        locations="State_Code", locationmode="USA-states",
        color=map_metric,
        color_continuous_scale="RdYlGn_r" if map_metric != "Route_Volume" else "Blues",
        scope="usa", hover_name="State/Province",
        hover_data={"State_Code": False,
                    "Avg_Lead_Time": ":.1f",
                    "Delay_Frequency_Pct": ":.1f",
                    "Route_Volume": ":,"},
        labels={map_metric: metric_label},
        title=f"US State Heatmap — {metric_label}",
    )

    factory_df = pd.DataFrame([
        {"Factory": k, "lat": v["lat"], "lon": v["lon"]}
        for k, v in FACTORY_COORDS.items()
    ])
    fig_map.add_scattergeo(
        lat=factory_df["lat"], lon=factory_df["lon"],
        text=factory_df["Factory"], mode="markers+text",
        marker=dict(size=14, color="yellow", symbol="star",
                    line=dict(width=1, color="black")),
        textposition="top center", name="Factory",
    )
    fig_map.update_layout(height=560, margin=dict(l=0, r=0, t=50, b=0))
    st.plotly_chart(fig_map, use_container_width=True)

    st.subheader("Regional Performance Summary")
    ra, rb = st.columns(2)
    with ra:
        fig_r1 = px.bar(
            regions.sort_values("Avg_Lead_Time", ascending=False),
            x="Region", y="Avg_Lead_Time", color="Region",
            color_discrete_map=REGION_COLORS, text="Avg_Lead_Time",
            error_y="Lead_Time_Std_Dev",
            title="Avg Lead Time by Region (± 1 std dev)",
            labels={"Avg_Lead_Time": "Avg Lead Time (days)"},
        )
        fig_r1.update_traces(texttemplate="%{text:.2f}d", textposition="outside")
        fig_r1.update_layout(showlegend=False, height=340)
        st.plotly_chart(fig_r1, use_container_width=True)
    with rb:
        fig_r2 = px.bar(
            regions.sort_values("Delay_Frequency_Pct", ascending=False),
            x="Region", y="Delay_Frequency_Pct", color="Region",
            color_discrete_map=REGION_COLORS, text="Delay_Frequency_Pct",
            title="Delay Rate % by Region",
            labels={"Delay_Frequency_Pct": "Delay Rate (%)"},
        )
        fig_r2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_r2.update_layout(showlegend=False, height=340)
        st.plotly_chart(fig_r2, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — GEOGRAPHIC BOTTLENECK ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("Geographic Bottleneck Analysis")
    # st.markdown('<div class="src-note">📂 Source: kpi_state_performance.csv · kpi_bottleneck_states.csv<br>Bottleneck = high shipment volume (≥ P60) AND high avg lead time (≥ P60)</div>', unsafe_allow_html=True)

    b1, b2, b3 = st.columns(3)
    for col, val, lbl in [
        (b1, str(len(bottlenecks)),                                  "Bottleneck States"),
        (b2, f"{int(bottlenecks['Route_Volume'].sum()):,}",          "Shipments Through Bottlenecks"),
        (b3, f"{bottlenecks['Delay_Frequency_Pct'].mean():.1f}%",   "Avg Delay Rate in Bottlenecks"),
    ]:
        col.markdown(
            f'<div class="kpi-box"><div class="kpi-val">{val}</div>'
            f'<div class="kpi-lbl">{lbl}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)

    # Quadrant chart
    st.subheader("Volume vs. Lead Time — Bottleneck Quadrant")
    vol_p60 = states["Route_Volume"].quantile(0.60)
    lt_p60  = states["Avg_Lead_Time"].quantile(0.60)
    states["Category"] = states["Is_Bottleneck"].map({1: "🚨 Bottleneck", 0: "✅ Acceptable"})

    fig_q = px.scatter(
        states,
        x="Route_Volume", y="Avg_Lead_Time",
        color="Category",
        color_discrete_map={"🚨 Bottleneck": "#EF553B", "✅ Acceptable": "#00CC96"},
        size="Delay_Frequency_Pct", size_max=35,
        hover_name="State/Province",
        hover_data={"Route_Volume": ":,", "Avg_Lead_Time": ":.2f",
                    "Delay_Frequency_Pct": ":.1f", "Category": False},
        labels={"Route_Volume": "Total Shipments",
                "Avg_Lead_Time": "Avg Lead Time (days)",
                "Delay_Frequency_Pct": "Delay Rate %"},
        title="Bubble size = delay rate  |  Red = bottleneck state",
    )
    fig_q.add_vline(x=vol_p60, line_dash="dash", line_color="#888",
                    annotation_text="Volume P60", annotation_position="top right")
    fig_q.add_hline(y=lt_p60, line_dash="dash", line_color="#888",
                    annotation_text="Lead Time P60", annotation_position="top right")
    fig_q.update_layout(height=500)
    st.plotly_chart(fig_q, use_container_width=True)

    # Bottleneck table
    st.subheader("🚨 Bottleneck States — Full KPI Detail")
    st.dataframe(
        bottlenecks[["State/Province","Region","Route_Volume","Avg_Lead_Time",
                      "Lead_Time_Std_Dev","Delay_Frequency_Pct",
                      "Avg_Efficiency_Score","Total_Sales"]]
        .rename(columns={
            "State/Province": "State", "Route_Volume": "Shipments",
            "Avg_Lead_Time": "Avg LT (d)", "Lead_Time_Std_Dev": "LT Std Dev",
            "Delay_Frequency_Pct": "Delay %", "Avg_Efficiency_Score": "Eff. Score",
            "Total_Sales": "Total Sales ($)",
        })
        .style
        .background_gradient(subset=["Avg LT (d)"], cmap="Reds")
        .background_gradient(subset=["Delay %"],    cmap="Reds")
        .format({"Avg LT (d)": "{:.2f}", "LT Std Dev": "{:.2f}",
                 "Delay %": "{:.1f}%", "Total Sales ($)": "${:,.0f}"}),
        use_container_width=True, height=280,
    )

    # Variability bar
    st.subheader("Lead Time Variability in Bottleneck States")
    fig_bv = px.bar(
        bottlenecks.sort_values("Lead_Time_Std_Dev", ascending=False),
        x="Lead_Time_Std_Dev", y="State/Province", orientation="h",
        color="Delay_Frequency_Pct", color_continuous_scale="Reds",
        text="Lead_Time_Std_Dev",
        labels={"Lead_Time_Std_Dev": "Std Dev (days)",
                "State/Province": "", "Delay_Frequency_Pct": "Delay Rate %"},
    )
    fig_bv.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig_bv.update_layout(height=320, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_bv, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — SHIP MODE COMPARISON
# ═════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("Ship Mode Performance Analysis")
    # st.markdown('<div class="src-note">📂 Source: kpi_ship_mode_performance.csv · kpi_factory_shipmode_pivot.csv</div>', unsafe_allow_html=True)

    ship_modes["Ship Mode"] = pd.Categorical(
        ship_modes["Ship Mode"], categories=SHIP_MODE_ORDER, ordered=True
    )
    ship_modes = ship_modes.sort_values("Ship Mode").reset_index(drop=True)

    # KPI metrics per mode
    cols = st.columns(4)
    for i, row in ship_modes.iterrows():
        cols[i].metric(
            label=row["Ship Mode"],
            value=f"{row['Avg_Lead_Time']:.1f} days",
            delta=f"{row['Delay_Frequency_Pct']:.1f}% delay rate",
            delta_color="inverse",
        )

    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        fig_box = px.box(
            orders, x="Ship Mode", y="Lead Time", color="Ship Mode",
            category_orders={"Ship Mode": SHIP_MODE_ORDER},
            title="Lead Time Distribution by Ship Mode",
            labels={"Lead Time": "Lead Time (days)"},
        )
        fig_box.update_layout(showlegend=False, height=380)
        st.plotly_chart(fig_box, use_container_width=True)

    with c2:
        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
        fig_dual.add_trace(
            go.Bar(x=ship_modes["Ship Mode"], y=ship_modes["Avg_Lead_Time"],
                   name="Avg Lead Time (days)", marker_color="#636EFA"),
            secondary_y=False,
        )
        fig_dual.add_trace(
            go.Scatter(x=ship_modes["Ship Mode"], y=ship_modes["Delay_Frequency_Pct"],
                       name="Delay Rate (%)", mode="lines+markers",
                       line=dict(color="#EF553B", width=2), marker=dict(size=10)),
            secondary_y=True,
        )
        fig_dual.update_yaxes(title_text="Avg Lead Time (days)", secondary_y=False)
        fig_dual.update_yaxes(title_text="Delay Rate (%)", secondary_y=True)
        fig_dual.update_layout(title="Lead Time vs Delay Rate by Ship Mode", height=380)
        st.plotly_chart(fig_dual, use_container_width=True)

    # Factory × Ship Mode heatmap
    st.subheader("Factory × Ship Mode — Avg Lead Time Heatmap")
    fac_plot = fac_pivot.set_index("Factory")
    fac_plot = fac_plot.reindex(columns=[c for c in SHIP_MODE_ORDER if c in fac_plot.columns])
    fig_hm = px.imshow(
        fac_plot, color_continuous_scale="RdYlGn_r", text_auto=True, aspect="auto",
        labels={"color": "Avg Lead Time (days)"},
        title="Avg Lead Time (days) per Factory × Ship Mode",
    )
    fig_hm.update_layout(height=340)
    st.plotly_chart(fig_hm, use_container_width=True)

    # Cost-time scatter
    st.subheader("Cost vs Speed — Trade-off Chart")
    fig_ct = px.scatter(
        ship_modes, x="Avg_Lead_Time", y="Avg_Cost",
        size="Route_Volume", text="Ship Mode", color="Ship Mode",
        title="Cost vs Speed (bubble size = shipment volume)",
        labels={"Avg_Lead_Time": "Avg Lead Time (days)", "Avg_Cost": "Avg Unit Cost ($)"},
    )
    fig_ct.update_traces(textposition="top center")
    fig_ct.update_layout(showlegend=False, height=380)
    st.plotly_chart(fig_ct, use_container_width=True)

    # Descriptive tradeoff table
    st.subheader("📋 Descriptive Cost–Time Trade-off Summary")
    tradeoff = ship_modes[["Ship Mode","Avg_Lead_Time","Avg_Cost","Avg_Gross_Profit",
                            "Delay_Frequency_Pct","Route_Volume","Avg_Sales"]].copy()
    tradeoff["Profit_Margin_%"] = (100 * tradeoff["Avg_Gross_Profit"] / tradeoff["Avg_Sales"]).round(1)
    tradeoff["Speed_Rank"]      = tradeoff["Avg_Lead_Time"].rank().astype(int)
    tradeoff["Recommendation"]  = tradeoff["Ship Mode"].map({
        "Same Day"      : "✅ Fastest & 0% delays — use for urgent orders",
        "First Class"   : "✅ Fast & 0% delays — best everyday balance",
        "Second Class"  : "⚠️ Moderate, low delay — OK for non-urgent",
        "Standard Class": "❌ Slowest, 38.8% delay — high risk",
    })
    st.dataframe(
        tradeoff[["Ship Mode","Speed_Rank","Avg_Lead_Time","Avg_Cost",
                  "Profit_Margin_%","Delay_Frequency_Pct","Route_Volume","Recommendation"]]
        .rename(columns={
            "Speed_Rank": "Speed Rank", "Avg_Lead_Time": "Avg LT (d)",
            "Avg_Cost": "Avg Cost ($)", "Profit_Margin_%": "Profit Margin %",
            "Delay_Frequency_Pct": "Delay Rate %", "Route_Volume": "Shipments",
        })
        .set_index("Ship Mode")
        .style
        .background_gradient(subset=["Avg LT (d)"], cmap="RdYlGn_r")
        .background_gradient(subset=["Delay Rate %"], cmap="Reds")
        .format({"Avg LT (d)": "{:.1f}", "Avg Cost ($)": "${:.2f}",
                 "Profit Margin %": "{:.1f}%", "Delay Rate %": "{:.1f}%"}),
        use_container_width=True, height=220,
    )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — ROUTE DRILL-DOWN
# ═════════════════════════════════════════════════════════════════════════════
with tab5:
    st.header("Route Drill-Down")
    # st.markdown('<div class="src-note">📂 Source: kpi_orders_enriched.csv — filtered by the sidebar controls</div>', unsafe_allow_html=True)

    if filtered.empty:
        st.warning("No data matches the current sidebar filters.")
        st.stop()

    d1, d2 = st.columns(2)
    with d1:
        sel_factory = st.selectbox("Select Factory",
                                   sorted(filtered["Factory"].dropna().unique()))
    with d2:
        avail_states = sorted(
            filtered[filtered["Factory"] == sel_factory]["State/Province"].unique()
        )
        sel_state = st.selectbox("Select State", avail_states)

    route_df = filtered[
        (filtered["Factory"] == sel_factory) &
        (filtered["State/Province"] == sel_state)
    ].copy()

    if route_df.empty:
        st.info("No shipments for this factory–state combination under current filters.")
    else:
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Shipments",  f"{len(route_df):,}")
        m2.metric("Avg Lead Time",    f"{route_df['Lead Time'].mean():.1f} days")
        m3.metric("LT Std Dev",       f"{route_df['Lead Time'].std():.2f} days")
        m4.metric("Delay Rate",       f"{100*route_df['Is_Delayed'].mean():.1f}%")
        m5.metric("Total Sales",      f"${route_df['Sales'].sum():,.0f}")

        st.markdown("---")
        cl, cr = st.columns(2)

        with cl:
            trend = (route_df.groupby("Order Month")["Lead Time"]
                     .agg(["mean", "std"]).reset_index()
                     .rename(columns={"mean": "Avg", "std": "Std"}))
            fig_t = px.line(
                trend, x="Order Month", y="Avg", markers=True, error_y="Std",
                title=f"Monthly Lead Time Trend — {sel_factory} → {sel_state}",
                labels={"Avg": "Avg Lead Time (days)", "Order Month": "Month"},
            )
            fig_t.update_layout(height=320)
            st.plotly_chart(fig_t, use_container_width=True)

        with cr:
            sm = (route_df.groupby("Ship Mode")
                  .agg(Shipments=("Lead Time", "count"),
                       Avg_LT=("Lead Time", "mean"),
                       Delay_Rate=("Is_Delayed", lambda x: 100 * x.mean()))
                  .reset_index())
            fig_sm = px.bar(
                sm, x="Ship Mode", y="Avg_LT", color="Delay_Rate",
                color_continuous_scale="RdYlGn_r", text="Avg_LT",
                category_orders={"Ship Mode": SHIP_MODE_ORDER},
                title="Avg Lead Time by Ship Mode (this route)",
                labels={"Avg_LT": "Avg Lead Time (days)", "Delay_Rate": "Delay %"},
            )
            fig_sm.update_traces(texttemplate="%{text:.1f}d", textposition="outside")
            fig_sm.update_layout(height=320)
            st.plotly_chart(fig_sm, use_container_width=True)

        with st.expander("📦 Order-Level Shipment Timeline"):
            fig_tl = px.scatter(
                route_df.sort_values("Order Date"),
                x="Order Date", y="Lead Time", color="Ship Mode",
                hover_data=["Order ID", "Product Name", "Sales"],
                title="Every order on this route plotted by lead time",
                category_orders={"Ship Mode": SHIP_MODE_ORDER},
                labels={"Lead Time": "Lead Time (days)"},
            )
            fig_tl.add_hline(y=lt_threshold, line_dash="dash", line_color="red",
                             annotation_text=f"Delay threshold: {lt_threshold}d")
            fig_tl.update_layout(height=380)
            st.plotly_chart(fig_tl, use_container_width=True)

            st.dataframe(
                route_df[["Order ID", "Order Date", "Ship Mode", "Product Name",
                           "Lead Time", "Is_Delayed", "Sales", "Gross Profit"]]
                .rename(columns={"Is_Delayed": "Delayed?"})
                .sort_values("Order Date", ascending=False)
                .reset_index(drop=True),
                use_container_width=True,
            )
