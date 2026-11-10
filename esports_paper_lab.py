import requests
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Esports Paper Lab",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Cito API ───────────────────────────────────────────────────────────────
CITO_BASE = "https://api.citoapi.com/api/v1"
CITO_KEY = st.secrets.get("CITO_KEY", "cito_b43929ae57aa2db93f36e49335d574d2241a36460cce889ccc8d23462183dd47")

session = requests.Session()
session.headers.update({"x-api-key": CITO_KEY})

def get_upcoming(game="cs2", limit=20):
    url = f"{CITO_BASE}/{game}/matches/upcoming"
    resp = session.get(url, params={"limit": limit}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])

def get_live(game="cs2", limit=10):
    url = f"{CITO_BASE}/{game}/matches/live"
    resp = session.get(url, params={"limit": limit}, timeout=30)
    if resp.status_code != 200:
        return []
    return resp.json().get("data", [])

# ── Sidebar ────────────────────────────────────────────────────────────────
st.sidebar.title("🎮 Esports Paper Lab")
st.sidebar.caption("Powered by Cito API")

game = st.sidebar.selectbox(
    "Game",
    ["cs2", "dota2", "lol"],
    format_func=lambda x: {"cs2": "CS2", "dota2": "Dota 2", "lol": "League of Legends"}[x],
)

if st.sidebar.button("🔄 Refresh", type="primary"):
    st.cache_data.clear()

# ── Load data ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_matches(game):
    upcoming = get_upcoming(game, limit=25)
    live = get_live(game, limit=10)
    return upcoming, live

upcoming, live = load_matches(game)

# ── Main UI ────────────────────────────────────────────────────────────────
game_name = {"cs2": "CS2", "dota2": "Dota 2", "lol": "League of Legends"}[game]
st.title(f"{game_name} Matches")

if live:
    st.subheader("🔴 Live")
    live_rows = []
    for m in live:
        live_rows.append({
            "Match": f"{m.get('team1Name','?')} vs {m.get('team2Name','?')}",
            "Score": f"{m.get('team1Score',0)} - {m.get('team2Score',0)}",
            "Event": m.get("eventName", ""),
            "Best of": m.get("bestOf", ""),
        })
    st.dataframe(pd.DataFrame(live_rows), use_container_width=True, hide_index=True)

st.subheader("Upcoming")
if not upcoming:
    st.info("No upcoming matches found.")
else:
    rows = []
    for m in upcoming:
        rows.append({
            "Match": f"{m.get('team1Name','?')} vs {m.get('team2Name','?')}",
            "Event": m.get("eventName", ""),
            "Starts": m.get("startsAt", "")[:16].replace("T", " ") if m.get("startsAt") else "",
            "Best of": m.get("bestOf", ""),
            "ID": m.get("id", ""),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)

    # Simple selection for more detail
    st.subheader("Match Detail")
    options = [f"{r['Match']} ({r['Event']})" for r in rows]
    choice = st.selectbox("Select a match", options)
    idx = options.index(choice)
    match = upcoming[idx]

    c1, c2, c3 = st.columns(3)
    c1.metric("Team 1", match.get("team1Name", "—"))
    c2.metric("Team 2", match.get("team2Name", "—"))
    c3.metric("Best of", match.get("bestOf", "—"))

    if match.get("streamLinks"):
        st.caption("Stream: " + match["streamLinks"][0].get("url", ""))

st.sidebar.markdown("---")
st.sidebar.caption("Data from Cito API")
