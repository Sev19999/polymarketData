import json
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(
    page_title="Esports Paper Lab",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"

session = requests.Session()
session.headers.update({"User-Agent": "EsportsPaperLab/1.0"})

# ── Helpers ────────────────────────────────────────────────────────────────
def get_markets(limit=150):
    params = {"limit": limit, "active": "true", "closed": "false"}
    resp = session.get(f"{GAMMA_BASE}/markets", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()

def classify_game(question, slug):
    text = f"{question or ''} {slug or ''}".lower()
    # Broader but still focused matching
    if any(k in text for k in [
        "league of legends", "lol worlds", "lol msi", "lck", "lpl", "lec", "lcs",
        "worlds", "msi"
    ]):
        return "League of Legends"
    if any(k in text for k in ["valorant", "vct"]):
        return "Valorant"
    if any(k in text for k in ["cs2", "csgo", "counter-strike", "counter strike", "blast", "iem"]):
        return "CS2"
    if any(k in text for k in ["dota", "dota 2", "dota2", "the international"]):
        return "Dota 2"
    return None

def get_price_history(token_id, interval="1d"):
    params = {"market": token_id, "interval": interval}
    resp = session.get(f"{CLOB_BASE}/prices-history", params=params, timeout=30)
    resp.raise_for_status()
    history = resp.json().get("history", [])
    if not history:
        return pd.DataFrame()
    df = pd.DataFrame(history)
    df["datetime"] = pd.to_datetime(df["t"], unit="s", utc=True)
    df = df.rename(columns={"p": "price"})
    return df[["datetime", "price"]].sort_values("datetime")

# ── Sidebar ────────────────────────────────────────────────────────────────
st.sidebar.title("🎮 Esports Paper Lab")
st.sidebar.caption("Polymarket data for LoL, CS2, Valorant & Dota 2")

game_filter = st.sidebar.multiselect(
    "Games",
    ["League of Legends", "CS2", "Valorant", "Dota 2"],
    default=["League of Legends", "CS2", "Valorant", "Dota 2"],
)

if st.sidebar.button("🔄 Refresh Markets", type="primary"):
    st.cache_data.clear()

# ── Load data ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_esports_markets():
    markets = get_markets(limit=200)
    rows = []
    for m in markets:
        game = classify_game(m.get("question"), m.get("slug"))
        if game:
            try:
                tokens = json.loads(m.get("clobTokenIds", "[]"))
                yes_token = tokens[0] if tokens else None
            except Exception:
                yes_token = None
            rows.append({
                "game": game,
                "question": m.get("question"),
                "slug": m.get("slug"),
                "yes_price": json.loads(m.get("outcomePrices", "[]"))[0] if m.get("outcomePrices") else None,
                "volume": float(m.get("volumeNum") or 0),
                "liquidity": float(m.get("liquidityNum") or 0),
                "yes_token": yes_token,
                "end_date": m.get("endDate"),
            })
    return pd.DataFrame(rows)

df = load_esports_markets()

# ── Main UI ────────────────────────────────────────────────────────────────
st.title("Esports Paper Lab")
st.caption("Track League of Legends, CS2, Valorant, and Dota 2 markets on Polymarket")

if df.empty:
    st.info("No active esports markets found right now. These usually appear around major tournaments. Try refreshing later.")
else:
    filtered = df[df["game"].isin(game_filter)].sort_values("volume", ascending=False)

    # Summary cards
    cols = st.columns(4)
    for i, game in enumerate(["League of Legends", "CS2", "Valorant", "Dota 2"]):
        count = len(df[df["game"] == game])
        cols[i].metric(game, f"{count} markets")

    st.subheader("Markets")
    display_df = filtered[["game", "question", "slug", "yes_price", "volume"]].copy()
    display_df["volume"] = display_df["volume"].apply(lambda x: f"${x:,.0f}")
    display_df["yes_price"] = display_df["yes_price"].apply(lambda x: f"{float(x):.3f}" if x else "—")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Market detail
    st.subheader("Market Detail")
    if not filtered.empty:
        options = filtered["slug"].tolist()
        selected_slug = st.selectbox(
            "Select a market",
            options,
            format_func=lambda s: filtered.loc[filtered["slug"] == s, "question"].values[0][:100],
        )
        row = filtered[filtered["slug"] == selected_slug].iloc[0]

        c1, c2, c3 = st.columns(3)
        c1.metric("Game", row["game"])
        c2.metric("Yes Price", f"{float(row['yes_price']):.3f}" if row["yes_price"] else "—")
        c3.metric("Volume", f"${row['volume']:,.0f}")

        if row["yes_token"]:
            with st.spinner("Loading price history..."):
                prices = get_price_history(row["yes_token"], interval="1d")
            if not prices.empty:
                fig = px.line(prices, x="datetime", y="price", title=row["question"])
                fig.update_layout(
                    yaxis_title="Yes Probability",
                    yaxis_range=[0, 1],
                    height=400,
                    margin=dict(l=20, r=20, t=40, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)

                # Simple paper test controls (all adjustable in the app)
                st.subheader("Quick Paper Test")
                
                strategy = st.selectbox(
                    "Strategy",
                    ["Custom (sliders)", "Buy Low / Sell High", "Aggressive", "Conservative"],
                )
                
                if strategy == "Custom (sliders)":
                    buy = st.slider("Buy when price is below", 0.05, 0.50, 0.30, 0.01)
                    sell = st.slider("Sell when price is above", 0.50, 0.95, 0.70, 0.01)
                elif strategy == "Buy Low / Sell High":
                    buy, sell = 0.25, 0.65
                    st.caption("Buy below 0.25 · Sell above 0.65")
                elif strategy == "Aggressive":
                    buy, sell = 0.35, 0.60
                    st.caption("Buy below 0.35 · Sell above 0.60")
                else:  # Conservative
                    buy, sell = 0.20, 0.75
                    st.caption("Buy below 0.20 · Sell above 0.75")

                start_cash = st.number_input("Starting capital ($)", min_value=100, max_value=10000, value=1000, step=100)

                if st.button("Run Test", type="primary"):
                    cash = float(start_cash)
                    pos = 0.0
                    trades = 0
                    for _, r in prices.iterrows():
                        p = r["price"]
                        if pos == 0 and p < buy:
                            pos = cash / p
                            cash = 0
                            trades += 1
                        elif pos > 0 and p > sell:
                            cash = pos * p
                            pos = 0
                            trades += 1
                    if pos > 0:
                        cash = pos * prices["price"].iloc[-1]
                    pnl = cash - start_cash
                    col_a, col_b = st.columns(2)
                    col_a.metric("Final Value", f"${cash:,.0f}")
                    col_b.metric("P&L", f"${pnl:,.0f}", f"{pnl/start_cash*100:+.1f}%")
                    st.caption(f"{trades} trades")
            else:
                st.warning("No price history available for this market yet.")
        else:
            st.warning("No token ID available.")

st.sidebar.markdown("---")
st.sidebar.markdown("Data from Polymarket public APIs")
