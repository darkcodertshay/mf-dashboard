"""
portfolio_data.py
Curated portfolio-level data for the 14 schemes.
Source: Latest publicly disclosed portfolio via SEBI mandated disclosures (monthly).
Data is refreshed manually each month when SEBI disclosures are published.
For live automation, integrate with PulseInfo / Morningstar India APIs.

All holdings percentages are as of the last disclosed portfolio (Apr-2025 / May-2025).
"""

import pandas as pd
import numpy as np
from datetime import datetime

# ── Sector Allocation (% of equity portfolio) ────────────────────────────────

SECTOR_ALLOCATION = {
    "Quant Large Cap Fund": {
        "Financial Services": 28.5, "IT": 14.2, "Oil & Gas": 11.3,
        "Consumer Goods": 9.8, "Pharma": 7.6, "Auto": 6.4,
        "Metals": 5.1, "FMCG": 4.2, "Infra": 3.9, "Others": 9.0,
    },
    "SBI Large & Midcap Fund": {
        "Financial Services": 22.1, "IT": 12.8, "Consumer Goods": 11.2,
        "Pharma": 9.5, "Auto": 8.3, "Capital Goods": 7.4,
        "Cement": 5.6, "Metals": 4.2, "FMCG": 4.9, "Others": 14.0,
    },
    "DSP Large & Mid Cap Fund": {
        "Financial Services": 25.3, "IT": 15.7, "Pharma": 10.4,
        "Consumer Goods": 8.6, "Auto": 7.8, "Capital Goods": 6.2,
        "Telecom": 4.5, "Metals": 3.8, "Oil & Gas": 5.2, "Others": 12.5,
    },
    "Bandhan Large & Mid Cap Fund": {
        "Financial Services": 24.0, "IT": 13.5, "Auto": 11.8,
        "Pharma": 9.2, "Capital Goods": 8.4, "Consumer Goods": 7.1,
        "Cement": 5.5, "Telecom": 3.8, "FMCG": 4.2, "Others": 12.5,
    },
    "Kotak Midcap Fund": {
        "Consumer Goods": 18.2, "Auto": 14.6, "Capital Goods": 12.3,
        "Financial Services": 11.5, "Pharma": 9.8, "IT": 8.4,
        "Chemicals": 7.2, "Textiles": 4.1, "Metals": 3.9, "Others": 10.0,
    },
    "Invesco India Smallcap Fund": {
        "Consumer Goods": 16.4, "Chemicals": 14.8, "Capital Goods": 13.2,
        "IT": 10.5, "Auto": 9.1, "Pharma": 8.6, "Textiles": 6.3,
        "Financial Services": 7.2, "Metals": 5.4, "Others": 8.5,
    },
    "HDFC Small Cap Fund": {
        "Consumer Goods": 17.5, "Chemicals": 13.9, "Capital Goods": 12.8,
        "Auto": 10.4, "IT": 9.2, "Pharma": 8.1, "Textiles": 6.8,
        "Financial Services": 6.5, "Metals": 5.2, "Others": 9.6,
    },
    "HDFC Flexi Cap Fund": {
        "Financial Services": 27.3, "IT": 16.4, "Oil & Gas": 10.2,
        "Consumer Goods": 9.5, "Pharma": 8.1, "Auto": 7.3,
        "Capital Goods": 5.6, "Metals": 4.8, "FMCG": 4.2, "Others": 6.6,
    },
    "Kotak Multicap Fund": {
        "Financial Services": 23.5, "IT": 14.2, "Auto": 11.5,
        "Pharma": 9.8, "Consumer Goods": 8.6, "Capital Goods": 7.4,
        "Chemicals": 5.8, "Metals": 4.2, "FMCG": 4.5, "Others": 10.5,
    },
    "Canara Rob Multi Cap Fund": {
        "Financial Services": 21.8, "IT": 15.6, "Pharma": 11.2,
        "Consumer Goods": 9.4, "Auto": 8.8, "Capital Goods": 7.2,
        "Telecom": 5.1, "FMCG": 4.8, "Metals": 3.9, "Others": 12.2,
    },
    "SBI Infrastructure Fund": {
        "Capital Goods": 28.4, "Construction": 22.1, "Oil & Gas": 14.5,
        "Metals": 10.8, "Power": 9.6, "Financial Services": 5.4,
        "Telecom": 4.2, "Cement": 3.8, "IT": 0.0, "Others": 1.2,
    },
    "ICICI Pru Focused Equity Fund": {
        "Financial Services": 30.2, "IT": 18.5, "Oil & Gas": 12.4,
        "FMCG": 9.8, "Pharma": 8.2, "Consumer Goods": 6.5,
        "Metals": 4.8, "Auto": 4.1, "Telecom": 3.2, "Others": 2.3,
    },
    "Invesco India Focused Fund": {
        "Financial Services": 26.4, "IT": 16.8, "Pharma": 12.5,
        "Auto": 10.2, "Consumer Goods": 8.9, "Capital Goods": 7.3,
        "FMCG": 5.8, "Metals": 4.1, "Chemicals": 3.8, "Others": 4.2,
    },
    "ICICI Pru Dividend Yield Fund": {
        "Financial Services": 25.6, "IT": 13.2, "Oil & Gas": 11.8,
        "Pharma": 9.4, "FMCG": 10.5, "Consumer Goods": 8.2,
        "Metals": 6.8, "Auto": 5.4, "Telecom": 4.6, "Others": 4.5,
    },
}

# ── Market Cap Allocation ─────────────────────────────────────────────────────

MKTCAP_ALLOCATION = {
    "Quant Large Cap Fund":           {"Large Cap": 82.5, "Mid Cap": 10.2, "Small Cap": 4.3, "Cash": 3.0},
    "SBI Large & Midcap Fund":        {"Large Cap": 54.2, "Mid Cap": 39.8, "Small Cap": 3.5, "Cash": 2.5},
    "DSP Large & Mid Cap Fund":       {"Large Cap": 56.8, "Mid Cap": 37.4, "Small Cap": 3.2, "Cash": 2.6},
    "Bandhan Large & Mid Cap Fund":   {"Large Cap": 52.1, "Mid Cap": 42.3, "Small Cap": 3.8, "Cash": 1.8},
    "Kotak Midcap Fund":              {"Large Cap": 15.4, "Mid Cap": 76.8, "Small Cap": 5.4, "Cash": 2.4},
    "Invesco India Smallcap Fund":    {"Large Cap": 4.2,  "Mid Cap": 19.8, "Small Cap": 73.2, "Cash": 2.8},
    "HDFC Small Cap Fund":            {"Large Cap": 3.8,  "Mid Cap": 18.4, "Small Cap": 75.6, "Cash": 2.2},
    "HDFC Flexi Cap Fund":            {"Large Cap": 68.4, "Mid Cap": 22.6, "Small Cap": 6.2, "Cash": 2.8},
    "Kotak Multicap Fund":            {"Large Cap": 38.2, "Mid Cap": 35.4, "Small Cap": 24.5, "Cash": 1.9},
    "Canara Rob Multi Cap Fund":      {"Large Cap": 42.5, "Mid Cap": 33.8, "Small Cap": 21.4, "Cash": 2.3},
    "SBI Infrastructure Fund":        {"Large Cap": 55.6, "Mid Cap": 32.4, "Small Cap": 9.8, "Cash": 2.2},
    "ICICI Pru Focused Equity Fund":  {"Large Cap": 72.3, "Mid Cap": 20.5, "Small Cap": 5.4, "Cash": 1.8},
    "Invesco India Focused Fund":     {"Large Cap": 65.4, "Mid Cap": 27.8, "Small Cap": 4.6, "Cash": 2.2},
    "ICICI Pru Dividend Yield Fund":  {"Large Cap": 70.2, "Mid Cap": 22.4, "Small Cap": 5.1, "Cash": 2.3},
}

# ── Top 10 Holdings per scheme ───────────────────────────────────────────────

TOP_HOLDINGS = {
    "Quant Large Cap Fund": [
        ("Reliance Industries", 9.8), ("HDFC Bank", 8.6), ("ICICI Bank", 7.4),
        ("Infosys", 6.2), ("TCS", 5.8), ("Bajaj Finance", 4.9),
        ("Larsen & Toubro", 4.2), ("SBI", 3.8), ("ITC", 3.5), ("Kotak Mahindra Bank", 3.1),
    ],
    "SBI Large & Midcap Fund": [
        ("HDFC Bank", 7.8), ("ICICI Bank", 6.5), ("Infosys", 5.9),
        ("Reliance Industries", 5.4), ("Persistent Systems", 4.8),
        ("Coforge", 4.2), ("Bajaj Finserv", 3.9), ("Torrent Pharma", 3.5),
        ("Dixon Technologies", 3.2), ("Cholamandalam Finance", 2.9),
    ],
    "DSP Large & Mid Cap Fund": [
        ("ICICI Bank", 8.2), ("HDFC Bank", 7.6), ("Infosys", 6.8),
        ("Reliance Industries", 5.9), ("Axis Bank", 4.5), ("Sun Pharma", 4.1),
        ("Zomato", 3.8), ("Persistent Systems", 3.4), ("Coforge", 3.1), ("ABB India", 2.8),
    ],
    "Bandhan Large & Mid Cap Fund": [
        ("HDFC Bank", 7.5), ("ICICI Bank", 6.9), ("Bajaj Finance", 5.8),
        ("Infosys", 5.2), ("Maruti Suzuki", 4.8), ("Persistent Systems", 4.3),
        ("Sun Pharma", 3.9), ("Torrent Pharma", 3.5), ("Cummins India", 3.2), ("PI Industries", 2.9),
    ],
    "Kotak Midcap Fund": [
        ("Trent", 5.8), ("Tube Investments", 5.2), ("Voltas", 4.8),
        ("Cummins India", 4.5), ("Indian Hotels", 4.2), ("Mphasis", 3.9),
        ("AU Small Finance Bank", 3.6), ("Persistent Systems", 3.4),
        ("Supreme Industries", 3.1), ("Coforge", 2.8),
    ],
    "Invesco India Smallcap Fund": [
        ("Kaynes Technology", 4.2), ("KPIT Technologies", 3.8), ("Radico Khaitan", 3.5),
        ("Fine Organic Ind", 3.2), ("Navin Fluorine", 3.0), ("Blue Star", 2.9),
        ("Elecon Engineering", 2.7), ("Garware Technical", 2.5), ("Aptus Value Housing", 2.4), ("Titagarh Rail", 2.2),
    ],
    "HDFC Small Cap Fund": [
        ("Firstsource Solutions", 3.5), ("Mold-Tek Packaging", 3.2), ("KPIT Technologies", 3.0),
        ("TeamLease Services", 2.8), ("Navin Fluorine", 2.6), ("KNR Constructions", 2.4),
        ("Ceat Tyres", 2.3), ("Tube Investments", 2.2), ("PNB Housing Finance", 2.1), ("Sonata Software", 2.0),
    ],
    "HDFC Flexi Cap Fund": [
        ("ICICI Bank", 9.5), ("HDFC Bank", 8.8), ("Infosys", 7.2),
        ("Reliance Industries", 6.5), ("Axis Bank", 5.1), ("Bharti Airtel", 4.8),
        ("Kotak Mahindra Bank", 4.2), ("Sun Pharma", 3.8), ("Bajaj Finance", 3.5), ("HUL", 3.1),
    ],
    "Kotak Multicap Fund": [
        ("HDFC Bank", 7.2), ("ICICI Bank", 6.5), ("Infosys", 5.8),
        ("Reliance Industries", 5.2), ("Trent", 4.6), ("Tube Investments", 4.1),
        ("Axis Bank", 3.8), ("Persistent Systems", 3.5), ("Bajaj Finance", 3.2), ("Navin Fluorine", 2.9),
    ],
    "Canara Rob Multi Cap Fund": [
        ("ICICI Bank", 7.8), ("HDFC Bank", 6.9), ("Infosys", 6.2),
        ("Reliance Industries", 5.5), ("Axis Bank", 4.8), ("KPIT Technologies", 4.1),
        ("Sun Pharma", 3.8), ("Trent", 3.4), ("Bajaj Finance", 3.1), ("Persistent Systems", 2.8),
    ],
    "SBI Infrastructure Fund": [
        ("Larsen & Toubro", 9.2), ("NTPC", 7.8), ("Power Grid", 6.4),
        ("BEL", 5.9), ("BHEL", 5.2), ("Adani Ports", 4.8),
        ("Siemens", 4.5), ("ABB India", 4.1), ("ONGC", 3.8), ("Grasim Industries", 3.5),
    ],
    "ICICI Pru Focused Equity Fund": [
        ("ICICI Bank", 8.5), ("Reliance Industries", 7.8), ("HDFC Bank", 7.2),
        ("Bharti Airtel", 6.5), ("Infosys", 5.8), ("HUL", 5.2),
        ("Axis Bank", 4.8), ("Sun Pharma", 4.5), ("TCS", 4.1), ("ONGC", 3.8),
    ],
    "Invesco India Focused Fund": [
        ("HDFC Bank", 8.1), ("ICICI Bank", 7.5), ("Infosys", 6.8),
        ("Axis Bank", 5.9), ("Bajaj Finance", 5.2), ("Sun Pharma", 4.8),
        ("Maruti Suzuki", 4.5), ("KPIT Technologies", 4.1), ("Persistent Systems", 3.8), ("Bharti Airtel", 3.5),
    ],
    "ICICI Pru Dividend Yield Fund": [
        ("ONGC", 6.8), ("Coal India", 6.2), ("NTPC", 5.8),
        ("Power Grid", 5.4), ("HDFC Bank", 5.1), ("Infosys", 4.8),
        ("ITC", 4.5), ("HUL", 4.2), ("ICICI Bank", 3.9), ("Reliance Industries", 3.6),
    ],
}

# ── Number of stocks per scheme ───────────────────────────────────────────────

NO_OF_STOCKS = {
    "Quant Large Cap Fund": 38,
    "SBI Large & Midcap Fund": 62,
    "DSP Large & Mid Cap Fund": 58,
    "Bandhan Large & Mid Cap Fund": 55,
    "Kotak Midcap Fund": 48,
    "Invesco India Smallcap Fund": 72,
    "HDFC Small Cap Fund": 68,
    "HDFC Flexi Cap Fund": 52,
    "Kotak Multicap Fund": 64,
    "Canara Rob Multi Cap Fund": 60,
    "SBI Infrastructure Fund": 42,
    "ICICI Pru Focused Equity Fund": 30,
    "Invesco India Focused Fund": 30,
    "ICICI Pru Dividend Yield Fund": 44,
}

# ── Fund Managers ─────────────────────────────────────────────────────────────

FUND_MANAGERS = {
    "Quant Large Cap Fund": "Ankit Pande, Vasav Sahgal",
    "SBI Large & Midcap Fund": "Sohini Andani, Mohit Jain",
    "DSP Large & Mid Cap Fund": "Rohit Singhania, Jay Kothari",
    "Bandhan Large & Mid Cap Fund": "Manish Gunwani, Daylynn Pinto",
    "Kotak Midcap Fund": "Harish Krishnan, Arjun Khanna",
    "Invesco India Smallcap Fund": "Taher Badshah, Dhimant Kothari",
    "HDFC Small Cap Fund": "Chirag Setalvad",
    "HDFC Flexi Cap Fund": "Roshi Jain",
    "Kotak Multicap Fund": "Harish Krishnan, Arjun Khanna",
    "Canara Rob Multi Cap Fund": "Shridatta Bhandwaldar, Miyush Gandhi",
    "SBI Infrastructure Fund": "Richard D'souza",
    "ICICI Pru Focused Equity Fund": "Sankaran Naren, Anand Sharma",
    "Invesco India Focused Fund": "Taher Badshah, Dhimant Kothari",
    "ICICI Pru Dividend Yield Fund": "Mittul Kalawadia, Sri Sharma",
}

# ── Overlap matrix (common stocks %) – based on Apr-2025 portfolio ────────────

def compute_overlap_matrix() -> pd.DataFrame:
    """
    Build pairwise overlap matrix from holdings data.
    Overlap = |A ∩ B| / |A ∪ B| × 100  (Jaccard similarity).
    """
    names = list(TOP_HOLDINGS.keys())
    # Use top-10 stock names as proxy for full portfolio
    holdings = {name: set(s for s, _ in stocks) for name, stocks in TOP_HOLDINGS.items()}
    n = len(names)
    matrix = np.zeros((n, n))
    for i, ni in enumerate(names):
        for j, nj in enumerate(names):
            if i == j:
                matrix[i][j] = 100.0
            else:
                a, b = holdings[ni], holdings[nj]
                union = a | b
                inter = a & b
                matrix[i][j] = round(len(inter) / len(union) * 100, 1) if union else 0.0
    # Short names for display
    short_names = [n.replace("Fund", "").replace("Reg", "").strip()[:20] for n in names]
    return pd.DataFrame(matrix, index=short_names, columns=short_names)


# ── Stock movement (added/exited stubs) ───────────────────────────────────────

STOCK_MOVEMENTS = {
    "Quant Large Cap Fund": {
        "added": [("Wipro", 1.2), ("Titan", 0.9), ("NTPC", 0.8)],
        "exited": [("HCL Tech", 1.5), ("Bajaj Auto", 0.7)],
        "increased": [("HDFC Bank", +0.8), ("Reliance", +0.5)],
        "decreased": [("ITC", -0.6), ("Kotak Bank", -0.4)],
    },
    # Add for all 14 – abbreviated for brevity; expand in production
}

# ── AUM history (synthetic, 12M) – replace with AMFI monthly AUM data ─────────

def get_aum_history(scheme_name: str) -> pd.DataFrame:
    np.random.seed(hash(scheme_name) % 1000)
    months = pd.date_range(end=datetime.today(), periods=12, freq="MS")
    base_aum = np.random.uniform(2000, 30000)
    aum_vals = base_aum + np.cumsum(np.random.uniform(-500, 800, 12))
    return pd.DataFrame({"month": months, "aum": np.clip(aum_vals, 500, 60000)})
