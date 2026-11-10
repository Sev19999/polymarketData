import json
import requests
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Polymarket Sports Dashboard",
    page_icon="📊",
    layout="wide",
)

GAMMA_BASE = "https://gamma-api.polymarket.com"

@st.cache_data(ttl=600)
def get_sports():
    resp = requests.get(f"{GAMMA_BASE}/sports", timeout=30)
    resp.raise_for_status()
    return resp.json()

@st.cache_data(ttl=300)
def get_events_for_series(series_id, limit=50):
    if not series_id:
        return []
    params = {
        "series_id": series_id,
        "active": "true",
        "closed": "false",
        "limit": limit,
        "order": "createdAt",
        "ascending": "false",
    }
    resp = requests.get(f"{GAMMA_BASE}/events", params=params, timeout=30)
    if resp.status_code != 200:
        return []
    return resp.json()

def categorize_sport(sport_code):
    code = (sport_code or "").lower()
    esports = ["cs2", "csgo", "dota", "lol", "valorant", "leagueoflegends", "overwatch", "rocketleague"]
    major = ["nfl", "nba", "mlb", "nhl", "epl", "ucl", "ufc", "mma"]
    if any(e in code for e in esports):
        return "Esports"
    if any(m in code for m in major):
        return "Major Sports"
    return "Other Sports"

st.title("Polymarket Sports Dashboard")
st.caption("Automatically discovers sports games via Gamma API")

if st.button("Refresh Sports List", type="primary"):
    st.cache_data.clear()

sports = get_sports()
st.success(f"Found {len(sports)} sports/leagues")

# Group by category
categories = {"Esports": [], "Major Sports": [], "Other Sports": []}
for s in sports:
    cat = categorize_sport(s.get("sport"))
    categories[cat].append(s)

# Let user pick category
cat_choice = st.selectbox("Category", list(categories.keys()))
sport_list = categories[cat_choice]

if not sport_list:
    st.info(f"No sports found in {cat_choice}")
else:
    sport_options = {f"{s.get('sport','?')} (series {s.get('series','?')})": s for s in sport_list[:100]}
    selected_label = st.selectbox("Select a league", list(sport_options.keys()))
    selected = sport_options[selected_label]
    series_id = selected.get("series")

    st.write(f"**Series ID:** {series_id}")

    if st.button("Load Games for this League"):
        with st.spinner("Loading events..."):
            events = get_events_for_series(series_id)
        if not events:
            st.warning("No active events found for this series.")
        else:
            st.subheader(f"{len(events)} Games")
            rows = []
            for e in events:
                rows.append({
                    "title": e.get("title"),
                    "slug": e.get("slug"),
                    "volume": float(e.get("volume") or 0),
                    "end_date": e.get("endDate"),
                    "markets": len(e.get("markets") or []),
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Export this League",
                data=csv,
                file_name=f"polymarket_{selected.get('sport','league')}.csv",
                mime="text/csv",
            )
