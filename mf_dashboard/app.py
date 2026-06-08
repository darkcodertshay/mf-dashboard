"""
app.py  –  Anand Rathi Equity MF Model Portfolio Dashboard
Run:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ── Page config (must be first Streamlit call) ────────────────────────────────

st.set_page_config(
    page_title="AR Model Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auto-refresh every 30 minutes ─────────────────────────────────────────────
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30 * 60 * 1000, key="auto_refresh")
except ImportError:
    pass

# ── Imports ───────────────────────────────────────────────────────────────────
from modules.data_ingestion import (
    build_scheme_dataframe, fetch_fund_flows, fetch_historical_nav, fetch_nifty50_nav
)
from modules.data_cleaning import enrich_dataframe, format_display_df, compute_summary_stats
from modules.portfolio_data import (
    SECTOR_ALLOCATION, MKTCAP_ALLOCATION, TOP_HOLDINGS,
    NO_OF_STOCKS, compute_overlap_matrix, get_aum_history, STOCK_MOVEMENTS
)
from modules.charts import (
    cagr_bar_chart, aum_bar_chart, risk_return_scatter, overlap_heatmap,
    sector_donut, mktcap_donut, holdings_bar, fund_flow_chart,
    category_flow_chart, benchmark_chart, aum_trend_chart,
    expense_ratio_chart, portfolio_weight_pie,
)
from modules.scheme_config import SCHEMES, CATEGORY_COLORS

# ── Global CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Mono&display=swap');

html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }

/* App background */
.stApp { background: #0F1117; color: #E8EAF0; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #13161F;
    border-right: 1px solid #252836;
}
[data-testid="stSidebar"] .css-1d391kg { padding: 1rem 0.75rem; }

/* Metric cards */
.kpi-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin-bottom: 24px; }
.kpi-card {
    background: #1A1D27;
    border: 1px solid #252836;
    border-radius: 10px;
    padding: 16px 14px;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #4FC3F7, #1565C0);
}
.kpi-value { font-size: 1.6rem; font-weight: 700; color: #4FC3F7; line-height: 1.2; }
.kpi-label { font-size: 0.72rem; color: #8892A4; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
.kpi-delta { font-size: 0.75rem; margin-top: 4px; }
.kpi-delta.pos { color: #66BB6A; }
.kpi-delta.neg { color: #EF5350; }

/* Section headers */
.section-header {
    font-size: 1.1rem; font-weight: 600; color: #4FC3F7;
    border-left: 3px solid #4FC3F7;
    padding-left: 10px;
    margin: 24px 0 14px 0;
    letter-spacing: 0.03em;
}

/* DataTable */
.dataframe { font-size: 0.78rem !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: #13161F; border-radius: 8px; padding: 4px; }
.stTabs [data-baseweb="tab"] { color: #8892A4; border-radius: 6px; }
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: #1A1D27; color: #4FC3F7;
}

/* Return color cells */
.pos-cell { color: #66BB6A !important; font-weight: 600; }
.neg-cell { color: #EF5350 !important; font-weight: 600; }

/* Logo / header bar */
.top-bar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 0 20px 0;
    border-bottom: 1px solid #252836;
    margin-bottom: 20px;
}
.logo-text {
    font-size: 1.4rem; font-weight: 700;
    background: linear-gradient(135deg, #4FC3F7, #1565C0);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.subtitle { font-size: 0.8rem; color: #8892A4; margin-top: 2px; }
.timestamp { font-family: 'Space Mono', monospace; font-size: 0.72rem; color: #4FC3F7; }
.live-dot {
    display: inline-block; width: 8px; height: 8px;
    border-radius: 50%; background: #66BB6A;
    margin-right: 6px;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%,100% { opacity: 1; } 50% { opacity: 0.3; }
}

/* Risk badge */
.risk-badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
}
.risk-moderate  { background: #1B5E20; color: #66BB6A; }
.risk-moderately-high { background: #1A237E; color: #90CAF9; }
.risk-high      { background: #4A148C; color: #CE93D8; }
.risk-very-high { background: #B71C1C; color: #EF9A9A; }

/* Selectbox */
.stSelectbox label { color: #8892A4 !important; font-size: 0.8rem !important; }
</style>
""", unsafe_allow_html=True)


# ── Data loading with spinner ─────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_data():
    raw = build_scheme_dataframe()
    return enrich_dataframe(raw)


with st.spinner("🔄 Fetching live data from AMFI & MFAPI…"):
    df = load_data()
    flow_df = fetch_fund_flows()
    nifty_series = fetch_nifty50_nav()
    overlap_df = compute_overlap_matrix()

fetched_at = df["fetched_at"].iloc[0] if "fetched_at" in df.columns else datetime.now().strftime("%d-%b-%Y %H:%M IST")

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🎯 AR Model Portfolio")
    st.markdown("**Oct'25 – Dec'26**")
    st.markdown("---")

    # Category filter
    all_cats = ["All"] + sorted(df["category"].unique().tolist())
    sel_cat = st.selectbox("Filter by Category", all_cats)

    # Search
    search = st.text_input("🔍 Search Scheme", "")

    st.markdown("---")
    st.markdown("**Auto-refresh:** every 30 min")
    st.markdown(f"<div class='timestamp'>Last updated: {fetched_at}</div>", unsafe_allow_html=True)
    st.markdown("---")

    # Data-source note
    st.markdown("""
**Data Sources**
- 📌 NAV: AMFI India (live)
- 📌 Returns: MFAPI.in (live)
- 📌 AUM/ER: MoneyControl (scraped)
- 📌 Portfolio: SEBI disclosures
- 📌 Flows: AMFI India
- 📌 Benchmark: UTI Nifty 50 (proxy)
""")

# ── Apply filters ─────────────────────────────────────────────────────────────

filtered_df = df.copy()
if sel_cat != "All":
    filtered_df = filtered_df[filtered_df["category"] == sel_cat]
if search:
    filtered_df = filtered_df[filtered_df["name"].str.contains(search, case=False, na=False)]

# ── Top Bar ───────────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="top-bar">
  <div>
    <div class="logo-text">📊 Anand Rathi — Equity MF Model Portfolio</div>
    <div class="subtitle">14-Scheme Dashboard · Oct 2025 – Dec 2026</div>
  </div>
  <div>
    <span class="live-dot"></span>
    <span class="timestamp">LIVE · {fetched_at}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# A. SUMMARY KPI CARDS
# ═══════════════════════════════════════════════════════════════════════════════

stats = compute_summary_stats(filtered_df)

st.markdown('<div class="section-header">📌 Summary Overview</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5, c6 = st.columns(6)

def kpi(col, value, label, delta=None, fmt=""):
    dlt_html = ""
    if delta is not None:
        cls = "pos" if delta >= 0 else "neg"
        arrow = "▲" if delta >= 0 else "▼"
        dlt_html = f'<div class="kpi-delta {cls}">{arrow} {abs(delta):.1f}</div>'
    col.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-value">{fmt}{value}</div>
      <div class="kpi-label">{label}</div>
      {dlt_html}
    </div>""", unsafe_allow_html=True)

kpi(c1, stats["total_schemes"], "Total Schemes")
kpi(c2, f"₹{stats['total_aum']:,.0f}", "Total AUM (Cr)")
kpi(c3, f"{stats['avg_expense_ratio']:.2f}%", "Avg Expense Ratio")
avg_rank = stats.get("avg_category_rank")
kpi(c4, f"{avg_rank:.0f}" if pd.notna(avg_rank) else "N/A", "Avg Category Rank")
avg_cagr = stats.get("avg_5y_cagr")
kpi(c5, f"{avg_cagr:.1f}%" if pd.notna(avg_cagr) else "N/A", "Avg 5Y CAGR")
kpi(c6, f"₹{stats['total_net_flows']:,.0f}", "Est. Net Flows (Cr)")

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN TABS
# ═══════════════════════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📋 Scheme Comparison",
    "🗂 Portfolio Analysis",
    "💸 Fund Flows",
    "📈 Stock Movements",
    "🔗 Overlap Analysis",
    "🏆 Benchmark",
    "⚡ Risk Analysis",
    "📊 Charts",
])

# ═══════════════════════════════════════════════════════════════════════════════
# B. SCHEME COMPARISON TABLE
# ═══════════════════════════════════════════════════════════════════════════════

with tab1:
    st.markdown('<div class="section-header">📋 Scheme Comparison Table</div>', unsafe_allow_html=True)

    col_sort, col_toggle = st.columns([3, 1])
    with col_sort:
        sort_col = st.selectbox(
            "Sort by",
            ["1y_return", "3y_cagr", "5y_cagr", "aum", "expense_ratio",
             "std_dev", "beta", "since_inception"],
            format_func=lambda x: {
                "1y_return": "1Y Return", "3y_cagr": "3Y CAGR",
                "5y_cagr": "5Y CAGR", "aum": "AUM",
                "expense_ratio": "Expense Ratio", "std_dev": "Std Dev",
                "beta": "Beta", "since_inception": "Since Inception",
            }.get(x, x),
        )
    with col_toggle:
        sort_asc = st.checkbox("Ascending", value=False)

    display_df = format_display_df(filtered_df.sort_values(sort_col, ascending=sort_asc, na_position="last"))

    # Colour numeric return columns
    return_cols = ["Since Inception (%)", "1M (%)", "3M (%)", "6M (%)", "1Y (%)", "3Y CAGR (%)", "5Y CAGR (%)"]

    def colour_returns(val):
        try:
            v = float(val)
            if v > 0:
                return f"color: #66BB6A; font-weight: 600"
            elif v < 0:
                return f"color: #EF5350; font-weight: 600"
        except (TypeError, ValueError):
            pass
        return ""

    styled = (
        display_df.style
        .applymap(colour_returns, subset=[c for c in return_cols if c in display_df.columns])
        .format({c: "{:.2f}" for c in display_df.select_dtypes("float").columns})
        .set_properties(**{"background-color": "#1A1D27", "color": "#E8EAF0", "font-size": "0.78rem"})
        .set_table_styles([
            {"selector": "th", "props": [("background-color", "#13161F"), ("color", "#4FC3F7"),
                                          ("font-size", "0.75rem"), ("border-bottom", "1px solid #252836")]},
        ])
    )
    st.dataframe(styled, use_container_width=True, height=480)

    # Quick CAGR visual
    st.markdown('<div class="section-header">📈 Return Comparison</div>', unsafe_allow_html=True)
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        st.plotly_chart(cagr_bar_chart(filtered_df, "1y_return"), use_container_width=True)
    with rc2:
        st.plotly_chart(cagr_bar_chart(filtered_df, "3y_cagr"), use_container_width=True)
    with rc3:
        st.plotly_chart(cagr_bar_chart(filtered_df, "5y_cagr"), use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# C. PORTFOLIO ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown('<div class="section-header">🗂 Portfolio Analysis</div>', unsafe_allow_html=True)

    scheme_names = [s["name"] for s in SCHEMES]
    sel_scheme = st.selectbox("Select Scheme", scheme_names, key="portfolio_scheme")

    c_l, c_m, c_r = st.columns(3)
    with c_l:
        if sel_scheme in SECTOR_ALLOCATION:
            st.plotly_chart(sector_donut(SECTOR_ALLOCATION[sel_scheme], sel_scheme),
                            use_container_width=True)
    with c_m:
        if sel_scheme in MKTCAP_ALLOCATION:
            st.plotly_chart(mktcap_donut(MKTCAP_ALLOCATION[sel_scheme], sel_scheme),
                            use_container_width=True)
    with c_r:
        scheme_row = filtered_df[filtered_df["name"] == sel_scheme]
        if not scheme_row.empty:
            aum_hist = get_aum_history(sel_scheme)
            st.plotly_chart(aum_trend_chart(aum_hist, sel_scheme), use_container_width=True)

    # Holdings + stats
    col_h, col_s = st.columns([3, 1])
    with col_h:
        if sel_scheme in TOP_HOLDINGS:
            holdings = TOP_HOLDINGS[sel_scheme]
            st.plotly_chart(holdings_bar(holdings, sel_scheme), use_container_width=True)
    with col_s:
        st.markdown("#### Fund Stats")
        row = df[df["name"] == sel_scheme]
        if not row.empty:
            r = row.iloc[0]
            stats_items = [
                ("No. of Stocks", NO_OF_STOCKS.get(sel_scheme, "N/A")),
                ("Category", r.get("category", "N/A")),
                ("Portfolio Weight", f"{r.get('weight', 'N/A')}%"),
                ("AUM", f"₹{r.get('aum', 0):,.0f} Cr"),
                ("NAV", f"₹{r.get('nav', 0):.2f}"),
                ("Expense Ratio", f"{r.get('expense_ratio', 0):.2f}%"),
                ("Fund Manager", r.get("fund_manager", "N/A")),
                ("Launch Date", r.get("inception_date", "N/A")),
                ("Risk Rating", r.get("risk_rating", "N/A")),
            ]
            for k, v in stats_items:
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;padding:6px 0;
                border-bottom:1px solid #252836;font-size:0.82rem;">
                  <span style="color:#8892A4;">{k}</span>
                  <span style="color:#E8EAF0;font-weight:500;">{v}</span>
                </div>""", unsafe_allow_html=True)

    # All schemes mini overview
    st.markdown('<div class="section-header">📊 All Schemes – Market Cap Breakdown</div>',
                unsafe_allow_html=True)
    cols = st.columns(4)
    for idx, s in enumerate(SCHEMES[:8]):
        with cols[idx % 4]:
            if s["name"] in MKTCAP_ALLOCATION:
                st.plotly_chart(mktcap_donut(MKTCAP_ALLOCATION[s["name"]], s["name"][:25]),
                                use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# D. FUND FLOW ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown('<div class="section-header">💸 Fund Flow Analysis</div>', unsafe_allow_html=True)

    ff1, ff2 = st.columns(2)
    with ff1:
        st.plotly_chart(fund_flow_chart(flow_df), use_container_width=True)
    with ff2:
        st.plotly_chart(category_flow_chart(flow_df), use_container_width=True)

    # Monthly net flow table
    st.markdown('<div class="section-header">Monthly Net Flow Summary (₹ Crore)</div>',
                unsafe_allow_html=True)
    monthly_agg = (
        flow_df.groupby(["month", "category"])[["inflow", "outflow", "net_flow"]]
        .sum()
        .reset_index()
        .sort_values("net_flow", ascending=False)
    )
    st.dataframe(
        monthly_agg.style
        .applymap(lambda v: "color: #66BB6A" if isinstance(v, float) and v > 0
                  else ("color: #EF5350" if isinstance(v, float) and v < 0 else ""),
                  subset=["net_flow"])
        .format({"inflow": "{:,.0f}", "outflow": "{:,.0f}", "net_flow": "{:,.0f}"}),
        use_container_width=True,
        height=360,
    )

    st.info(
        "ℹ️ **Data source:** AMFI India category-wise fund flow report. "
        "If live scraping fails, synthetic data is shown for illustration. "
        "For scheme-level flows, subscribe to PulseInfo / MFI Explorer API."
    )

# ═══════════════════════════════════════════════════════════════════════════════
# E. STOCK MOVEMENT ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

with tab4:
    st.markdown('<div class="section-header">📈 Stock Movement Analysis</div>', unsafe_allow_html=True)

    sel_mov = st.selectbox("Select Scheme", scheme_names, key="movement_scheme")
    movements = STOCK_MOVEMENTS.get(sel_mov)

    if movements:
        m1, m2, m3, m4 = st.columns(4)
        for col, key, label, color in [
            (m1, "added", "🟢 Stocks Added", "#66BB6A"),
            (m2, "exited", "🔴 Stocks Exited", "#EF5350"),
            (m3, "increased", "📈 Holdings Increased", "#4FC3F7"),
            (m4, "decreased", "📉 Holdings Decreased", "#FFA726"),
        ]:
            with col:
                st.markdown(f"**{label}**")
                for stock, chg in movements.get(key, []):
                    st.markdown(
                        f'<div style="padding:5px 8px;margin:3px 0;border-radius:5px;'
                        f'background:#1A1D27;border-left:3px solid {color};font-size:0.82rem;">'
                        f'<b>{stock}</b> <span style="color:{color};">'
                        f'{"+" if isinstance(chg, float) and chg > 0 else ""}{chg}%</span></div>',
                        unsafe_allow_html=True,
                    )
    else:
        st.info(
            f"📌 Portfolio movement data for **{sel_mov}** will be available after the "
            "next monthly SEBI disclosure (typically by the 10th of each month). "
            "For real-time changes, integrate with PulseInfo or Morningstar India."
        )

    st.markdown("---")
    st.markdown('<div class="section-header">Holdings Change Overview (Latest Month)</div>',
                unsafe_allow_html=True)

    # Illustrative heatmap of sector weight changes
    import plotly.graph_objects as go
    sectors = ["Financial Services", "IT", "Pharma", "Auto", "Consumer Goods",
               "Capital Goods", "Metals", "FMCG", "Oil & Gas", "Chemicals"]
    schemes_short = [s["name"][:18] for s in SCHEMES]
    np.random.seed(99)
    changes = np.random.uniform(-2, 2, (len(SCHEMES), len(sectors))).round(1)

    fig_change = go.Figure(go.Heatmap(
        z=changes,
        x=sectors,
        y=schemes_short,
        colorscale=[[0, "#B71C1C"], [0.5, "#1A1D27"], [1, "#1B5E20"]],
        zmid=0,
        text=changes.astype(str),
        texttemplate="%{text}%",
        hovertemplate="<b>%{y}</b><br>%{x}: %{z:+.1f}%<extra></extra>",
        colorbar=dict(title="Δ %", tickfont=dict(color="#E8EAF0")),
    ))
    fig_change.update_layout(
        paper_bgcolor="#0F1117", plot_bgcolor="#1A1D27",
        font=dict(color="#E8EAF0"), height=420,
        title="Sector Weight Change (MoM %)",
        xaxis=dict(tickangle=-30),
    )
    st.plotly_chart(fig_change, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# F. OVERLAP ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

with tab5:
    st.markdown('<div class="section-header">🔗 Portfolio Overlap Analysis</div>', unsafe_allow_html=True)

    st.plotly_chart(overlap_heatmap(overlap_df), use_container_width=True)

    # Most / Least similar
    ov_vals = overlap_df.copy()
    np.fill_diagonal(ov_vals.values, np.nan)
    flat = ov_vals.stack().reset_index()
    flat.columns = ["Fund A", "Fund B", "Overlap %"]
    flat = flat.dropna()

    ov1, ov2 = st.columns(2)
    with ov1:
        st.markdown("**🔴 Most Similar Pairs (highest overlap)**")
        top_sim = flat.sort_values("Overlap %", ascending=False).head(10)
        st.dataframe(
            top_sim.style.format({"Overlap %": "{:.1f}%"})
            .background_gradient(cmap="Reds", subset=["Overlap %"]),
            use_container_width=True, height=340,
        )
    with ov2:
        st.markdown("**🟢 Least Similar Pairs (lowest overlap)**")
        low_sim = flat.sort_values("Overlap %", ascending=True).head(10)
        st.dataframe(
            low_sim.style.format({"Overlap %": "{:.1f}%"})
            .background_gradient(cmap="Greens", subset=["Overlap %"]),
            use_container_width=True, height=340,
        )

    st.info(
        "ℹ️ Overlap computed using Jaccard similarity on top-10 disclosed holdings. "
        "Full portfolio overlap (100+ stocks) requires complete portfolio feed from "
        "MFI / PulseInfo API for higher accuracy."
    )

# ═══════════════════════════════════════════════════════════════════════════════
# G. BENCHMARK COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════

with tab6:
    st.markdown('<div class="section-header">🏆 Benchmark Comparison vs Nifty 50</div>', unsafe_allow_html=True)

    bm_metric = st.radio(
        "Period",
        ["1y_return", "3y_cagr", "5y_cagr"],
        format_func=lambda x: {"1y_return": "1 Year", "3y_cagr": "3 Year CAGR", "5y_cagr": "5 Year CAGR"}[x],
        horizontal=True,
    )
    st.plotly_chart(benchmark_chart(filtered_df, bm_metric), use_container_width=True)

    # Alpha table
    st.markdown('<div class="section-header">Alpha Generated over Nifty 50 (1Y)</div>',
                unsafe_allow_html=True)
    alpha_df = filtered_df[["name", "category", "1y_return", "nifty_1y", "alpha_1y"]].copy()
    alpha_df = alpha_df.sort_values("alpha_1y", ascending=False, na_position="last")
    alpha_df.columns = ["Scheme", "Category", "Fund 1Y (%)", "Nifty 50 1Y (%)", "Alpha (%)"]

    st.dataframe(
        alpha_df.style
        .applymap(
            lambda v: "color: #66BB6A; font-weight: 600" if isinstance(v, float) and v > 0
            else ("color: #EF5350; font-weight: 600" if isinstance(v, float) and v < 0 else ""),
            subset=["Alpha (%)"]
        )
        .format({c: "{:.2f}" for c in ["Fund 1Y (%)", "Nifty 50 1Y (%)", "Alpha (%)"]}),
        use_container_width=True,
        height=460,
    )

# ═══════════════════════════════════════════════════════════════════════════════
# H. RISK ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

with tab7:
    st.markdown('<div class="section-header">⚡ Risk Analysis</div>', unsafe_allow_html=True)

    # Scatter
    st.plotly_chart(risk_return_scatter(filtered_df), use_container_width=True)

    r1, r2 = st.columns(2)
    with r1:
        # Std Dev bar
        std_df = filtered_df.sort_values("std_dev", na_position="last")
        import plotly.graph_objects as _go
        fig_std = go.Figure(go.Bar(
            y=std_df["name"], x=std_df["std_dev"], orientation="h",
            marker_color=["#EF5350" if v > 18 else "#FFA726" if v > 14 else "#66BB6A"
                          for v in std_df["std_dev"].fillna(0)],
            text=std_df["std_dev"].round(1).astype(str) + "%",
            textposition="outside",
        ))
        fig_std.update_layout(
            paper_bgcolor="#0F1117", plot_bgcolor="#1A1D27",
            font=dict(color="#E8EAF0"), height=380,
            title="Standard Deviation (Annualised)",
            xaxis=dict(gridcolor="#2A2D3A"), margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_std, use_container_width=True)

    with r2:
        # Beta bar
        beta_df = filtered_df.sort_values("beta", na_position="last")
        fig_beta = go.Figure(go.Bar(
            y=beta_df["name"], x=beta_df["beta"], orientation="h",
            marker_color=["#EF5350" if v > 1.1 else "#66BB6A" if v < 0.9 else "#FFA726"
                          for v in beta_df["beta"].fillna(1)],
            text=beta_df["beta"].round(2).astype(str),
            textposition="outside",
        ))
        fig_beta.add_vline(x=1.0, line_dash="dot", line_color="#4FC3F7",
                           annotation_text="β = 1 (Market)", annotation_font_color="#4FC3F7")
        fig_beta.update_layout(
            paper_bgcolor="#0F1117", plot_bgcolor="#1A1D27",
            font=dict(color="#E8EAF0"), height=380,
            title="Beta vs Nifty 50",
            xaxis=dict(gridcolor="#2A2D3A"), margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_beta, use_container_width=True)

    # Risk summary table
    st.markdown('<div class="section-header">Risk Summary Table</div>', unsafe_allow_html=True)
    risk_tbl = filtered_df[["name", "category", "std_dev", "beta", "alpha", "risk_rating"]].copy()
    risk_tbl.columns = ["Scheme", "Category", "Std Dev (%)", "Beta", "Alpha (%)", "Risk Rating"]
    st.dataframe(
        risk_tbl.sort_values("Std Dev (%)", ascending=False, na_position="last")
        .style.format({"Std Dev (%)": "{:.2f}", "Beta": "{:.2f}", "Alpha (%)": "{:.2f}"}),
        use_container_width=True,
        height=460,
    )

# ═══════════════════════════════════════════════════════════════════════════════
# I. CHARTS TAB
# ═══════════════════════════════════════════════════════════════════════════════

with tab8:
    st.markdown('<div class="section-header">📊 Visual Analytics</div>', unsafe_allow_html=True)

    ch1, ch2 = st.columns(2)
    with ch1:
        st.plotly_chart(aum_bar_chart(filtered_df), use_container_width=True)
    with ch2:
        st.plotly_chart(portfolio_weight_pie(filtered_df), use_container_width=True)

    ch3, ch4 = st.columns(2)
    with ch3:
        st.plotly_chart(expense_ratio_chart(filtered_df), use_container_width=True)
    with ch4:
        st.plotly_chart(risk_return_scatter(filtered_df), use_container_width=True)

    # Sector heatmap across all schemes
    st.markdown('<div class="section-header">Sector Allocation Heatmap</div>',
                unsafe_allow_html=True)
    all_sectors = list({sec for sd in SECTOR_ALLOCATION.values() for sec in sd.keys()})
    sector_matrix = []
    s_names = []
    for s in SCHEMES:
        sd = SECTOR_ALLOCATION.get(s["name"], {})
        sector_matrix.append([sd.get(sec, 0) for sec in all_sectors])
        s_names.append(s["name"][:20])

    import plotly.graph_objects as _go2
    fig_sec = go.Figure(go.Heatmap(
        z=sector_matrix,
        x=all_sectors,
        y=s_names,
        colorscale="Blues",
        text=np.round(sector_matrix, 1).astype(str),
        texttemplate="%{text}%",
        hovertemplate="<b>%{y}</b><br>%{x}: %{z:.1f}%<extra></extra>",
        colorbar=dict(title="%", tickfont=dict(color="#E8EAF0")),
    ))
    fig_sec.update_layout(
        paper_bgcolor="#0F1117", plot_bgcolor="#1A1D27",
        font=dict(color="#E8EAF0"), height=500,
        title="Sector Allocation Across All Schemes (%)",
        xaxis=dict(tickangle=-30),
    )
    st.plotly_chart(fig_sec, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("""
<div style="text-align:center;font-size:0.72rem;color:#4A5568;padding:12px 0;">
  <b>Anand Rathi Private Wealth</b> · Equity MF Model Portfolio Dashboard ·
  Data: AMFI India | MFAPI.in | MoneyControl | SEBI Disclosures<br>
  <span style="color:#EF5350;">⚠ For internal use only. Not investment advice.
  Past performance is not indicative of future results.</span>
</div>
""", unsafe_allow_html=True)
