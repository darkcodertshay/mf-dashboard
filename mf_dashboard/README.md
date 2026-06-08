# 📊 Anand Rathi — Equity MF Model Portfolio Dashboard

A production-grade, live Streamlit dashboard for the 14-scheme equity MF model portfolio
(Oct 2025 – Dec 2026). Fetches real-time data from AMFI India, MFAPI.in, and MoneyControl.

---

## 📁 Folder Structure

```
mf_dashboard/
├── app.py                        # Main Streamlit dashboard
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── .streamlit/
│   └── config.toml               # Dark theme & server settings
└── modules/
    ├── __init__.py
    ├── scheme_config.py          # Central registry: 14 scheme URLs, codes, weights
    ├── data_ingestion.py         # Live data fetching (AMFI, MFAPI, MoneyControl)
    ├── data_cleaning.py          # Enrichment, validation, formatting
    ├── portfolio_data.py         # Sector/holdings/overlap curated data
    └── charts.py                 # All Plotly chart builders
```

---

## ⚡ Quick Start (Local)

```bash
# 1. Clone / copy the project
cd mf_dashboard

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the dashboard
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## 🌐 Data Sources & Live Refresh

| Module            | Source                          | TTL      | Fallback                  |
|-------------------|---------------------------------|----------|---------------------------|
| NAV (current)     | AMFI India NAV flat file        | 1 hour   | Last cached value         |
| Historical NAV    | MFAPI.in REST API               | 1 hour   | Cached DataFrame          |
| Returns / CAGR    | Computed from MFAPI history     | 1 hour   | N/A                       |
| AUM / ER          | MoneyControl HTML scrape        | 2 hours  | Curated estimates         |
| Portfolio data    | SEBI monthly disclosures        | Manual   | portfolio_data.py module  |
| Fund flows        | AMFI category-wise report       | 24 hours | Synthetic illustration    |
| Benchmark (N50)   | UTI Nifty 50 Index via MFAPI    | 1 hour   | Flat return estimate      |

Auto-refresh: every **30 minutes** using `streamlit-autorefresh`.

---

## 🚀 Deployment

### Option A — Streamlit Community Cloud (Free)

1. Push this folder to a **public GitHub repo**.
2. Go to https://share.streamlit.io → New app.
3. Set `app.py` as the main file.
4. Deploy. No secrets needed for public APIs.

### Option B — Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.headless=true"]
```

```bash
docker build -t ar-mf-dashboard .
docker run -p 8501:8501 ar-mf-dashboard
```

### Option C — AWS EC2 / GCP VM

```bash
# Install
sudo apt update && sudo apt install python3-pip -y
pip3 install -r requirements.txt

# Run with screen (persistent)
screen -S dashboard
streamlit run app.py --server.port 8501 --server.headless true

# Or use systemd service for auto-start on reboot
```

---

## 📌 Limitations & Notes

1. **MoneyControl scraping**: MC uses heavy JavaScript rendering. The scraper does
   best-effort HTML parsing. Some fields (AUM, ER) may fall back to curated estimates.
   **Production fix**: Use Playwright or Selenium with a headless browser.

2. **Portfolio holdings / sector data**: Sourced from SEBI-mandated monthly disclosures.
   Updated manually in `modules/portfolio_data.py` each month.
   **Production fix**: Subscribe to PulseInfo API or Morningstar India for automated feeds.

3. **Fund flows**: AMFI category-level flows fetched. Scheme-level flows are not publicly
   available for free. **Production fix**: MFI Explorer or NJ India Invest API.

4. **Overlap matrix**: Computed on top-10 holdings (Jaccard similarity). Full 100+ stock
   overlap requires complete portfolio feed. Accuracy improves with full portfolio data.

5. **Invesco Smallcap (Fund 6)**: URL provided is a Google share link. The dashboard
   uses the AMFI code (147977) directly for data fetching.

---

## 🔧 Extending the Dashboard

- **Add a scheme**: Add a new entry in `modules/scheme_config.py` → `SCHEMES` list.
- **Update portfolio data**: Edit `modules/portfolio_data.py` monthly after SEBI disclosures.
- **Add alerts**: Use `st.toast()` or email via SMTP when returns cross a threshold.
- **Database backend**: Replace in-memory `st.cache_data` with PostgreSQL / SQLite for
  historical tracking.

---

## 📄 License

For internal use by Anand Rathi Private Wealth. Not for redistribution.
Past performance is not indicative of future results. Not investment advice.
