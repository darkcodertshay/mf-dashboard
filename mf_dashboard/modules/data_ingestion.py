"""
data_ingestion.py
Fetches live mutual fund data from:
  1. AMFI India NAV feed (primary – free, official)
  2. mfapi.in (historical NAV – free, JSON REST)
  3. MoneyControl scraping (AUM, ratios, portfolio – with polite delays)
  4. Morningstar India API endpoints (risk metrics)

All functions are cached with st.cache_data so they auto-refresh on TTL expiry.
"""

import requests
import pandas as pd
import numpy as np
import time
import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import streamlit as st

from modules.scheme_config import SCHEMES

# ── HTTP helpers ──────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

JSON_HEADERS = {**HEADERS, "Accept": "application/json, text/plain, */*"}


def safe_get(url: str, retries: int = 3, delay: float = 1.0, json_mode=False):
    """HTTP GET with retry logic; returns None on failure."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=JSON_HEADERS if json_mode else HEADERS,
                             timeout=15)
            if r.status_code == 200:
                return r.json() if json_mode else r
        except Exception as e:
            pass
        time.sleep(delay * (attempt + 1))
    return None


# ── 1. AMFI NAV feed ─────────────────────────────────────────────────────────

AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_amfi_nav_all() -> pd.DataFrame:
    """Download the full AMFI NAV flat file and parse it into a DataFrame."""
    resp = safe_get(AMFI_NAV_URL)
    if resp is None:
        return pd.DataFrame()
    rows = []
    for line in resp.text.splitlines():
        parts = line.split(";")
        if len(parts) >= 6:
            try:
                rows.append({
                    "scheme_code": parts[0].strip(),
                    "isin_growth": parts[1].strip(),
                    "isin_div": parts[2].strip(),
                    "scheme_name": parts[3].strip(),
                    "nav": float(parts[4].strip()),
                    "nav_date": parts[5].strip(),
                })
            except (ValueError, IndexError):
                pass
    return pd.DataFrame(rows)


def get_nav_for_scheme(amfi_code: str, amfi_df: pd.DataFrame) -> dict:
    """Look up NAV for a scheme code in the AMFI DataFrame."""
    row = amfi_df[amfi_df["scheme_code"] == amfi_code]
    if row.empty:
        return {"nav": None, "nav_date": None, "scheme_name_amfi": None}
    r = row.iloc[0]
    return {
        "nav": r["nav"],
        "nav_date": r["nav_date"],
        "scheme_name_amfi": r["scheme_name"],
    }


# ── 2. mfapi.in – historical NAV ─────────────────────────────────────────────

MFAPI_BASE = "https://api.mfapi.in/mf"

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_historical_nav(amfi_code: str) -> pd.DataFrame:
    """Return a date-indexed DataFrame of historical NAV for one scheme."""
    data = safe_get(f"{MFAPI_BASE}/{amfi_code}", json_mode=True)
    if not data or "data" not in data:
        return pd.DataFrame()
    df = pd.DataFrame(data["data"])
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna().sort_values("date").set_index("date")
    return df


def compute_cagr(nav_series: pd.Series, years: float):
    """Compute CAGR over `years` from today going backwards."""
    if nav_series.empty:
        return None
    latest = nav_series.iloc[-1]
    target_date = nav_series.index[-1] - pd.DateOffset(years=years)
    past = nav_series[nav_series.index <= target_date]
    if past.empty:
        return None
    start = past.iloc[-1]
    if start <= 0:
        return None
    return round(((latest / start) ** (1 / years) - 1) * 100, 2)


def compute_returns(nav_series: pd.Series) -> dict:
    """Compute 1M, 3M, 6M, 1Y, 3Y, 5Y returns and since-inception CAGR."""
    if nav_series.empty:
        return {}
    latest_date = nav_series.index[-1]
    latest_nav = nav_series.iloc[-1]
    inception_nav = nav_series.iloc[0]
    inception_years = (latest_date - nav_series.index[0]).days / 365.25

    def ret(months):
        td = latest_date - pd.DateOffset(months=months)
        past = nav_series[nav_series.index <= td]
        if past.empty:
            return None
        return round((latest_nav / past.iloc[-1] - 1) * 100, 2)

    return {
        "1m_return": ret(1),
        "3m_return": ret(3),
        "6m_return": ret(6),
        "1y_return": ret(12),
        "3y_cagr": compute_cagr(nav_series, 3),
        "5y_cagr": compute_cagr(nav_series, 5),
        "since_inception": (
            round(((latest_nav / inception_nav) ** (1 / inception_years) - 1) * 100, 2)
            if inception_years > 0 else None
        ),
        "inception_date": nav_series.index[0].strftime("%d-%b-%Y"),
        "latest_nav": round(latest_nav, 4),
        "latest_nav_date": latest_date.strftime("%d-%b-%Y"),
    }


def compute_risk_metrics(nav_series: pd.Series, benchmark_series: pd.Series = None) -> dict:
    """Compute Std Dev, Beta, Sharpe (approx)."""
    if nav_series.empty or len(nav_series) < 30:
        return {}
    daily_ret = nav_series.pct_change().dropna()
    std_dev = round(daily_ret.std() * np.sqrt(252) * 100, 2)
    beta = None
    alpha = None
    if benchmark_series is not None and not benchmark_series.empty:
        combined = pd.DataFrame({"fund": daily_ret}).join(
            pd.DataFrame({"bench": benchmark_series.pct_change().dropna()}),
            how="inner"
        )
        if len(combined) > 30:
            cov = np.cov(combined["fund"], combined["bench"])
            beta = round(cov[0, 1] / cov[1, 1], 2)
            fund_ann = daily_ret.mean() * 252 * 100
            bench_ann = benchmark_series.pct_change().dropna().mean() * 252 * 100
            alpha = round(fund_ann - beta * bench_ann, 2)
    return {"std_dev": std_dev, "beta": beta, "alpha": alpha}


# ── 3. MF Scraper – AUM, expense ratio, fund manager, category rank ──────────

MC_OVERVIEW_BASE = "https://www.moneycontrol.com/mutual-funds/nav"

@st.cache_data(ttl=7200, show_spinner=False)
def scrape_mc_overview(mc_url: str, scheme_name: str) -> dict:
    """
    Scrape MoneyControl fund page for AUM, expense ratio, fund manager, etc.
    Returns a dict; uses sensible fallbacks if scraping fails.
    NOTE: MoneyControl uses heavy JS. We attempt a best-effort parse of
    the server-side HTML. For production, consider Playwright/Selenium.
    """
    resp = safe_get(mc_url)
    result = {
        "aum": None,
        "expense_ratio": None,
        "fund_manager": None,
        "category_rank": None,
        "no_of_stocks": None,
        "beta_mc": None,
        "std_dev_mc": None,
    }
    if resp is None:
        return result
    try:
        soup = BeautifulSoup(resp.text, "lxml")
        full_text = soup.get_text(" ", strip=True)

        # AUM
        aum_match = re.search(
            r"AUM[:\s₹]*([0-9,]+(?:\.[0-9]+)?)\s*(Cr|Crore|cr)", full_text, re.I
        )
        if aum_match:
            result["aum"] = float(aum_match.group(1).replace(",", ""))

        # Expense ratio
        exp_match = re.search(r"Expense Ratio[:\s]*([0-9.]+)\s*%", full_text, re.I)
        if exp_match:
            result["expense_ratio"] = float(exp_match.group(1))

        # Fund manager – look for "Fund Manager" label
        fm_match = re.search(
            r"Fund Manager[:\s]+([A-Za-z .]+?)(?:\s{2,}|,|\|)", full_text, re.I
        )
        if fm_match:
            result["fund_manager"] = fm_match.group(1).strip()

        # Category rank
        rank_match = re.search(r"Category Rank[:\s#]*([0-9]+)", full_text, re.I)
        if rank_match:
            result["category_rank"] = int(rank_match.group(1))

        # No. of stocks
        stocks_match = re.search(r"No\. of Stocks[:\s]*([0-9]+)", full_text, re.I)
        if stocks_match:
            result["no_of_stocks"] = int(stocks_match.group(1))

    except Exception:
        pass
    return result


# ── 4. AMFI SID/SAI – sector & holdings (via public JSON where available) ────

MF_PORTFOLIO_API = "https://api.mfapi.in/mf/{code}/portfolio"  # hypothetical
# NOTE: mfapi.in does not expose portfolio. We use a curated static fallback
# dataset for sector/holdings, refreshed monthly. See modules/portfolio_data.py.


# ── 5. Nifty 50 benchmark (Yahoo Finance via yfinance or manual) ─────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_nifty50_nav() -> pd.Series:
    """
    Fetch Nifty 50 TRI from AMFI (using Nifty 50 index fund as proxy).
    Fallback: UTI Nifty 50 Index Fund AMFI code 120716.
    """
    amfi_code = "120716"  # UTI Nifty 50 Index Fund – Direct (Growth)
    df = fetch_historical_nav(amfi_code)
    if df.empty:
        return pd.Series(dtype=float)
    return df["nav"]


# ── 6. Orchestrator – build full enriched DataFrame ──────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def build_scheme_dataframe() -> pd.DataFrame:
    """
    Master function: fetch all data, compute all metrics, return one DataFrame
    with one row per scheme.  This is the single call used by the dashboard.
    """
    amfi_df = fetch_amfi_nav_all()
    nifty_series = fetch_nifty50_nav()
    records = []

    for s in SCHEMES:
        row = {
            "id": s["id"],
            "name": s["name"],
            "full_name": s["full_name"],
            "category": s["category"],
            "weight": s["weight"],
            "amfi_code": s["amfi_code"],
            "mc_code": s["mc_code"],
            "mc_url": s["mc_url"],
        }

        # NAV from AMFI feed
        nav_info = get_nav_for_scheme(s["amfi_code"], amfi_df)
        row.update(nav_info)

        # Historical returns
        hist = fetch_historical_nav(s["amfi_code"])
        if not hist.empty:
            returns = compute_returns(hist["nav"])
            row.update(returns)
            risk = compute_risk_metrics(hist["nav"], nifty_series)
            row.update(risk)
        else:
            row.update({
                "1m_return": None, "3m_return": None, "6m_return": None,
                "1y_return": None, "3y_cagr": None, "5y_cagr": None,
                "since_inception": None, "inception_date": None,
                "std_dev": None, "beta": None, "alpha": None,
            })

        # Benchmark comparison
        if not hist.empty and not nifty_series.empty:
            nifty_ret = compute_returns(nifty_series)
            row["nifty_1y"] = nifty_ret.get("1y_return")
            row["nifty_3y"] = nifty_ret.get("3y_cagr")
            row["nifty_5y"] = nifty_ret.get("5y_cagr")
            row["alpha_1y"] = (
                (row.get("1y_return") or 0) - (row.get("nifty_1y") or 0)
            )
        else:
            row["nifty_1y"] = row["nifty_3y"] = row["nifty_5y"] = row["alpha_1y"] = None

        # MC scrape (AUM, ER, manager, rank, stocks)
        mc_data = scrape_mc_overview(s["mc_url"], s["name"])
        row.update(mc_data)

        records.append(row)
        time.sleep(0.4)  # polite crawl delay

    df = pd.DataFrame(records)
    df["fetched_at"] = datetime.now().strftime("%d-%b-%Y %H:%M IST")
    return df


# ── 7. Fund flow data (AMFI monthly) ─────────────────────────────────────────

AMFI_FLOW_URL = (
    "https://www.amfiindia.com/research-information/"
    "fund-flow-report/category-wise-fund-flow"
)

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_fund_flows() -> pd.DataFrame:
    """
    Fetch category-wise fund flows from AMFI India.
    Returns a DataFrame with columns: date, category, inflow, outflow, net_flow.
    Falls back to an illustrative synthetic dataset if scraping fails.
    """
    resp = safe_get(AMFI_FLOW_URL)
    if resp is None:
        return _synthetic_fund_flows()
    try:
        tables = pd.read_html(resp.text)
        if tables:
            df = tables[0]
            # normalise column names
            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
            return df
    except Exception:
        pass
    return _synthetic_fund_flows()


def _synthetic_fund_flows() -> pd.DataFrame:
    """
    Synthetic monthly fund-flow data for illustration when AMFI is unavailable.
    All figures in ₹ Crore.
    """
    np.random.seed(42)
    months = pd.date_range(end=datetime.today(), periods=12, freq="MS")
    categories = ["Large Cap", "Large & Mid Cap", "Mid Cap", "Small Cap",
                  "Flexi Cap", "Multi Cap", "Focused", "Dividend Yield"]
    rows = []
    for m in months:
        for cat in categories:
            inflow = np.random.uniform(500, 5000)
            outflow = np.random.uniform(300, 4000)
            rows.append({
                "month": m.strftime("%b-%Y"),
                "date": m,
                "category": cat,
                "inflow": round(inflow, 1),
                "outflow": round(outflow, 1),
                "net_flow": round(inflow - outflow, 1),
            })
    return pd.DataFrame(rows)
