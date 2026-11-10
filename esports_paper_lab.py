import json
import requests
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Polymarket Dashboard",
    page_icon="📊",
    layout="wide",
)

GAMMA_BASE = "https://gamma-api.polymarket.com"

CRYPTO_SERIES = [
    "btc-up-or-down-daily",
    "eth-up-or-down-daily",
    "btc-multi-strikes-weekly",
    "ethereum-multi-strikes-weekly",
    "btc-updown-15m",
    "btc-updown-1h",
    "eth-updown-15m",
    "sol-updown-15m",
]
COMMODITY_SERIES = [
    "gold-updown-15m",
    "gold-updown-1h",
    "gold-updown-1d",
    "silver-updown-15m",
    "silver-updown-1h",
    "silver-updown-1d",
]

def categorize(text):
    t = (text or "").lower()
    if any(k in t for k in ["cs2", "csgo", "counter-strike", "counter strike", "dota", "valorant", "league of legends", "lol worlds", "lck", "lpl", "esport"]):
        return "Esports"
    if any(k in t for k in ["nba", "nfl", "mlb", "nhl", "soccer", "football", "basketball", "ufc", "mma", "tennis", "golf", "f1"]):
        return "Sports"
    if any(k in t for k in ["gold", "silver", "oil", "commodity", "copper"]):
        return "Commodities"
    if any(k in t for k in ["temperature", "weather", "rain", "snow"]):
        return "Weather"
    if any(k in t for k in ["stock", "nasdaq", "s&p", "earnings"]):
        return "Stocks"
    return "Other"

@st.cache_data(ttl=300)
def load_markets(limit=300):
    resp = requests.get(
        f"{GAMMA_BASE}/markets",
        params={"active": "true", "closed": "false", "limit": limit},
        timeout=30,
    )
    resp.raise_for_status()
    markets = resp.json()
    rows = []
    for m in markets:
        text = f"{m.get('question','')} {m.get('slug','')}"
        yes_price = None
        try:
            prices = json.loads(m.get("outcomePrices") or "[]")
            yes_price = float(prices[0]) if prices else None
        except Exception:
            pass
        rows.append({
            "category": categorize(text),
            "question": m.get("question"),
            "slug": m.get("slug"),
            "yes_price": yes_price,
            "volume": float(m.get("volumeNum") or m.get("volume") or 0),
        })
    return pd.DataFrame(rows)

@st.cache_data(ttl=300)
def load_series_events(series_slug, limit=20):
    params = {"series_slug": series_slug, "active": "true", "closed": "false", "limit": limit}
    resp = requests.get(f"{GAMMA_BASE}/events", params=params, timeout=30)
    if resp.status_code != 200:
        return []
    return resp.json()

@st.cache_data(ttl=600)
def load_sports():
    resp = requests.get(f"{GAMMA_BASE}/sports", timeout=30)
    resp.raise_for_status()
    return resp.json()

st.title("Polymarket Dashboard")
st.caption("Esports · Sports · Crypto Windows · Commodities")

if st.button("Refresh", type="primary"):
    st.cache_data.clear()

# Main category tabs (no Crypto, no Politics)
df = load_markets()
if not df.empty:
    cats = ["Esports", "Sports", "Commodities", "Stocks", "Weather", "Other"]
    available = [c for c in cats if c in df["category"].unique()]
    if available:
        tabs = st.tabs(available)
        for tab, cat in zip(tabs, available):
            with tab:
                subset = df[df["category"] == cat].sort_values("volume", ascending=False)
                st.subheader(f"{cat} — {len(subset)}")
                display = subset[["question", "yes_price", "volume", "slug"]].copy()
                display["yes_price"] = display["yes_price"].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
                display["volume"] = display["volume"].apply(lambda x: f"${x:,.0f}")
                st.dataframe(display, use_container_width=True, hide_index=True)
                csv = subset.to_csv(index=False).encode("utf-8")
                st.download_button(f"Export {cat}", csv, f"polymarket_{cat.lower()}.csv", "text/csv", key=f"exp_{cat}")

st.divider()

# Esports leagues from sports endpoint
st.subheader("Esports Leagues")
sports = load_sports()
esports = [s for s in sports if any(k in (s.get("sport") or "").lower() for k in ["cs2", "csgo", "dota", "lol", "valorant", "esport"])]
if esports:
    labels = [f"{s.get('sport','?')} (series {s.get('series','?')})" for s in esports[:30]]
    choice = st.selectbox("League", labels)
    idx = labels.index(choice)
    series_id = esports[idx].get("series")
    if st.button("Load Esports Games"):
        params = {"series_id": series_id, "active": "true", "closed": "false", "limit": 30}
        resp = requests.get(f"{GAMMA_BASE}/events", params=params, timeout=30)
        events = resp.json() if resp.status_code == 200 else []
        if events:
            rows = [{"title": e.get("title"), "slug": e.get("slug"), "volume": e.get("volume")} for e in events]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No active games for this league right now.")
else:
    st.info("No esports leagues found in the sports list right now.")

st.divider()

# Crypto windows (kept)
st.subheader("Crypto Windows")
crypto_choice = st.selectbox("Crypto series", CRYPTO_SERIES)
if st.button("Load Crypto Windows"):
    events = load_series_events(crypto_choice)
    if events:
        rows = [{"title": e.get("title"), "slug": e.get("slug"), "volume": e.get("volume")} for e in events]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No active windows for this series right now.")

# Commodities
st.subheader("Commodities Windows")
comm_choice = st.selectbox("Commodity series", COMMODITY_SERIES)
if st.button("Load Commodity Windows"):
    events = load_series_events(comm_choice)
    if events:
        rows = [{"title": e.get("title"), "slug": e.get("slug"), "volume": e.get("volume")} for e in events]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No active windows for this series right now.")
