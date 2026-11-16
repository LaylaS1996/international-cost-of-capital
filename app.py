"""International Cost of Capital Calculator — Kellogg International Finance.

Web sources may change their HTML structure. Failed fetches are prominently
identified; illustrative fallback inputs are never represented as live data.
"""

from datetime import datetime, timezone
from io import BytesIO, StringIO
import re

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="International Cost of Capital", page_icon="🌎", layout="wide")

BETA_URL = "https://pages.stern.nyu.edu/~adamodar/pc/datasets/betas.xls"
SPREAD_URL = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ratings.html"
OECD_URL = "https://www.oecd.org/en/publications/corporate-tax-statistics-2026_73af6222-en/full-report/statutory-corporate-income-tax-rates_ce84abb9.html"
TE_URL = "https://tradingeconomics.com/bonds?app=true"
OECD_API_URL = (
    "https://sdmx.oecd.org/public/rest/data/"
    "OECD.CTP.TPS,DSD_TAX_CIT@DF_CIT,2.0/"
    "USA+COL+GBR+DEU+FRA+JPN+CAN+AUS+IND+BRA.A..ST..S13...?"
    "startPeriod=2026&endPeriod=2026&dimensionAtObservation=AllDimensions&format=csvfile"
)
COUNTRIES = {
    "United States": "United States", "Colombia": "Colombia",
    "United Kingdom": "United Kingdom", "Germany": "Germany",
    "France": "France", "Japan": "Japan", "Canada": "Canada",
    "Australia": "Australia", "India": "India", "Brazil": "Brazil",
}
COURSE_BETA = 0.80
COURSE_TAX = 35.0
COURSE_US_YIELD = 4.0
COURSE_FOREIGN_YIELD = 12.0
COURSE_SPREAD = 1.5


def download(url):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; StudentResearch/1.0)"}, timeout=18)
    response.raise_for_status()
    return response.content


def clean_columns(frame):
    frame = frame.copy()
    frame.columns = [" ".join(str(x) for x in c) if isinstance(c, tuple) else str(c) for c in frame.columns]
    return frame


def numeric(value):
    if pd.isna(value):
        return None
    match = re.search(r"-?\d+(?:[.,]\d+)?", str(value).replace("\u00a0", ""))
    return float(match.group(0).replace(",", ".")) if match else None


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_betas():
    raw = download(BETA_URL)
    workbook = pd.ExcelFile(BytesIO(raw), engine="xlrd")
    for sheet in workbook.sheet_names:
        frame = pd.read_excel(workbook, sheet_name=sheet, header=None)
        for i in range(min(15, len(frame))):
            headers = [str(v).strip().lower() for v in frame.iloc[i]]
            industry_cols = [j for j, v in enumerate(headers) if "industry" in v and ("name" in v or v == "industry")]
            beta_cols = [j for j, v in enumerate(headers) if "unlevered beta" in v and "correct" not in v]
            if industry_cols and beta_cols:
                rows = frame.iloc[i + 1:, [industry_cols[0], beta_cols[0]]].copy()
                rows.columns = ["Industry", "Beta"]
                rows["Industry"] = rows["Industry"].astype(str).str.strip()
                rows["Beta"] = pd.to_numeric(rows["Beta"], errors="coerce")
                rows = rows.loc[rows["Beta"].between(0, 20) & rows["Industry"].ne("nan")]
                rows = rows.drop_duplicates("Industry").sort_values("Industry").reset_index(drop=True)
                if len(rows) >= 10:
                    return rows
    raise ValueError("Unlevered-beta column not found in Damodaran workbook")


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_bbb_spread():
    tables = pd.read_html(StringIO(download(SPREAD_URL).decode("utf-8", errors="replace")))
    for raw in tables:
        frame = raw.astype(str)
        for _, row in frame.iterrows():
            cells = [str(x).strip() for x in row.tolist()]
            for idx, value in enumerate(cells):
                if re.search(r"Baa2\s*/\s*BBB", value, re.IGNORECASE):
                    # First BBB row and its immediately following spread are
                    # the large non-financial firm column in the source table.
                    for spread_text in cells[idx + 1:idx + 3]:
                        if "%" in spread_text:
                            spread = numeric(spread_text)
                            if spread is not None and 0 <= spread <= 20:
                                return spread
    raise ValueError("Large non-financial Baa2/BBB spread not found")


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_oecd_taxes():
    """Read OECD 2026 combined general-government statutory CIT rates via SDMX.

    Never infer a tax rate from a report summary or another tax indicator.
    """
    response = requests.get(
        OECD_API_URL,
        headers={"Accept": "csvfile", "User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    frame = pd.read_csv(StringIO(response.text))
    columns = {str(c).upper(): c for c in frame.columns}
    required = ("REF_AREA", "TIME_PERIOD", "OBS_VALUE")
    if not all(c in columns for c in required):
        raise ValueError("OECD API did not return the expected SDMX CSV fields")
    names = {"USA": "United States", "COL": "Colombia", "GBR": "United Kingdom",
             "DEU": "Germany", "FRA": "France", "JPN": "Japan", "CAN": "Canada",
             "AUS": "Australia", "IND": "India", "BRA": "Brazil"}
    result = {}
    for _, row in frame.iterrows():
        code = str(row[columns["REF_AREA"]]).strip().upper()
        year = str(row[columns["TIME_PERIOD"]]).strip()
        value = pd.to_numeric(row[columns["OBS_VALUE"]], errors="coerce")
        if code in names and year == "2026" and pd.notna(value) and 0 <= value <= 60:
            result[names[code]] = float(value)
    if "United States" not in result:
        raise ValueError("OECD API returned no usable U.S. statutory rate for 2026")
    return result


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_bond_yields():
    """Read current 10-year yields from Trading Economics public bond table."""
    html = download(TE_URL).decode("utf-8", errors="replace")
    result = {}
    for raw in pd.read_html(StringIO(html)):
        frame = clean_columns(raw)
        cols = list(frame.columns)
        country_col = next((c for c in cols if any(w in c.lower().replace(" ", "") for w in ("country", "major10y", "government"))), None)
        yield_col = next((c for c in cols if c.lower().strip() in ("yield", "last")), None)
        if not country_col or not yield_col:
            continue
        for _, row in frame.iterrows():
            label = str(row[country_col]).strip()
            value = numeric(row[yield_col])
            if value is None or not -5 <= value <= 50:
                continue
            for country in COUNTRIES:
                if label.lower() == country.lower() or label.lower().startswith(country.lower() + " "):
                    result[country] = value
    if "United States" not in result:
        raise ValueError("U.S. 10-year bond yield not found in public table")
    return result


def calculate(beta, tax_pct, us_yield_pct, foreign_yield_pct, spread_pct, foreign_spread_pct, erp_pct, debt_pct):
    d = debt_pct / 100
    tax, rf_us, rf_foreign = tax_pct / 100, us_yield_pct / 100, foreign_yield_pct / 100
    spread, foreign_spread, erp = spread_pct / 100, foreign_spread_pct / 100, erp_pct / 100
    levered = beta * (1 + (1 - tax) * d / (1 - d))
    us_equity = rf_us + levered * erp
    us_debt = rf_us + spread
    us_wacc = (1 - d) * us_equity + d * us_debt * (1 - tax)
    factor = (1 + rf_foreign) / (1 + rf_us)
    foreign_equity = (1 + us_equity) * factor - 1
    foreign_debt = rf_foreign + foreign_spread
    foreign_wacc = (1 - d) * foreign_equity + d * foreign_debt * (1 - tax)
    return {"Levered Beta": levered, "USD Cost of Equity (%)": us_equity * 100,
            "USD Cost of Debt (%)": us_debt * 100, "USD WACC (%)": us_wacc * 100,
            "Foreign Cost of Equity (%)": foreign_equity * 100,
            "Foreign Cost of Debt (%)": foreign_debt * 100,
            "Foreign WACC (%)": foreign_wacc * 100}


st.title("🌎 International Cost of Capital Calculator")
st.caption("Kellogg International Finance · Professor Sergio Rebelo methodology")
st.write("Compare the USD and selected-country currency costs of equity, debt, and WACC. Market data is fetched where available; every fallback is labeled.")

with st.sidebar:
    st.header("Investment Assumptions")
    if st.button("🔄 Refresh source data", use_container_width=True):
        fetch_betas.clear()
        fetch_bbb_spread.clear()
        fetch_oecd_taxes.clear()
        fetch_bond_yields.clear()
        st.rerun()

status = {}
fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
try:
    betas = fetch_betas()
    status["Industry betas"] = "Fetched from Damodaran"
except Exception as exc:
    betas = pd.DataFrame({"Industry": ["Software (System & Application)", "Real Estate"], "Beta": [COURSE_BETA, COURSE_BETA]})
    status["Industry betas"] = f"Unavailable — illustrative beta; {type(exc).__name__}"
try:
    bbb_default = fetch_bbb_spread()
    status["USD BBB spread"] = "Fetched from Damodaran"
except Exception as exc:
    bbb_default = COURSE_SPREAD
    status["USD BBB spread"] = f"Unavailable — illustrative 1.5%; {type(exc).__name__}"
try:
    taxes = fetch_oecd_taxes()
    status["Corporate taxes"] = "Fetched OECD 2026 statutory rates"
except Exception as exc:
    taxes = {}
    status["Corporate taxes"] = f"Unavailable — manual input required; {type(exc).__name__}"
try:
    yields = fetch_bond_yields()
    status["10-year yields"] = "Fetched Trading Economics bond table"
except Exception as exc:
    yields = {}
    status["10-year yields"] = f"Unavailable — manual input required; {type(exc).__name__}"

industry_names = betas["Industry"].tolist()
default_industry = next((i for i, value in enumerate(industry_names) if "Software (System" in value), 0)
with st.sidebar:
    industry = st.selectbox("Industry", industry_names, index=default_industry)
    country = st.selectbox("Target country", list(COUNTRIES), index=0)
    erp_pct = st.number_input("Equity risk premium (%)", 0.0, 30.0, 6.5, 0.1)
    debt_pct = st.slider("Target debt financing (%)", 0, 99, 30)
    st.subheader("Fetched inputs and overrides")
    beta_auto = float(betas.loc[betas["Industry"] == industry, "Beta"].iloc[0])
    override_beta = st.checkbox("Override unlevered beta")
    beta = st.number_input("Unlevered beta", 0.0, 20.0, beta_auto, 0.01, disabled=not override_beta)
    us_tax_auto = next((v for k, v in taxes.items() if k.lower() in ("united states", "united states of america")), None)
    foreign_tax_auto = taxes.get(country)
    tax_country = st.radio("Project corporate tax rate", ["U.S. tax", "Selected-country tax"], horizontal=True)
    tax_auto = us_tax_auto if tax_country == "U.S. tax" else foreign_tax_auto
    override_tax = st.checkbox("Override corporate tax", value=(tax_auto is None))
    tax_pct = st.number_input("Corporate tax rate (%)", 0.0, 100.0, float(tax_auto if tax_auto is not None else COURSE_TAX), 0.1, disabled=not override_tax)
    override_us_yield = st.checkbox("Override U.S. 10-year yield", value=("United States" not in yields))
    us_yield_pct = st.number_input("U.S. 10-year yield (%)", -5.0, 50.0, float(yields.get("United States", COURSE_US_YIELD)), 0.01, disabled=not override_us_yield)
    foreign_auto = us_yield_pct if country == "United States" else yields.get(country)
    override_foreign_yield = st.checkbox("Override target-country 10-year yield", value=(foreign_auto is None), disabled=(country == "United States"))
    foreign_yield_pct = (us_yield_pct if country == "United States" else st.number_input(
        "Target-country 10-year yield (%)", -5.0, 50.0,
        float(foreign_auto if foreign_auto is not None else COURSE_FOREIGN_YIELD), 0.01,
        disabled=not override_foreign_yield))
    override_spread = st.checkbox("Override USD BBB spread")
    spread_pct = st.number_input("USD BBB borrowing spread (%)", 0.0, 20.0, float(bbb_default), 0.01, disabled=not override_spread)
    auto_foreign_spread = spread_pct * (1 + foreign_yield_pct / 100) / (1 + us_yield_pct / 100)
    override_foreign_spread = st.checkbox("Override foreign-currency BBB spread")
    foreign_spread_pct = st.number_input("Foreign BBB spread (%)", 0.0, 30.0, float(auto_foreign_spread), 0.01, disabled=not override_foreign_spread)

# Disabled controls display fetched values; the widget returns those values.
if country == "United States":
    foreign_yield_pct = us_yield_pct
    if not override_foreign_spread:
        foreign_spread_pct = spread_pct

if 1 + us_yield_pct / 100 <= 0:
    st.error("U.S. 10-year yield must exceed -100%.")
    st.stop()

if tax_auto is None and not override_tax:
    st.error("OECD tax rate could not be read. Enable the manual corporate tax override.")
    st.stop()

outputs = calculate(beta, tax_pct, us_yield_pct, foreign_yield_pct, spread_pct,
                    foreign_spread_pct, erp_pct, debt_pct)
st.header("Cost of Capital Comparison")
left, right = st.columns(2)
with left:
    st.subheader("🇺🇸 United States (USD)")
    st.metric("Cost of equity", f"{outputs['USD Cost of Equity (%)']:.4f}%")
    st.metric("Cost of debt", f"{outputs['USD Cost of Debt (%)']:.4f}%")
    st.metric("WACC", f"{outputs['USD WACC (%)']:.4f}%")
with right:
    st.subheader(f"🌍 {country} (local currency)")
    st.metric("Cost of equity", f"{outputs['Foreign Cost of Equity (%)']:.4f}%")
    st.metric("Cost of debt", f"{outputs['Foreign Cost of Debt (%)']:.4f}%")
    st.metric("WACC", f"{outputs['Foreign WACC (%)']:.4f}%")

st.subheader("Inputs and assumptions")
st.write(f"Industry: **{industry}** · Unlevered beta: **{beta:.4f}** · Levered beta: **{outputs['Levered Beta']:.4f}**")
st.write(f"Project tax rate: **{tax_pct:.2f}%** ({tax_country}) · Debt share: **{debt_pct}%** · ERP: **{erp_pct:.2f}%**")
st.write(f"U.S. 10-year yield: **{us_yield_pct:.2f}%** · Target-country yield: **{foreign_yield_pct:.2f}%** · USD BBB spread: **{spread_pct:.2f}%** · Foreign spread: **{foreign_spread_pct:.4f}%**")
st.caption("All rates are nominal annual percentage rates; borrowing spread is added to the respective government yield. A foreign rate reflects the selected currency, not an exchange-rate prediction.")

st.header("All-industry comparison")
industry_rows = []
for _, item in betas.iterrows():
    result = calculate(float(item["Beta"]), tax_pct, us_yield_pct, foreign_yield_pct,
                       spread_pct, foreign_spread_pct, erp_pct, debt_pct)
    industry_rows.append({"Industry": item["Industry"], "Unlevered Beta": float(item["Beta"]), **result})
comparison = pd.DataFrame(industry_rows)
st.dataframe(comparison, hide_index=True, use_container_width=True)
st.download_button("⬇️ Download all-industry CSV", comparison.to_csv(index=False).encode("utf-8"), "international_cost_of_capital_all_industries.csv", "text/csv")
selected_row = pd.DataFrame([{"Industry": industry, "Country": country, "Unlevered Beta": beta,
                              "Tax (%)": tax_pct, "ERP (%)": erp_pct, "Debt (%)": debt_pct,
                              "US 10Y (%)": us_yield_pct, "Foreign 10Y (%)": foreign_yield_pct,
                              "USD Spread (%)": spread_pct, "Foreign Spread (%)": foreign_spread_pct, **outputs}])
st.download_button("⬇️ Download selected calculation CSV", selected_row.to_csv(index=False).encode("utf-8"), "international_cost_of_capital_selected.csv", "text/csv")

st.header("Data sources and freshness")
for label, msg in status.items():
    if msg.startswith("Fetched"):
        st.success(f"{label}: {msg}")
    else:
        st.warning(f"{label}: {msg}")
st.caption(f"Data fetch checked at {fetched_at}. This is the retrieval time, not necessarily the original market observation or publication date. Beta workbook is typically annual; OECD page is the 2026 edition. Trading Economics values may be delayed or inaccessible. Always verify the dated source before submitting.")
st.markdown(f"[Damodaran industry beta workbook]({BETA_URL}) · [Damodaran rating spreads]({SPREAD_URL}) · [OECD 2026 corporate tax report]({OECD_URL}) · [Trading Economics bonds]({TE_URL})")

