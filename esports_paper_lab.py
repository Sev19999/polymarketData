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

def categorize(text):
    t = (text or "").lower()
    if any(k in t for k in ["cs2", "csgo", "counter-strike", "dota", "valorant", "league of legends", "lol ", "esport"]):
        return "Esports"
    if any(k in t for k in ["nba", "nfl", "mlb", "nhl", "soccer", "football", "basketball", "ufc", "mma", "tennis", "golf", "f1", "formula"]):
        return "Sports"
    if any(k in t for k in ["bitcoin", "btc", "ethereum", "eth", "crypto", "solana", "sol ", "dogecoin", "xrp"]):
        return "Crypto"
    if any(k in t for k in ["election", "president", "trump", "biden", "harris", "congress", "senate", "governor"]):
        return "Politics"
    if any(k in t for k in ["temperature", "weather", "rain", "snow", "hurricane"]):
        return "Weather"
    if any(k in t for k in ["gold", "oil", "silver", "commodity", "copper", "wheat", "corn"]):
        return "Commodities"
    if any(k in t for k in ["stock", "nasdaq", "s&p", "dow", "earnings", "ipo"]):
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
            "end_date": m.get("endDate"),
        })
    return pd.DataFrame(rows)

@st.cache_data(ttl=600)
def load_sports():
    resp = requests.get(f"{GAMMA_BASE}/sports", timeout=30)
    resp.raise_for_status()
    return resp.json()

st.title("Polymarket Dashboard")
st.caption("Markets by category")

col1, col2 = st.columns(2)
with col1:
    if st.button("Pull Markets", type="primary"):
        st.cache_data.clear()
with col2:
    if st.button("Refresh Sports List"):
        st.cache_data.clear()

# Markets by category
df = load_markets()
if not df.empty:
    cats = ["Esports", "Sports", "Crypto", "Commodities", "Stocks", "Politics", "Weather", "Other"]
    available = [c for c in cats if c in df["category"].unique()]
    tabs = st.tabs(available)
    for tab, cat in zip(tabs, available):
        with tab:
            subset = df[df["category"] == cat].sort_values("volume", ascending=False)
            st.subheader(f"{cat} — {len(subset)} markets")
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
                key=f"export_{cat}",
            )

st.divider()
st.subheader("Sports Leagues")
sports = load_sports()
st.write(f"{len(sports)} leagues available")

# Filter sports by type
sport_cats = {"Esports": [], "Major": [], "Other": []}
for s in sports:
    code = (s.get("sport") or "").lower()
    if any(k in code for k in ["cs2", "csgo", "dota", "lol", "valorant", "esport"]):
        sport_cats["Esports"].append(s)
    elif any(k in code for k in ["nfl", "nba", "mlb", "nhl", "epl", "ufc"]):
        sport_cats["Major"].append(s)
    else:
        sport_cats["Other"].append(s)

sport_tab = st.selectbox("League type", list(sport_cats.keys()))
league_list = sport_cats[sport_tab][:50]
if league_list:
    labels = [f"{s.get('sport','?')} (series {s.get('series','?')})" for s in league_list]
    choice = st.selectbox("League", labels)
    idx = labels.index(choice)
    series_id = league_list[idx].get("series")
    if st.button("Load Games"):
        params = {"series_id": series_id, "active": "true", "closed": "false", "limit": 30}
        resp = requests.get(f"{GAMMA_BASE}/events", params=params, timeout=30)
        events = resp.json() if resp.status_code == 200 else []
        if events:
            rows = [{"title": e.get("title"), "slug": e.get("slug"), "volume": e.get("volume")} for e in events]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No active games for this league right now.")
