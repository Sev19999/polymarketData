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

def categorize(question, slug):
    text = f"{question or ''} {slug or ''}".lower()
    if any(k in text for k in ["cs2", "csgo", "counter-strike", "counter strike", "dota", "valorant", "league of legends", "lol worlds", "lck", "lpl"]):
        return "Esports"
    if any(k in text for k in ["nba", "nfl", "mlb", "nhl", "soccer", "football", "basketball", "ufc", "mma"]):
        return "Sports"
    if any(k in text for k in ["bitcoin", "btc", "ethereum", "eth", "crypto", "solana"]):
        return "Crypto"
    if any(k in text for k in ["election", "president", "trump", "biden", "harris", "congress", "senate"]):
        return "Politics"
    if any(k in text for k in ["temperature", "weather", "rain", "snow"]):
        return "Weather"
    return "Other"

@st.cache_data(ttl=300)
def load_markets(limit=200):
    resp = requests.get(
        f"{GAMMA_BASE}/markets",
        params={"active": "true", "closed": "false", "limit": limit},
        timeout=30,
    )
    resp.raise_for_status()
    markets = resp.json()
    rows = []
    for m in markets:
        yes_price = None
        try:
            prices = json.loads(m.get("outcomePrices") or "[]")
            yes_price = float(prices[0]) if prices else None
        except Exception:
            pass
        rows.append({
            "category": categorize(m.get("question"), m.get("slug")),
            "question": m.get("question"),
            "slug": m.get("slug"),
            "yes_price": yes_price,
            "volume": float(m.get("volumeNum") or m.get("volume") or 0),
            "end_date": m.get("endDate"),
        })
    return pd.DataFrame(rows)

st.title("Polymarket Dashboard")
st.caption("Markets sorted by category")

if st.button("Pull Markets", type="primary"):
    st.cache_data.clear()

df = load_markets()

if df.empty:
    st.info("No markets returned. Try pulling again.")
else:
    categories = sorted(df["category"].unique())
    tabs = st.tabs(categories)

    for tab, cat in zip(tabs, categories):
        with tab:
            subset = df[df["category"] == cat].sort_values("volume", ascending=False)
            st.subheader(f"{cat} ({len(subset)})")

            display = subset[["question", "yes_price", "volume", "slug"]].copy()
            display["yes_price"] = display["yes_price"].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
            display["volume"] = display["volume"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(display, use_container_width=True, hide_index=True)

            csv = subset.to_csv(index=False).encode("utf-8")
            st.download_button(
                label=f"Export {cat}",
                data=csv,
                file_name=f"polymarket_{cat.lower()}.csv",
                mime="text/csv",
            )
