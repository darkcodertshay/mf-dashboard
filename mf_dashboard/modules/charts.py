"""
charts.py
All Plotly chart-building functions used by the dashboard.
Each function returns a plotly Figure object.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from modules.scheme_config import CATEGORY_COLORS

# ── Palette ───────────────────────────────────────────────────────────────────

BG = "#0F1117"
CARD_BG = "#1A1D27"
GRID = "#2A2D3A"
TEXT = "#E8EAF0"
ACCENT = "#4FC3F7"
GREEN = "#66BB6A"
RED = "#EF5350"
AMBER = "#FFA726"

BASE_LAYOUT = dict(
    paper_bgcolor=BG,
    plot_bgcolor=CARD_BG,
    font=dict(color=TEXT, family="Inter, sans-serif"),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
)


def _layout(**kwargs):
    d = dict(**BASE_LAYOUT)
    d.update(kwargs)
    return d


# ── CAGR Comparison Bar ───────────────────────────────────────────────────────

def cagr_bar_chart(df: pd.DataFrame, metric: str = "1y_return") -> go.Figure:
    label_map = {
        "1y_return": "1-Year Return (%)",
        "3y_cagr": "3-Year CAGR (%)",
        "5y_cagr": "5-Year CAGR (%)",
    }
    sorted_df = df.sort_values(metric, ascending=False)
    colors = [GREEN if v > 0 else RED for v in sorted_df[metric].fillna(0)]
    fig = go.Figure(go.Bar(
        x=sorted_df["name"],
        y=sorted_df[metric],
        marker_color=colors,
        text=sorted_df[metric].round(1).astype(str) + "%",
        textposition="outside",
    ))
    fig.update_layout(
        **_layout(title=label_map.get(metric, metric), height=380),
        xaxis=dict(tickangle=-30, gridcolor=GRID),
        yaxis=dict(gridcolor=GRID, zeroline=True, zerolinecolor=GRID),
    )
    return fig


# ── AUM Bar Chart ─────────────────────────────────────────────────────────────

def aum_bar_chart(df: pd.DataFrame) -> go.Figure:
    sorted_df = df.sort_values("aum", ascending=True)
    fig = go.Figure(go.Bar(
        y=sorted_df["name"],
        x=sorted_df["aum"],
        orientation="h",
        marker_color=ACCENT,
        text=("₹" + (sorted_df["aum"] / 100).round(0).astype(int).astype(str) + "B"),
        textposition="outside",
    ))
    fig.update_layout(
        **_layout(title="AUM (₹ Crore)", height=420),
        xaxis=dict(gridcolor=GRID, title="₹ Crore"),
        yaxis=dict(gridcolor=GRID),
    )
    return fig


# ── Risk-Return Scatter ───────────────────────────────────────────────────────

def risk_return_scatter(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for cat, grp in df.groupby("category"):
        fig.add_trace(go.Scatter(
            x=grp["std_dev"],
            y=grp["1y_return"],
            mode="markers+text",
            name=cat,
            text=grp["name"].str.split().str[0],
            textposition="top center",
            marker=dict(
                size=grp["aum"].fillna(1000) / 3000 + 8,
                color=CATEGORY_COLORS.get(cat, ACCENT),
                line=dict(color="white", width=1),
                opacity=0.85,
            ),
        ))
    fig.update_layout(
        **_layout(title="Risk vs Return (bubble size = AUM)", height=420),
        xaxis=dict(title="Annualised Std Dev (%)", gridcolor=GRID),
        yaxis=dict(title="1-Year Return (%)", gridcolor=GRID),
    )
    return fig


# ── Overlap Heatmap ───────────────────────────────────────────────────────────

def overlap_heatmap(overlap_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=overlap_df.values,
        x=overlap_df.columns.tolist(),
        y=overlap_df.index.tolist(),
        colorscale=[
            [0.0, "#0F1117"], [0.3, "#1A3A5C"], [0.6, "#1E88E5"], [1.0, "#E53935"],
        ],
        text=overlap_df.values.round(1).astype(str),
        texttemplate="%{text}%",
        hovertemplate="<b>%{y}</b> ↔ <b>%{x}</b><br>Overlap: %{z:.1f}%<extra></extra>",
        showscale=True,
        colorbar=dict(title="Overlap %", tickfont=dict(color=TEXT)),
    ))
    fig.update_layout(
        **_layout(title="Portfolio Overlap Matrix (%)", height=520),
        xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
        yaxis=dict(tickfont=dict(size=10)),
    )
    return fig


# ── Sector Donut ──────────────────────────────────────────────────────────────

def sector_donut(sector_data: dict, scheme_name: str) -> go.Figure:
    labels = list(sector_data.keys())
    values = list(sector_data.values())
    colors = px.colors.qualitative.Bold
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors),
        textinfo="label+percent",
        hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        **_layout(title=f"Sector Allocation – {scheme_name}", height=360),
        showlegend=False,
    )
    return fig


# ── Market Cap Donut ──────────────────────────────────────────────────────────

def mktcap_donut(mktcap_data: dict, scheme_name: str) -> go.Figure:
    labels = list(mktcap_data.keys())
    values = list(mktcap_data.values())
    colors = ["#1E88E5", "#FB8C00", "#E53935", "#66BB6A"]
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors),
        textinfo="label+percent",
        hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        **_layout(title=f"Market Cap – {scheme_name}", height=300),
        showlegend=True,
    )
    return fig


# ── Top Holdings Horizontal Bar ───────────────────────────────────────────────

def holdings_bar(holdings: list, scheme_name: str) -> go.Figure:
    stocks, pcts = zip(*holdings) if holdings else ([], [])
    fig = go.Figure(go.Bar(
        y=list(stocks),
        x=list(pcts),
        orientation="h",
        marker_color=ACCENT,
        text=[f"{p}%" for p in pcts],
        textposition="outside",
    ))
    fig.update_layout(
        **_layout(title=f"Top 10 Holdings – {scheme_name}", height=320),
        xaxis=dict(gridcolor=GRID, title="%"),
        yaxis=dict(autorange="reversed"),
    )
    return fig


# ── Fund Flow Bar ─────────────────────────────────────────────────────────────

def fund_flow_chart(flow_df: pd.DataFrame) -> go.Figure:
    monthly = flow_df.groupby("month")[["inflow", "outflow", "net_flow"]].sum().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Inflow", x=monthly["month"], y=monthly["inflow"],
                         marker_color=GREEN))
    fig.add_trace(go.Bar(name="Outflow", x=monthly["month"], y=monthly["outflow"],
                         marker_color=RED))
    fig.add_trace(go.Scatter(name="Net Flow", x=monthly["month"], y=monthly["net_flow"],
                             mode="lines+markers", marker_color=AMBER,
                             line=dict(width=2, dash="dot")))
    fig.update_layout(
        **_layout(title="Monthly Fund Flows (₹ Cr)", height=360),
        barmode="group",
        xaxis=dict(gridcolor=GRID),
        yaxis=dict(gridcolor=GRID, title="₹ Crore"),
    )
    return fig


# ── Category Net-Flow Bar ─────────────────────────────────────────────────────

def category_flow_chart(flow_df: pd.DataFrame) -> go.Figure:
    cat_flow = flow_df.groupby("category")["net_flow"].sum().sort_values()
    colors = [GREEN if v >= 0 else RED for v in cat_flow.values]
    fig = go.Figure(go.Bar(
        y=cat_flow.index.tolist(),
        x=cat_flow.values,
        orientation="h",
        marker_color=colors,
        text=[f"₹{abs(v):.0f} Cr" for v in cat_flow.values],
        textposition="outside",
    ))
    fig.update_layout(
        **_layout(title="Category-wise Net Flows (₹ Cr)", height=340),
        xaxis=dict(gridcolor=GRID, zeroline=True, zerolinecolor=GRID),
    )
    return fig


# ── Benchmark Comparison ──────────────────────────────────────────────────────

def benchmark_chart(df: pd.DataFrame, metric: str = "1y_return") -> go.Figure:
    label_map = {"1y_return": "1Y", "3y_cagr": "3Y CAGR", "5y_cagr": "5Y CAGR"}
    nifty_col = {"1y_return": "nifty_1y", "3y_cagr": "nifty_3y", "5y_cagr": "nifty_5y"}.get(metric)
    sorted_df = df.sort_values(metric, ascending=False)
    nifty_val = sorted_df[nifty_col].mean() if nifty_col and nifty_col in sorted_df else None

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=sorted_df["name"],
        y=sorted_df[metric],
        name="Fund",
        marker_color=ACCENT,
        text=sorted_df[metric].round(1).astype(str) + "%",
        textposition="outside",
    ))
    if nifty_val is not None:
        fig.add_hline(y=nifty_val, line_dash="dot", line_color=AMBER,
                      annotation_text=f"Nifty 50: {nifty_val:.1f}%",
                      annotation_font_color=AMBER)
    fig.update_layout(
        **_layout(title=f"{label_map.get(metric, metric)} vs Nifty 50", height=380),
        xaxis=dict(tickangle=-30, gridcolor=GRID),
        yaxis=dict(gridcolor=GRID),
    )
    return fig


# ── AUM Trend Line ────────────────────────────────────────────────────────────

def aum_trend_chart(aum_df: pd.DataFrame, scheme_name: str) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=aum_df["month"],
        y=aum_df["aum"],
        mode="lines+markers",
        fill="tozeroy",
        fillcolor=f"rgba(79,195,247,0.1)",
        line=dict(color=ACCENT, width=2),
        marker=dict(size=6),
    ))
    fig.update_layout(
        **_layout(title=f"AUM Trend – {scheme_name}", height=280),
        xaxis=dict(gridcolor=GRID),
        yaxis=dict(gridcolor=GRID, title="₹ Crore"),
    )
    return fig


# ── Expense Ratio Comparison ──────────────────────────────────────────────────

def expense_ratio_chart(df: pd.DataFrame) -> go.Figure:
    sorted_df = df.sort_values("expense_ratio")
    fig = go.Figure(go.Bar(
        x=sorted_df["name"],
        y=sorted_df["expense_ratio"],
        marker_color=[GREEN if v < 1.7 else AMBER if v < 2.0 else RED
                      for v in sorted_df["expense_ratio"].fillna(0)],
        text=sorted_df["expense_ratio"].round(2).astype(str) + "%",
        textposition="outside",
    ))
    fig.update_layout(
        **_layout(title="Expense Ratio Comparison (%)", height=360),
        xaxis=dict(tickangle=-30, gridcolor=GRID),
        yaxis=dict(gridcolor=GRID),
    )
    return fig


# ── Portfolio Weight Pie ──────────────────────────────────────────────────────

def portfolio_weight_pie(df: pd.DataFrame) -> go.Figure:
    colors = [CATEGORY_COLORS.get(c, ACCENT) for c in df["category"]]
    fig = go.Figure(go.Pie(
        labels=df["name"],
        values=df["weight"],
        hole=0.5,
        marker=dict(colors=colors),
        textinfo="label+percent",
        hovertemplate="%{label}: %{value}%<extra></extra>",
    ))
    fig.update_layout(
        **_layout(title="Portfolio Weight Allocation", height=380),
        showlegend=False,
    )
    return fig
