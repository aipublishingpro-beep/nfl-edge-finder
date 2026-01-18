import streamlit as st
import requests
from datetime import datetime
import pytz
import json
import os
import time
import uuid

st.set_page_config(page_title="NFL Edge Finder", page_icon="🏈", layout="wide")

# ========== SESSION ID ==========
if "sid" not in st.session_state:
    st.session_state["sid"] = str(uuid.uuid4())

# ========== TIMEZONE ==========
eastern = pytz.timezone("US/Eastern")
today_str = datetime.now(eastern).strftime("%Y-%m-%d")

# ========== CSS ==========
st.markdown("""
<style>
.stLinkButton > a {
    background-color: #00aa00 !important;
    border-color: #00aa00 !important;
    color: white !important;
}
.stLinkButton > a:hover {
    background-color: #00cc00 !important;
    border-color: #00cc00 !important;
}
</style>
""", unsafe_allow_html=True)

# ========== PERSISTENT STORAGE ==========
POSITIONS_FILE = "nfl_positions.json"

def load_positions():
    try:
        if os.path.exists(POSITIONS_FILE):
            with open(POSITIONS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_positions(positions):
    try:
        with open(POSITIONS_FILE, 'w') as f:
            json.dump(positions, f, indent=2)
    except:
        pass

# ========== SESSION STATE ==========
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False
if "positions" not in st.session_state:
    st.session_state.positions = load_positions()
if "selected_ml_pick" not in st.session_state:
    st.session_state.selected_ml_pick = None
if "editing_position" not in st.session_state:
    st.session_state.editing_position = None

# ========== AUTO REFRESH ==========
if st.session_state.auto_refresh:
    st.markdown(f'<meta http-equiv="refresh" content="15;url=?r={int(time.time()) + 15}">', unsafe_allow_html=True)
    auto_status = "🔄 Auto-refresh ON (15s)"
else:
    auto_status = "⏸️ Auto-refresh OFF"

# ========== TEAM DATA ==========
KALSHI_CODES = {
    "Arizona": "ARI", "Atlanta": "ATL", "Baltimore": "BAL", "Buffalo": "BUF",
    "Carolina": "CAR", "Chicago": "CHI", "Cincinnati": "CIN", "Cleveland": "CLE",
    "Dallas": "DAL", "Denver": "DEN", "Detroit": "DET", "Green Bay": "GB",
    "Houston": "HOU", "Indianapolis": "IND", "Jacksonville": "JAX", "Kansas City": "KC",
    "Las Vegas": "LV", "LA Chargers": "LAC", "LA Rams": "LA", "Miami": "MIA",
    "Minnesota": "MIN", "New England": "NE", "New Orleans": "NO", "NY Giants": "NYG",
    "NY Jets": "NYJ", "Philadelphia": "PHI", "Pittsburgh": "PIT", "San Francisco": "SF",
    "Seattle": "SEA", "Tampa Bay": "TB", "Tennessee": "TEN", "Washington": "WAS"
}

TEAM_ABBREVS = {
    "Arizona Cardinals": "Arizona", "Atlanta Falcons": "Atlanta", "Baltimore Ravens": "Baltimore",
    "Buffalo Bills": "Buffalo", "Carolina Panthers": "Carolina", "Chicago Bears": "Chicago",
    "Cincinnati Bengals": "Cincinnati", "Cleveland Browns": "Cleveland", "Dallas Cowboys": "Dallas",
    "Denver Broncos": "Denver", "Detroit Lions": "Detroit", "Green Bay Packers": "Green Bay",
    "Houston Texans": "Houston", "Indianapolis Colts": "Indianapolis", "Jacksonville Jaguars": "Jacksonville",
    "Kansas City Chiefs": "Kansas City", "Las Vegas Raiders": "Las Vegas", "Los Angeles Chargers": "LA Chargers",
    "Los Angeles Rams": "LA Rams", "Miami Dolphins": "Miami", "Minnesota Vikings": "Minnesota",
    "New England Patriots": "New England", "New Orleans Saints": "New Orleans", "New York Giants": "NY Giants",
    "New York Jets": "NY Jets", "Philadelphia Eagles": "Philadelphia", "Pittsburgh Steelers": "Pittsburgh",
    "San Francisco 49ers": "San Francisco", "Seattle Seahawks": "Seattle", "Tampa Bay Buccaneers": "Tampa Bay",
    "Tennessee Titans": "Tennessee", "Washington Commanders": "Washington"
}

# Reverse lookup: short name to Kalshi code
SHORT_TO_KALSHI = {v: k for k, v in KALSHI_CODES.items()}

TEAM_STATS = {
    "Arizona": {"dvoa": -8.5, "def_rank": 28, "home_win_pct": 0.45},
    "Atlanta": {"dvoa": 2.5, "def_rank": 20, "home_win_pct": 0.55},
    "Baltimore": {"dvoa": 12.5, "def_rank": 2, "home_win_pct": 0.72},
    "Buffalo": {"dvoa": 15.8, "def_rank": 4, "home_win_pct": 0.78},
    "Carolina": {"dvoa": -12.5, "def_rank": 26, "home_win_pct": 0.38},
    "Chicago": {"dvoa": 8.5, "def_rank": 10, "home_win_pct": 0.65},
    "Cincinnati": {"dvoa": 5.8, "def_rank": 12, "home_win_pct": 0.58},
    "Cleveland": {"dvoa": -2.5, "def_rank": 15, "home_win_pct": 0.52},
    "Dallas": {"dvoa": 3.2, "def_rank": 14, "home_win_pct": 0.62},
    "Denver": {"dvoa": 12.5, "def_rank": 3, "home_win_pct": 0.75},
    "Detroit": {"dvoa": 18.5, "def_rank": 6, "home_win_pct": 0.75},
    "Green Bay": {"dvoa": 8.2, "def_rank": 10, "home_win_pct": 0.70},
    "Houston": {"dvoa": 6.5, "def_rank": 8, "home_win_pct": 0.58},
    "Indianapolis": {"dvoa": -6.8, "def_rank": 22, "home_win_pct": 0.48},
    "Jacksonville": {"dvoa": -4.5, "def_rank": 19, "home_win_pct": 0.45},
    "Kansas City": {"dvoa": 22.5, "def_rank": 7, "home_win_pct": 0.82},
    "Las Vegas": {"dvoa": -8.2, "def_rank": 25, "home_win_pct": 0.45},
    "LA Chargers": {"dvoa": 7.8, "def_rank": 9, "home_win_pct": 0.55},
    "LA Rams": {"dvoa": 5.5, "def_rank": 14, "home_win_pct": 0.55},
    "Miami": {"dvoa": 5.2, "def_rank": 13, "home_win_pct": 0.62},
    "Minnesota": {"dvoa": 10.5, "def_rank": 11, "home_win_pct": 0.68},
    "New England": {"dvoa": 9.5, "def_rank": 5, "home_win_pct": 0.70},
    "New Orleans": {"dvoa": -3.8, "def_rank": 21, "home_win_pct": 0.55},
    "NY Giants": {"dvoa": -15.5, "def_rank": 30, "home_win_pct": 0.35},
    "NY Jets": {"dvoa": -7.5, "def_rank": 23, "home_win_pct": 0.42},
    "Philadelphia": {"dvoa": 14.8, "def_rank": 3, "home_win_pct": 0.75},
    "Pittsburgh": {"dvoa": 2.8, "def_rank": 5, "home_win_pct": 0.65},
    "San Francisco": {"dvoa": 10.5, "def_rank": 6, "home_win_pct": 0.68},
    "Seattle": {"dvoa": 14.5, "def_rank": 2, "home_win_pct": 0.78},
    "Tampa Bay": {"dvoa": 4.2, "def_rank": 29, "home_win_pct": 0.55},
    "Tennessee": {"dvoa": -9.8, "def_rank": 31, "home_win_pct": 0.42},
    "Washington": {"dvoa": 9.5, "def_rank": 8, "home_win_pct": 0.62}
}

STAR_PLAYERS = {
    "Arizona": ["Kyler Murray"], "Atlanta": ["Kirk Cousins", "Bijan Robinson"],
    "Baltimore": ["Lamar Jackson", "Derrick Henry"], "Buffalo": ["Josh Allen", "James Cook"],
    "Carolina": ["Bryce Young"], "Chicago": ["Caleb Williams"],
    "Cincinnati": ["Joe Burrow", "Ja'Marr Chase"], "Cleveland": ["Deshaun Watson"],
    "Dallas": ["Dak Prescott", "CeeDee Lamb"], "Denver": ["Bo Nix"],
    "Detroit": ["Jared Goff", "Amon-Ra St. Brown"], "Green Bay": ["Jordan Love"],
    "Houston": ["C.J. Stroud", "Nico Collins"], "Indianapolis": ["Anthony Richardson"],
    "Jacksonville": ["Trevor Lawrence"], "Kansas City": ["Patrick Mahomes", "Travis Kelce"],
    "Las Vegas": ["Gardner Minshew"], "LA Chargers": ["Justin Herbert"],
    "LA Rams": ["Matthew Stafford", "Puka Nacua"], "Miami": ["Tua Tagovailoa", "Tyreek Hill"],
    "Minnesota": ["J.J. McCarthy", "Justin Jefferson"], "New England": ["Drake Maye"],
    "New Orleans": ["Derek Carr"], "NY Giants": ["Daniel Jones"],
    "NY Jets": ["Aaron Rodgers"], "Philadelphia": ["Jalen Hurts", "Saquon Barkley"],
    "Pittsburgh": ["Russell Wilson"], "San Francisco": ["Brock Purdy", "Christian McCaffrey"],
    "Seattle": ["Sam Darnold", "Jaxon Smith-Njigba"], "Tampa Bay": ["Baker Mayfield"],
    "Tennessee": ["Will Levis"], "Washington": ["Jayden Daniels"]
}

def build_kalshi_ml_url(away_team, home_team, game_date=None):
    away_code = KALSHI_CODES.get(away_team, "XXX")
    home_code = KALSHI_CODES.get(home_team, "XXX")
    if game_date:
        date_str = game_date.strftime("%y%b%d").upper()
    else:
        date_str = datetime.now(eastern).strftime("%y%b%d").upper()
    ticker = f"KXNFLGAME-{date_str}{away_code}{home_code}"
    return f"https://kalshi.com/markets/KXNFLGAME/{ticker}"

# ========== FOOTBALL FIELD VISUALIZATION ==========
def render_football_field(ball_yard, down, distance, possession_team, away_team, home_team, yards_to_endzone=None, poss_text=None):
    """
    Render football field with ball position.
    ball_yard: 0-100 scale where 0=away endzone, 100=home endzone
    """
    ball_yard = max(0, min(100, ball_yard))
    ball_pct = 10 + (ball_yard / 100) * 80
    
    away_code = KALSHI_CODES.get(away_team, away_team[:3].upper())
    home_code = KALSHI_CODES.get(home_team, home_team[:3].upper())
    
    if down and distance:
        situation = f"{down} & {distance}"
    else:
        situation = "—"
    
    poss_code = KALSHI_CODES.get(possession_team, "???") if possession_team else "???"
    
    # Show ball location text
    if poss_text:
        ball_loc = poss_text
    elif yards_to_endzone:
        ball_loc = f"{yards_to_endzone} to go"
    else:
        ball_loc = ""
    
    field_html = f"""
    <div style="background:#1a1a1a;padding:15px;border-radius:10px;margin:10px 0">
        <div style="display:flex;justify-content:space-between;margin-bottom:8px">
            <span style="color:#ffaa00;font-weight:bold">🏈 {poss_code} Ball</span>
            <span style="color:#aaa">{ball_loc}</span>
            <span style="color:#fff;font-weight:bold">{situation}</span>
        </div>
        <div style="position:relative;height:60px;background:linear-gradient(90deg,#8B0000 0%,#8B0000 10%,#228B22 10%,#228B22 90%,#00008B 90%,#00008B 100%);border-radius:8px;overflow:hidden">
            <div style="position:absolute;left:10%;top:0;bottom:0;width:1px;background:rgba(255,255,255,0.3)"></div>
            <div style="position:absolute;left:20%;top:0;bottom:0;width:1px;background:rgba(255,255,255,0.3)"></div>
            <div style="position:absolute;left:30%;top:0;bottom:0;width:1px;background:rgba(255,255,255,0.3)"></div>
            <div style="position:absolute;left:40%;top:0;bottom:0;width:1px;background:rgba(255,255,255,0.3)"></div>
            <div style="position:absolute;left:50%;top:0;bottom:0;width:2px;background:rgba(255,255,255,0.6)"></div>
            <div style="position:absolute;left:60%;top:0;bottom:0;width:1px;background:rgba(255,255,255,0.3)"></div>
            <div style="position:absolute;left:70%;top:0;bottom:0;width:1px;background:rgba(255,255,255,0.3)"></div>
            <div style="position:absolute;left:80%;top:0;bottom:0;width:1px;background:rgba(255,255,255,0.3)"></div>
            <div style="position:absolute;left:90%;top:0;bottom:0;width:1px;background:rgba(255,255,255,0.3)"></div>
            <div style="position:absolute;left:{ball_pct}%;top:50%;transform:translate(-50%,-50%);font-size:24px;text-shadow:0 0 10px #fff">🏈</div>
            <div style="position:absolute;left:5%;top:50%;transform:translate(-50%,-50%);color:#fff;font-weight:bold;font-size:12px">{away_code}</div>
            <div style="position:absolute;left:95%;top:50%;transform:translate(-50%,-50%);color:#fff;font-weight:bold;font-size:12px">{home_code}</div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:5px;color:#888;font-size:11px">
            <span>← {away_code}</span>
            <span>10</span>
            <span>20</span>
            <span>30</span>
            <span>40</span>
            <span>50</span>
            <span>40</span>
            <span>30</span>
            <span>20</span>
            <span>10</span>
            <span>{home_code} →</span>
        </div>
    </div>
    """
    return field_html

# ========== ESPN DATA ==========
def fetch_espn_scores():
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        games = {}
        for event in data.get("events", []):
            event_id = event.get("id", "")
            comp = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            home_team, away_team, home_score, away_score = None, None, 0, 0
            home_id, away_id = None, None
            home_abbrev, away_abbrev = None, None
            for c in competitors:
                name = c.get("team", {}).get("displayName", "")
                team_name = TEAM_ABBREVS.get(name, name)
                team_id = c.get("team", {}).get("id", "")
                team_abbrev = c.get("team", {}).get("abbreviation", "")
                score = int(c.get("score", 0) or 0)
                if c.get("homeAway") == "home":
                    home_team, home_score, home_id, home_abbrev = team_name, score, team_id, team_abbrev
                else:
                    away_team, away_score, away_id, away_abbrev = team_name, score, team_id, team_abbrev
            
            status_obj = event.get("status", {})
            status_type = status_obj.get("type", {}).get("name", "STATUS_SCHEDULED")
            clock = status_obj.get("displayClock", "")
            period = status_obj.get("period", 0)
            
            # Get situation data
            situation = comp.get("situation", {})
            down = situation.get("down")
            distance = situation.get("distance")
            yard_line = situation.get("yardLine", 50)
            yards_to_endzone = situation.get("yardsToEndzone", 50)
            possession_id = situation.get("possession", "")
            is_red_zone = situation.get("isRedZone", False)
            poss_text = situation.get("possessionText", "")
            down_distance_text = situation.get("downDistanceText", "")
            
            # Determine possession team
            if possession_id == home_id:
                possession_team = home_team
                is_home_possession = True
            elif possession_id == away_id:
                possession_team = away_team
                is_home_possession = False
            else:
                possession_team = None
                is_home_possession = None
            
            # FIXED BALL POSITION CALCULATION
            # Field: 0 = away endzone (left), 100 = home endzone (right)
            # yardsToEndzone = distance from scoring
            # Away team attacks toward 100 (home endzone)
            # Home team attacks toward 0 (away endzone)
            if yards_to_endzone is not None and is_home_possession is not None:
                if is_home_possession:
                    # Home team attacks left (toward 0), so ball is at yardsToEndzone from 0
                    ball_yard = yards_to_endzone
                else:
                    # Away team attacks right (toward 100), so ball is at 100 - yardsToEndzone
                    ball_yard = 100 - yards_to_endzone
            else:
                ball_yard = 50
            
            game_date_str = event.get("date", "")
            try:
                game_date = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
            except:
                game_date = datetime.now(eastern)
            
            game_key = f"{away_team}@{home_team}"
            games[game_key] = {
                "event_id": event_id,
                "away_team": away_team, "home_team": home_team,
                "away_score": away_score, "home_score": home_score,
                "away_id": away_id, "home_id": home_id,
                "away_abbrev": away_abbrev, "home_abbrev": home_abbrev,
                "total": away_score + home_score,
                "period": period, "clock": clock, "status_type": status_type,
                "game_date": game_date,
                "down": down, "distance": distance, "yard_line": yard_line,
                "yards_to_endzone": yards_to_endzone,
                "ball_yard": ball_yard, "possession_team": possession_team,
                "is_red_zone": is_red_zone, "poss_text": poss_text,
                "down_distance_text": down_distance_text
            }
        return games
    except Exception as e:
        st.error(f"ESPN fetch error: {e}")
        return {}

def fetch_espn_injuries():
    injuries = {}
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        for team_data in data.get("injuries", []):
            team_name = team_data.get("displayName", "")
            team_key = TEAM_ABBREVS.get(team_name, team_name)
            if not team_key:
                continue
            injuries[team_key] = []
            for player in team_data.get("injuries", []):
                athlete = player.get("athlete", {})
                name = athlete.get("displayName", "")
                status = player.get("status", "")
                position = athlete.get("position", {}).get("abbreviation", "")
                if name:
                    injuries[team_key].append({"name": name, "status": status, "position": position})
    except:
        pass
    return injuries

# ========== ML SCORING ==========
def get_injury_score(team, injuries):
    team_injuries = injuries.get(team, [])
    stars = STAR_PLAYERS.get(team, [])
    score = 0
    out_players = []
    qb_out = False
    
    for inj in team_injuries:
        name = inj.get("name", "")
        status = inj.get("status", "").upper()
        position = inj.get("position", "").upper()
        is_star = any(star.lower() in name.lower() for star in stars)
        is_qb = position == "QB"
        
        if "OUT" in status:
            if is_qb:
                score += 5.0
                qb_out = True
                out_players.append(f"🚨 {name} (QB)")
            elif is_star:
                score += 2.0
                out_players.append(name)
    
    return score, out_players, qb_out

def calc_ml_score(home_team, away_team, injuries):
    home = TEAM_STATS.get(home_team, {})
    away = TEAM_STATS.get(away_team, {})
    
    score_home, score_away = 0, 0
    reasons_home, reasons_away = [], []
    
    home_dvoa = home.get('dvoa', 0)
    away_dvoa = away.get('dvoa', 0)
    dvoa_diff = home_dvoa - away_dvoa
    if dvoa_diff > 8:
        score_home += 1.0
        reasons_home.append(f"📊 DVOA +{home_dvoa:.1f}")
    elif dvoa_diff < -8:
        score_away += 1.0
        reasons_away.append(f"📊 DVOA +{away_dvoa:.1f}")
    
    home_def = home.get('def_rank', 16)
    away_def = away.get('def_rank', 16)
    if home_def <= 5:
        score_home += 1.0
        reasons_home.append(f"🛡️ #{home_def} DEF")
    if away_def <= 5:
        score_away += 1.0
        reasons_away.append(f"🛡️ #{away_def} DEF")
    
    score_home += 1.0
    
    home_inj, home_out, home_qb_out = get_injury_score(home_team, injuries)
    away_inj, away_out, away_qb_out = get_injury_score(away_team, injuries)
    
    if away_qb_out:
        score_home += 2.5
        reasons_home.append("🏥 QB Out")
    if home_qb_out:
        score_away += 2.5
        reasons_away.append("🏥 QB Out")
    
    home_hw = home.get('home_win_pct', 0.5)
    if home_hw > 0.65:
        score_home += 0.8
        reasons_home.append(f"🏠 {int(home_hw*100)}%")
    
    total = score_home + score_away
    if total > 0:
        home_final = round((score_home / total) * 10, 1)
        away_final = round((score_away / total) * 10, 1)
    else:
        home_final, away_final = 5.0, 5.0
    
    if home_final >= away_final:
        return home_team, home_final, reasons_home[:4], home_out, away_out
    else:
        return away_team, away_final, reasons_away[:4], home_out, away_out

def get_signal_tier(score):
    if score >= 8.0:
        return "🟢 STRONG BUY", "#00ff00"
    elif score >= 6.5:
        return "🔵 BUY", "#00aaff"
    elif score >= 5.5:
        return "🟡 LEAN", "#ffff00"
    else:
        return "⚪ TOSS-UP", "#888888"

# ========== FETCH DATA ==========
games = fetch_espn_scores()
game_list = sorted(list(games.keys()))
injuries = fetch_espn_injuries()
now = datetime.now(eastern)

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("⚡ LiveState")
    st.caption("Pre-resolution stress detection")
    st.markdown("""
| State | Price Move |
|-------|------------|
| 🔴 **MAX** | 3-7¢ |
| 🟠 **ELEVATED** | 1-4¢ |
| 🟢 **NORMAL** | — |
""")
    st.divider()
    st.header("📖 ML LEGEND")
    st.markdown("🟢 **STRONG** → 8.0+\n\n🔵 **BUY** → 6.5-7.9\n\n🟡 **LEAN** → 5.5-6.4")
    st.divider()
    st.caption("v1.7 NFL EDGE")

# ========== TITLE ==========
st.title("🏈 NFL EDGE FINDER")
st.caption("Pre-game picks + LiveState in-game stress detection")

# ========== LIVESTATE ==========
live_games = {k: v for k, v in games.items() if v['period'] > 0 and v['status_type'] != "STATUS_FINAL"}
final_games = {k: v for k, v in games.items() if v['status_type'] == "STATUS_FINAL"}

if live_games or final_games:
    st.subheader("⚡ LiveState — Live Uncertainty Tracker")
    st.caption("Pre-resolution stress detection • Not predictions • Not play-by-play")
    
    hdr1, hdr2, hdr3 = st.columns([3, 1, 1])
    hdr1.caption(f"{auto_status} | {now.strftime('%I:%M:%S %p ET')} | v1.7")
    if hdr2.button("🔄 Auto" if not st.session_state.auto_refresh else "⏹️ Stop", use_container_width=True, key="auto_live"):
        st.session_state.auto_refresh = not st.session_state.auto_refresh
        st.rerun()
    if hdr3.button("🔄 Now", use_container_width=True, key="refresh_live"):
        st.query_params["r"] = str(int(time.time()))
        st.rerun()
    
    # FINAL GAMES
    for game_key, g in final_games.items():
        parts = game_key.split("@")
        winner = parts[1] if g['home_score'] > g['away_score'] else parts[0]
        winner_code = KALSHI_CODES.get(winner, winner[:3].upper())
        
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1a2e1a,#0a1e0a);padding:18px;border-radius:12px;border:2px solid #44ff44;margin-bottom:15px">
            <div style="text-align:center">
                <b style="color:#fff;font-size:1.4em">{g['away_team']} {g['away_score']} @ {g['home_team']} {g['home_score']}</b>
                <span style="color:#44ff44;margin-left:20px;font-size:1.2em">✅ RESOLVED</span>
            </div>
            <div style="background:#000;padding:12px;border-radius:8px;margin-top:12px;text-align:center">
                <span style="color:#44ff44;font-size:1.2em">FINAL | {winner_code} WIN | Uncertainty resolved</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # LIVE GAMES
    for game_key, g in live_games.items():
        quarter = g['period']
        clock_str = g['clock']
        away_score = g['away_score']
        home_score = g['home_score']
        score_diff = abs(home_score - away_score)
        
        if score_diff >= 17:
            score_pressure = "Blowout"
        elif score_diff >= 9:
            score_pressure = "Two Poss"
        else:
            score_pressure = "One Poss"
        
        if quarter >= 5:
            state_label = "MAX UNCERTAINTY"
            state_color = "#ff0000"
            expected_leak = "3-7¢"
            q_display = "🏈 OVERTIME"
            clock_pressure = "🚨 OVERTIME"
        elif quarter == 4 and score_diff <= 8:
            state_label = "ELEVATED"
            state_color = "#ffaa00"
            expected_leak = "1-4¢"
            q_display = f"Q{quarter}"
            clock_pressure = "Q4 Crunch"
        else:
            state_label = "NORMAL"
            state_color = "#44ff44"
            expected_leak = "—"
            q_display = f"Q{quarter}"
            clock_pressure = f"Q{quarter}"
        
        if g.get('is_red_zone'):
            clock_pressure += " 🔴 RED ZONE"
        
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1a1a2e,#0a0a1e);padding:18px;border-radius:12px;border:2px solid {state_color};margin-bottom:15px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                <div style="flex:1"></div>
                <div style="text-align:center;flex:2">
                    <b style="color:#fff;font-size:1.4em">{g['away_team']} {away_score} @ {g['home_team']} {home_score}</b>
                </div>
                <div style="text-align:right;flex:1">
                    <b style="color:{state_color};font-size:1.4em">{state_label}</b>
                    <div style="color:#888;font-size:0.85em">Price Move: {expected_leak}</div>
                </div>
            </div>
            <div style="background:#000;padding:15px;border-radius:8px;text-align:center">
                <span style="color:{state_color};font-size:1.3em;font-weight:bold">{q_display} {clock_str}</span>
            </div>
            <div style="text-align:center;margin-top:12px">
                <span style="color:{state_color};font-size:1.1em">{clock_pressure}</span> • 
                <span style="color:#ffaa44;font-size:1.1em">{score_pressure}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Football field visualization
        parts = game_key.split("@")
        field_html = render_football_field(
            g.get('ball_yard', 50),
            g.get('down'),
            g.get('distance'),
            g.get('possession_team'),
            parts[0],
            parts[1],
            g.get('yards_to_endzone'),
            g.get('poss_text')
        )
        st.markdown(field_html, unsafe_allow_html=True)
        
        kalshi_url = build_kalshi_ml_url(parts[0], parts[1], g.get('game_date'))
        st.link_button(f"🔗 Trade {game_key.replace('@', ' @ ')}", kalshi_url, use_container_width=True)
    
    st.divider()

# ========== ACTIVE POSITIONS ==========
st.subheader("📈 ACTIVE POSITIONS")

if not live_games and not final_games:
    hdr1, hdr2, hdr3 = st.columns([3, 1, 1])
    hdr1.caption(f"{auto_status} | {now.strftime('%I:%M:%S %p ET')} | v1.7")
    if hdr2.button("🔄 Auto" if not st.session_state.auto_refresh else "⏹️ Stop", use_container_width=True, key="auto_pos"):
        st.session_state.auto_refresh = not st.session_state.auto_refresh
        st.rerun()
    if hdr3.button("🔄 Refresh", use_container_width=True, key="refresh_pos"):
        st.query_params["r"] = str(int(time.time()))
        st.rerun()

if st.session_state.positions:
    for idx, pos in enumerate(st.session_state.positions):
        game_key = pos['game']
        g = games.get(game_key)
        price = pos.get('price', 50)
        contracts = pos.get('contracts', 1)
        cost = round(price * contracts / 100, 2)
        potential_win = round((100 - price) * contracts / 100, 2)
        
        if g:
            pick = pos.get('pick', '')
            parts = game_key.split("@")
            away_team, home_team = parts[0], parts[1]
            home_score, away_score = g['home_score'], g['away_score']
            pick_score = home_score if pick == home_team else away_score
            opp_score = away_score if pick == home_team else home_score
            lead = pick_score - opp_score
            is_final = g['status_type'] == "STATUS_FINAL"
            game_status = "FINAL" if is_final else f"Q{g['period']} {g['clock']}" if g['period'] > 0 else "SCHEDULED"
            
            if is_final:
                won = pick_score > opp_score
                status_label = "✅ WON!" if won else "❌ LOST"
                status_color = "#00ff00" if won else "#ff0000"
                pnl = f"+${potential_win:.2f}" if won else f"-${cost:.2f}"
                pnl_color = "#00ff00" if won else "#ff0000"
            elif g['period'] > 0:
                if lead >= 14:
                    status_label, status_color = "🟢 CRUISING", "#00ff00"
                elif lead >= 7:
                    status_label, status_color = "🟢 LEADING", "#00ff00"
                elif lead >= 1:
                    status_label, status_color = "🟡 AHEAD", "#ffff00"
                elif lead >= -7:
                    status_label, status_color = "🟠 CLOSE", "#ff8800"
                else:
                    status_label, status_color = "🔴 BEHIND", "#ff0000"
                pnl, pnl_color = f"Win: +${potential_win:.2f}", "#888"
            else:
                status_label, status_color = "⏳ SCHEDULED", "#888"
                lead = 0
                pnl, pnl_color = f"Win: +${potential_win:.2f}", "#888"
            
            st.markdown(f"""<div style='background:linear-gradient(135deg,#1a1a2e,#16213e);padding:15px;border-radius:10px;border:2px solid {status_color};margin-bottom:10px'>
            <div style='display:flex;justify-content:space-between'>
            <div><b style='color:#fff;font-size:1.2em'>{game_key.replace('@', ' @ ')}</b> <span style='color:#888'>{game_status}</span></div>
            <b style='color:{status_color};font-size:1.3em'>{status_label}</b>
            </div>
            <div style='margin-top:10px;color:#aaa'>🎯 Pick: <b style='color:#fff'>{pick}</b> | 💵 {contracts}x @ {price}¢ (${cost:.2f}) | 📊 {pick_score}-{opp_score} | Lead: <b style='color:{status_color}'>{lead:+d}</b> | <span style='color:{pnl_color}'>{pnl}</span></div></div>""", unsafe_allow_html=True)
            
            btn1, btn2, btn3 = st.columns([3, 1, 1])
            kalshi_url = build_kalshi_ml_url(parts[0], parts[1], g.get('game_date'))
            btn1.link_button("🔗 Trade on Kalshi", kalshi_url, use_container_width=True)
            if btn2.button("✏️", key=f"edit_{idx}"):
                st.session_state.editing_position = idx if st.session_state.editing_position != idx else None
                st.rerun()
            if btn3.button("🗑️", key=f"del_{idx}"):
                st.session_state.positions.pop(idx)
                save_positions(st.session_state.positions)
                st.rerun()
            
            if st.session_state.editing_position == idx:
                e1, e2, e3 = st.columns(3)
                new_price = e1.number_input("Entry ¢", min_value=1, max_value=99, value=pos.get('price', 50), key=f"price_{idx}")
                new_contracts = e2.number_input("Contracts", min_value=1, value=pos.get('contracts', 1), key=f"contracts_{idx}")
                pick_options = [parts[1], parts[0]]
                current_pick = pos.get('pick', parts[1])
                pick_idx = pick_options.index(current_pick) if current_pick in pick_options else 0
                new_pick = e3.radio("Pick", pick_options, index=pick_idx, horizontal=True, key=f"pick_{idx}")
                
                if st.button("💾 Save", key=f"save_{idx}", type="primary"):
                    st.session_state.positions[idx]['price'] = new_price
                    st.session_state.positions[idx]['contracts'] = new_contracts
                    st.session_state.positions[idx]['pick'] = new_pick
                    st.session_state.editing_position = None
                    save_positions(st.session_state.positions)
                    st.rerun()
    
    if st.button("🗑️ Clear All", use_container_width=True):
        st.session_state.positions = []
        save_positions(st.session_state.positions)
        st.rerun()
else:
    st.info("No positions — add below")

st.divider()

# ========== ML PICKS ==========
st.subheader("🎯 PRE-GAME ML PICKS")

ml_results = []
for game_key, g in games.items():
    if g['status_type'] != "STATUS_SCHEDULED":
        continue
    away = g["away_team"]
    home = g["home_team"]
    try:
        pick, score, reasons, home_out, away_out = calc_ml_score(home, away, injuries)
        tier, color = get_signal_tier(score)
        ml_results.append({
            "pick": pick, "score": score, "color": color, "reasons": reasons,
            "away": away, "home": home, "game_date": g.get('game_date'), "game_key": game_key
        })
    except:
        continue

ml_results.sort(key=lambda x: x["score"], reverse=True)

if ml_results:
    for r in ml_results:
        if r["score"] < 5.5:
            continue
        
        pick_team = r["pick"]
        pick_code = KALSHI_CODES.get(pick_team, pick_team[:3].upper())
        opponent = r["away"] if pick_team == r["home"] else r["home"]
        reasons_str = " • ".join(r["reasons"])
        
        away_code = KALSHI_CODES.get(r["away"], "XXX")
        home_code = KALSHI_CODES.get(r["home"], "XXX")
        date_str = r["game_date"].strftime("%y%b%d").upper() if r["game_date"] else datetime.now(eastern).strftime("%y%b%d").upper()
        ticker = f"KXNFLGAME-{date_str}{away_code}{home_code}"
        this_url = f"https://kalshi.com/markets/KXNFLGAME/{ticker}"
        
        st.markdown(f"""<div style="background:linear-gradient(135deg,#0f172a,#020617);padding:8px 12px;margin-bottom:2px;border-radius:6px;border-left:3px solid {r['color']}">
        <b style="color:#fff">{pick_team}</b> <span style="color:#666">vs {opponent}</span> 
        <span style="color:#38bdf8">{r['score']}/10</span> 
        <span style="color:#777;font-size:0.8em">{reasons_str}</span></div>""", unsafe_allow_html=True)
        
        st.link_button(f"BUY {pick_code}", this_url, use_container_width=True)
else:
    st.info("No scheduled games with picks")

st.divider()

# ========== ADD POSITION ==========
st.subheader("➕ ADD POSITION")

game_options = ["Select..."] + [gk.replace("@", " @ ") for gk in game_list]
selected_game = st.selectbox("Game", game_options)

if selected_game != "Select...":
    parts = selected_game.replace(" @ ", "@").split("@")
    g = games.get(f"{parts[0]}@{parts[1]}")
    game_date = g.get('game_date') if g else None
    st.link_button("🔗 View on Kalshi", build_kalshi_ml_url(parts[0], parts[1], game_date), use_container_width=True)

p1, p2, p3 = st.columns(3)
with p1:
    if selected_game != "Select...":
        parts = selected_game.replace(" @ ", "@").split("@")
        st.session_state.selected_ml_pick = st.radio("Pick", [parts[1], parts[0]], horizontal=True)

price_paid = p2.number_input("Price ¢", min_value=1, max_value=99, value=50)
contracts = p3.number_input("Contracts", min_value=1, value=1)

if st.button("✅ ADD", use_container_width=True, type="primary"):
    if selected_game == "Select...":
        st.error("Select a game!")
    else:
        game_key = selected_game.replace(" @ ", "@")
        st.session_state.positions.append({
            "game": game_key,
            "type": "ml",
            "pick": st.session_state.selected_ml_pick,
            "price": price_paid,
            "contracts": contracts,
            "cost": round(price_paid * contracts / 100, 2),
            "added_at": now.strftime("%a %I:%M %p")
        })
        save_positions(st.session_state.positions)
        st.rerun()

st.divider()

# ========== ALL GAMES ==========
st.subheader("📺 ALL GAMES")
if games:
    cols = st.columns(4)
    for i, (k, g) in enumerate(games.items()):
        with cols[i % 4]:
            st.write(f"**{g['away_team']}** {g['away_score']}")
            st.write(f"**{g['home_team']}** {g['home_score']}")
            if g['status_type'] == "STATUS_FINAL":
                status = "FINAL"
            elif g['period'] > 0:
                status = f"Q{g['period']} {g['clock']}"
            else:
                status = "SCHEDULED"
            st.caption(f"{status} | {g['total']} pts")
else:
    st.info("No games this week")

st.divider()
st.caption("⚠️ Educational analysis only. Not financial advice. v1.7")
