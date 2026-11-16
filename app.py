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
OECD_URL = "https://www.oecd.org/en/publications/corporate-tax-statistics-2024_9c27d6e8-en/full-report/statutory-corporate-income-tax-rates_440f9286.html"
TE_URL = "https://tradingeconomics.com/bonds?app=true"

# Embedded spreadsheet snapshots. Values are percentage points, not decimals.
# OECD 2024 observations: user-provided OECD Corporate Tax Rates 2024 workbook.
# Bond observations: user-provided Trading Economics screenshot snapshot, November 15, 2026.
TAX_RATES_2024 = {'Albania': 15.0, 'Andorra': 10.0, 'Angola': 25.0, 'Anguilla': 0.0, 'Antigua and Barbuda': 25.0, 'Argentina': 35.0, 'Armenia': 18.0, 'Aruba': 22.0, 'Australia': 30.0, 'Austria': 23.0, 'Azerbaijan': 20.0, 'Bahamas': 0.0, 'Bahrain': 0.0, 'Bailiwick of Guernsey': 0.0, 'Barbados': 9.0, 'Belgium': 25.0, 'Belize': 0.0, 'Benin': 30.0, 'Bermuda': 0.0, 'Bosnia and Herzegovina': 10.0, 'Botswana': 22.0, 'Brazil': 34.0, 'British Virgin Islands': 0.0, 'Brunei Darussalam': 18.5, 'Bulgaria': 10.0, 'Burkina Faso': 27.5, 'Cabo Verde': 21.42, 'Cameroon': 33.0, 'Canada': 25.99, 'Cayman Islands': 0.0, 'Chile': 27.0, 'China (People’s Republic of)': 25.0, 'Colombia': 35.0, 'Congo': 28.0, 'Cook Islands': 20.0, 'Costa Rica': 30.0, 'Croatia': 18.0, 'Curaçao': 15.0, 'Czechia': 21.0, 'Côte d’Ivoire': 25.0, 'Democratic Republic of the Congo': 30.0, 'Denmark': 22.0, 'Djibouti': 25.0, 'Dominica': 25.0, 'Dominican Republic': 27.0, 'Egypt': 22.5, 'Estonia': 20.0, 'Eswatini': 27.5, 'Faroe Islands': 18.0, 'Finland': 20.0, 'France': 25.825, 'Gabon': 30.0, 'Georgia': 15.0, 'Germany': 30.133026, 'Gibraltar': 12.5, 'Greece': 22.0, 'Greenland': 26.5, 'Grenada': 28.0, 'Haiti': 30.0, 'Honduras': 30.0, 'Hong Kong (China)': 16.5, 'Hungary': 9.0, 'Iceland': 21.0, 'India': 25.17, 'Indonesia': 22.0, 'Ireland': 12.5, 'Isle of Man': 0.0, 'Israel': 23.0, 'Italy': 27.81, 'Jamaica': 25.0, 'Japan': 29.74, 'Jersey': 0.0, 'Jordan': 20.0, 'Kazakhstan': 20.0, 'Kenya': 30.0, 'Korea': 26.4, 'Kuwait': 15.0, 'Latvia': 20.0, 'Liberia': 25.0, 'Liechtenstein': 12.5, 'Lithuania': 15.0, 'Luxembourg': 24.94, 'Macau (China)': 12.0, 'Malaysia': 24.0, 'Maldives': 15.0, 'Malta': 35.0, 'Mauritania': 25.0, 'Mauritius': 15.0, 'Mexico': 30.0, 'Monaco': 25.0, 'Mongolia': 25.0, 'Montenegro': 15.0, 'Montserrat': 30.0, 'Morocco': 33.0, 'Namibia': 32.0, 'Netherlands': 25.8, 'New Zealand': 28.0, 'Nigeria': 30.0, 'North Macedonia': 10.0, 'Norway': 22.0, 'Oman': 15.0, 'Pakistan': 29.0, 'Panama': 25.0, 'Papua New Guinea': 30.0, 'Paraguay': 10.0, 'Peru': 29.5, 'Philippines': 25.0, 'Poland': 19.0, 'Portugal': 31.5, 'Qatar': 10.0, 'Romania': 16.0, 'Saint Kitts and Nevis': 33.0, 'Saint Lucia': 30.0, 'Saint Vincent and the Grenadines': 28.0, 'Samoa': 27.0, 'San Marino': 17.0, 'Saudi Arabia': 20.0, 'Senegal': 30.0, 'Serbia': 15.0, 'Seychelles': 25.0, 'Sierra Leone': 25.0, 'Singapore': 17.0, 'Slovak Republic': 21.0, 'Slovenia': 22.0, 'South Africa': 27.0, 'Spain': 25.0, 'Sri Lanka': 30.0, 'Sweden': 20.6, 'Switzerland': 19.608138, 'Thailand': 20.0, 'Togo': 27.0, 'Trinidad and Tobago': 30.0, 'Tunisia': 15.0, 'Turks and Caicos Islands': 0.0, 'Türkiye': 25.0, 'Ukraine': 18.0, 'United Arab Emirates': 9.0, 'United Kingdom': 25.0, 'United States': 25.631375, 'Uruguay': 25.0, 'Uzbekistan': 15.0, 'Viet Nam': 20.0, 'Zambia': 30.0}
ISO3_CODES = {'Albania': 'ALB', 'Andorra': 'AND', 'Angola': 'AGO', 'Anguilla': 'AIA', 'Antigua and Barbuda': 'ATG', 'Argentina': 'ARG', 'Armenia': 'ARM', 'Aruba': 'ABW', 'Australia': 'AUS', 'Austria': 'AUT', 'Azerbaijan': 'AZE', 'Bahamas': 'BHS', 'Bahrain': 'BHR', 'Bailiwick of Guernsey': 'GGY', 'Barbados': 'BRB', 'Belgium': 'BEL', 'Belize': 'BLZ', 'Benin': 'BEN', 'Bermuda': 'BMU', 'Bosnia and Herzegovina': 'BIH', 'Botswana': 'BWA', 'Brazil': 'BRA', 'British Virgin Islands': 'VGB', 'Brunei Darussalam': 'BRN', 'Bulgaria': 'BGR', 'Burkina Faso': 'BFA', 'Cabo Verde': 'CPV', 'Cameroon': 'CMR', 'Canada': 'CAN', 'Cayman Islands': 'CYM', 'Chile': 'CHL', 'China (People’s Republic of)': 'CHN', 'Colombia': 'COL', 'Congo': 'COG', 'Cook Islands': 'COK', 'Costa Rica': 'CRI', 'Croatia': 'HRV', 'Curaçao': 'CUW', 'Czechia': 'CZE', 'Côte d’Ivoire': 'CIV', 'Democratic Republic of the Congo': 'COD', 'Denmark': 'DNK', 'Djibouti': 'DJI', 'Dominica': 'DMA', 'Dominican Republic': 'DOM', 'Egypt': 'EGY', 'Estonia': 'EST', 'Eswatini': 'SWZ', 'Faroe Islands': 'FRO', 'Finland': 'FIN', 'France': 'FRA', 'Gabon': 'GAB', 'Georgia': 'GEO', 'Germany': 'DEU', 'Gibraltar': 'GIB', 'Greece': 'GRC', 'Greenland': 'GRL', 'Grenada': 'GRD', 'Haiti': 'HTI', 'Honduras': 'HND', 'Hong Kong (China)': 'HKG', 'Hungary': 'HUN', 'Iceland': 'ISL', 'India': 'IND', 'Indonesia': 'IDN', 'Ireland': 'IRL', 'Isle of Man': 'IMN', 'Israel': 'ISR', 'Italy': 'ITA', 'Jamaica': 'JAM', 'Japan': 'JPN', 'Jersey': 'JEY', 'Jordan': 'JOR', 'Kazakhstan': 'KAZ', 'Kenya': 'KEN', 'Korea': 'KOR', 'Kuwait': 'KWT', 'Latvia': 'LVA', 'Liberia': 'LBR', 'Liechtenstein': 'LIE', 'Lithuania': 'LTU', 'Luxembourg': 'LUX', 'Macau (China)': 'MAC', 'Malaysia': 'MYS', 'Maldives': 'MDV', 'Malta': 'MLT', 'Mauritania': 'MRT', 'Mauritius': 'MUS', 'Mexico': 'MEX', 'Monaco': 'MCO', 'Mongolia': 'MNG', 'Montenegro': 'MNE', 'Montserrat': 'MSR', 'Morocco': 'MAR', 'Namibia': 'NAM', 'Netherlands': 'NLD', 'New Zealand': 'NZL', 'Nigeria': 'NGA', 'North Macedonia': 'MKD', 'Norway': 'NOR', 'Oman': 'OMN', 'Pakistan': 'PAK', 'Panama': 'PAN', 'Papua New Guinea': 'PNG', 'Paraguay': 'PRY', 'Peru': 'PER', 'Philippines': 'PHL', 'Poland': 'POL', 'Portugal': 'PRT', 'Qatar': 'QAT', 'Romania': 'ROU', 'Saint Kitts and Nevis': 'KNA', 'Saint Lucia': 'LCA', 'Saint Vincent and the Grenadines': 'VCT', 'Samoa': 'WSM', 'San Marino': 'SMR', 'Saudi Arabia': 'SAU', 'Senegal': 'SEN', 'Serbia': 'SRB', 'Seychelles': 'SYC', 'Sierra Leone': 'SLE', 'Singapore': 'SGP', 'Slovak Republic': 'SVK', 'Slovenia': 'SVN', 'South Africa': 'ZAF', 'Spain': 'ESP', 'Sri Lanka': 'LKA', 'Sweden': 'SWE', 'Switzerland': 'CHE', 'Thailand': 'THA', 'Togo': 'TGO', 'Trinidad and Tobago': 'TTO', 'Tunisia': 'TUN', 'Turks and Caicos Islands': 'TCA', 'Türkiye': 'TUR', 'Ukraine': 'UKR', 'United Arab Emirates': 'ARE', 'United Kingdom': 'GBR', 'United States': 'USA', 'Uruguay': 'URY', 'Uzbekistan': 'UZB', 'Viet Nam': 'VNM', 'Zambia': 'ZMB'}
BOND_YIELDS_2026_11_15 = {'Australia': 5.138, 'Austria': 3.6096, 'Belgium': 4.3545, 'Brazil': 15.335, 'Canada': 3.856, 'Chile': 6.01, 'China': 1.6181, 'Colombia': 12.698, 'Croatia': 3.8668, 'Czech Republic': 5.2222, 'Denmark': 3.169, 'Finland': 3.7611, 'France': 4.921, 'Germany': 3.3762, 'Greece': 4.2636, 'Hong Kong': 3.994, 'Hungary': 5.5249, 'Iceland': 6.81, 'India': 7.312, 'Indonesia': 7.607, 'Ireland': 3.5391, 'Israel': 4.183, 'Italy': 4.437, 'Japan': 2.877, 'Kenya': 12.5, 'Lithuania': 4.325, 'Malaysia': 3.8628, 'Mexico': 9.308, 'Netherlands': 3.4768, 'New Zealand': 4.768, 'Nigeria': 16.598, 'Norway': 4.3842, 'Pakistan': 12.604, 'Peru': 6.2414, 'Philippines': 7.767, 'Poland': 6.335, 'Portugal': 3.819, 'Romania': 7.12, 'Russia': 16.74, 'Singapore': 2.3296, 'Slovakia': 4.305, 'Slovenia': 3.914, 'South Africa': 8.675, 'South Korea': 3.987, 'Spain': 3.9442, 'Sweden': 3.098, 'Switzerland': 0.5626, 'Taiwan': 1.86, 'Thailand': 1.995, 'Turkey': 33.52, 'United Kingdom': 5.3377, 'United States': 5.149, 'Vietnam': 4.573, 'Zambia': 14.74}
COUNTRY_NAMES = sorted(set(TAX_RATES_2024) | set(BOND_YIELDS_2026_11_15))

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


def fetch_oecd_taxes():
    """Return supplied OECD 2024 country data (not live 2026 data)."""
    return TAX_RATES_2024.copy()


def fetch_bond_yields():
    """Return supplied Trading Economics 10-year snapshot (not live yields)."""
    return BOND_YIELDS_2026_11_15.copy()


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
st.write("Compare the USD and selected-country currency costs of equity, debt, and WACC. Tax and bond data come from uploaded dated spreadsheets; industry beta and BBB spread are fetched when accessible. All fallback assumptions are labeled.")

with st.sidebar:
    st.header("Investment Assumptions")
    if st.button("🔄 Refresh source data", use_container_width=True):
        fetch_betas.clear()
        fetch_bbb_spread.clear()
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
    status["Corporate taxes"] = "Loaded supplied OECD 2024 workbook snapshot"
except Exception as exc:
    taxes = {}
    status["Corporate taxes"] = f"Embedded tax snapshot could not be loaded; {type(exc).__name__}"
try:
    yields = fetch_bond_yields()
    status["10-year yields"] = "Loaded supplied Trading Economics snapshot (November 15, 2026)"
except Exception as exc:
    yields = {}
    status["10-year yields"] = f"Embedded yield snapshot could not be loaded; {type(exc).__name__}"

industry_names = betas["Industry"].tolist()
default_industry = next((i for i, value in enumerate(industry_names) if "Software (System" in value), 0)
with st.sidebar:
    industry = st.selectbox("Industry", industry_names, index=default_industry)
    country = st.selectbox("Target country", COUNTRY_NAMES, index=COUNTRY_NAMES.index("United States"))
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
    if tax_auto is None:
        st.warning("No 2024 OECD tax rate for this selection. The displayed tax is an illustrative manual assumption.")
    override_us_yield = st.checkbox("Override U.S. 10-year yield", value=("United States" not in yields))
    us_yield_pct = st.number_input("U.S. 10-year yield (%)", -5.0, 50.0, float(yields.get("United States", COURSE_US_YIELD)), 0.01, disabled=not override_us_yield)
    foreign_auto = us_yield_pct if country == "United States" else yields.get(country)
    override_foreign_yield = st.checkbox("Override target-country 10-year yield", value=(foreign_auto is None), disabled=(country == "United States"))
    if foreign_auto is None and country != "United States":
        st.warning("No 10-year yield in the screenshot snapshot for this country. Enter a verified yield; 12% is only an example.")
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

if country != "United States" and foreign_auto is None and not override_foreign_yield:
    st.error("A verified target-country 10-year yield is required for this calculation.")
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
st.caption("Tax data: OECD 2024 (supplied workbook). Bond yields: Trading Economics screenshot snapshot, November 15, 2026. All rates are nominal annual percentage rates; borrowing spread is added to the respective government yield. A foreign rate reflects the selected currency, not an exchange-rate prediction.")

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
    if msg.startswith(("Fetched", "Loaded")):
        st.success(f"{label}: {msg}")
    else:
        st.warning(f"{label}: {msg}")
st.caption(f"Data availability checked at {fetched_at}. This is the retrieval time, not necessarily the original market observation or publication date. Beta workbook is typically annual; OECD tax rates are from 2024 and may be outdated; bond yields are a dated November 2026 snapshot, not live updates. Always verify the dated source before submitting.")
st.markdown(f"[Damodaran industry beta workbook]({BETA_URL}) · [Damodaran rating spreads]({SPREAD_URL}) · [OECD 2024 corporate tax report]({OECD_URL}) · [Trading Economics bonds]({TE_URL})")


with st.expander("Source coverage and data vintage"):
    st.write(f"OECD 2024 tax jurisdictions: **{len(TAX_RATES_2024)}** | Bond yield snapshot countries: **{len(BOND_YIELDS_2026_11_15)}**")
    st.write("For a country without a matching bond observation, supply a verified yield manually. The 2024 tax sheet is historical and should not be described as the current tax rate.")
