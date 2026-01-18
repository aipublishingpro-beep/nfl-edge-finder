import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz
import json
import os
import time
import uuid

st.set_page_config(page_title="NFL Edge Finder", page_icon="🏈", layout="wide")

# ========== SESSION ID FOR DIAGNOSTICS ==========
if "sid" not in st.session_state:
    st.session_state["sid"] = str(uuid.uuid4())

DIAGNOSTICS_FILE = "diagnostics_log.json"

def log_diagnostic(action):
    record = {
        "timestamp": datetime.now().isoformat(),
        "sid": st.session_state["sid"],
        "action": action
    }
    try:
        logs = []
        if os.path.exists(DIAGNOSTICS_FILE):
            with open(DIAGNOSTICS_FILE, 'r') as f:
                logs = json.load(f)
        logs.append(record)
        with open(DIAGNOSTICS_FILE, 'w') as f:
            json.dump(logs, f, indent=2)
    except:
        pass

# ========== DAILY DATE KEY ==========
eastern = pytz.timezone("US/Eastern")
today_str = datetime.now(eastern).strftime("%Y-%m-%d")

# Fixed CSS
st.markdown("""
<style>
div[role="radiogroup"] label { cursor: pointer; }
div[role="radiogroup"] label span {
    padding: 8px 18px;
    border-radius: 10px;
    display: inline-block;
    font-weight: 700;
}
div[role="radiogroup"] input:checked + div span { box-shadow: inset 0 0 0 2px white; }
div[role="radiogroup"] label:nth-of-type(1) span {
    background: linear-gradient(135deg, #102a1a, #163a26);
    border: 2px solid #00ff88;
    color: #ccffee;
}
div[role="radiogroup"] label:nth-of-type(2) span {
    background: linear-gradient(135deg, #2a1515, #3a1a1a);
    border: 2px solid #ff4444;
    color: #ffcccc;
}
.stLinkButton > a {
    background-color: #00aa00 !important;
    border-color: #00aa00 !important;
    color: white !important;
}
.stLinkButton > a:hover {
    background-color: #00cc00 !important;
    border-color: #00cc00 !important;
}
.uncertainty-max {
    background: linear-gradient(135deg, #4a1a1a, #2a0a0a) !important;
    border: 2px solid #ff4444 !important;
    animation: pulse-red 1.5s infinite;
}
.uncertainty-elevated {
    background: linear-gradient(135deg, #4a3a1a, #2a2a0a) !important;
    border: 2px solid #ffaa00 !important;
}
@keyframes pulse-red {
    0%, 100% { box-shadow: 0 0 5px #ff4444; }
    50% { box-shadow: 0 0 20px #ff4444; }
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

# ========== SESSION STATE INIT ==========
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False
if "positions" not in st.session_state:
    st.session_state.positions = load_positions()
if "selected_ml_pick" not in st.session_state:
    st.session_state.selected_ml_pick = None
if "editing_position" not in st.session_state:
    st.session_state.editing_position = None
if "livestate_prev" not in st.session_state:
    st.session_state.livestate_prev = {}

# ========== DATE INVALIDATION ==========
if "snapshot_date" not in st.session_state or st.session_state["snapshot_date"] != today_str:
    st.session_state["snapshot_date"] = today_str

if st.session_state.auto_refresh:
    cache_buster = int(time.time()) + 15
    st.markdown(f'<meta http-equiv="refresh" content="15;url=?r={cache_buster}">', unsafe_allow_html=True)
    auto_status = "🔄 Auto-refresh ON (15s)"
else:
    auto_status = "⏸️ Auto-refresh OFF"

# ========== KALSHI TEAM CODES ==========
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

def build_kalshi_ml_url(away_team, home_team, game_date=None):
    away_code = KALSHI_CODES.get(away_team, "XXX")
    home_code = KALSHI_CODES.get(home_team, "XXX")
    if game_date:
        date_str = game_date.strftime("%y%b%d").upper()
    else:
        today = datetime.now(eastern)
        date_str = today.strftime("%y%b%d").upper()
    ticker = f"KXNFLGAME-{date_str}{away_code}{home_code}"
    return f"https://kalshi.com/markets/KXNFLGAME/{ticker}"

# ========== NFL TEAM DATA ==========
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

# ========== UNCERTAINTY DETECTION ENGINE ==========

def normalize_yardline(yard_line, poss_team, home_team, is_red_zone=False):
    """
    Normalize yardline to distance-to-opponent-end-zone (0-100 scale).
    0 = own goal line, 100 = opponent goal line.
    ESPN yardLine is raw field position (0-50), need context to normalize.
    """
    if yard_line is None:
        return 50  # Default to midfield if unknown
    
    # ESPN red zone flag is reliable when present
    if is_red_zone:
        return max(80, 100 - yard_line)
    
    # If yardline > 50, ESPN already normalized it in some endpoints
    if yard_line > 50:
        return yard_line
    
    # Conservative: without possession side info, assume midfield-ish
    # This avoids false Red Zone / Own Deep classifications
    return yard_line + 50 if yard_line <= 25 else yard_line

def get_field_position_band(yardline_100):
    """Convert normalized yardline to descriptive band"""
    if yardline_100 < 25:
        return "Own Deep", "#ff4444"
    elif yardline_100 < 40:
        return "Own Side", "#ff8844"
    elif yardline_100 < 60:
        return "Midfield", "#ffff44"
    elif yardline_100 < 80:
        return "Opp Side", "#88ff44"
    else:
        return "Red Zone", "#44ff44"

def get_score_pressure(score_diff):
    """Categorize score differential"""
    if abs(score_diff) >= 17:
        return "Blowout", "#888888"
    elif abs(score_diff) >= 9:
        return "Two Poss", "#ffaa44"
    else:
        return "One Poss", "#ff4444"

def get_clock_pressure(quarter, clock_seconds):
    """Determine clock urgency"""
    if quarter <= 2:
        return "Low", "#44ff44"
    elif quarter == 3:
        return "Medium", "#ffff44"
    else:
        if clock_seconds <= 120:
            return "CRITICAL", "#ff0000"
        elif clock_seconds <= 300:
            return "High", "#ff4444"
        elif clock_seconds <= 480:
            return "Elevated", "#ff8844"
        else:
            return "Medium", "#ffaa44"

def calculate_uncertainty(down, yards_to_go, yardline_100, quarter, clock_seconds, 
                          score_diff, had_turnover=False, prev_score_pressure=None):
    """
    Core uncertainty formula - detects pre-resolution stress points
    where markets historically soften BEFORE the play outcome.
    
    Uses ONLY snap-to-snap variables. Returns raw score (internal only)
    and trigger list. Raw score NEVER displayed - only state labels.
    """
    uncertainty = 0
    triggers = []
    
    # Down-Based Triggers
    if down == 3 and yards_to_go >= 7:
        uncertainty += 1
        triggers.append(f"3rd & Long ({yards_to_go})")
    
    if down == 4:
        uncertainty += 2
        triggers.append("4th Down Decision")
    
    # Field + Down Combo (high value)
    if down >= 3 and yardline_100 >= 40:
        uncertainty += 2
        triggers.append(f"Conversion Territory")
    
    # Red Zone Volatility
    if yardline_100 >= 80 and down >= 2:
        uncertainty += 1
        triggers.append("Red Zone Pressure")
    
    # End-of-Quarter State
    if clock_seconds <= 120:
        uncertainty += 1
        triggers.append(f"2-Min Warning Zone")
    
    # Sudden Change Setup (turnover + good field)
    if had_turnover and yardline_100 >= 40:
        uncertainty += 2
        triggers.append("Sudden Change")
    
    # Score Transition Detection (the 6¢ insight)
    current_pressure, _ = get_score_pressure(score_diff)
    if prev_score_pressure == "Two Poss" and current_pressure == "One Poss":
        uncertainty += 2
        triggers.append("Score Compression!")
    
    # Goal-to-go situations
    if yardline_100 >= 90 and down <= 3:
        uncertainty += 1
        triggers.append("Goal Line")
    
    # Late game + close + 4th quarter
    if quarter == 4 and abs(score_diff) <= 8 and clock_seconds <= 300:
        uncertainty += 2
        triggers.append("Crunch Time")
    
    return uncertainty, triggers

def get_uncertainty_state(uncertainty_score):
    """Convert score to actionable state"""
    if uncertainty_score >= 4:
        return "MAX UNCERTAINTY", "#ff0000", "3-7¢"
    elif uncertainty_score >= 2:
        return "ELEVATED", "#ffaa00", "1-4¢"
    else:
        return "NORMAL", "#44ff44", "—"

def fetch_live_situation(event_id):
    """
    Fetch detailed play-by-play situation from ESPN.
    Returns ONLY snap-to-snap variables for LiveState.
    
    NFL uses plays endpoint, not situation object in summary.
    """
    try:
        # NFL uses the plays endpoint for live data
        plays_url = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{event_id}/competitions/{event_id}/plays?limit=10"
        resp = requests.get(plays_url, timeout=8)
        data = resp.json()
        
        items = data.get("items", [])
        if not items:
            return None
        
        # Get most recent play
        last_play = items[-1] if items else {}
        
        # Extract situation from last play
        down = last_play.get("start", {}).get("down", 0)
        distance = last_play.get("start", {}).get("distance", 0)
        raw_yardline = last_play.get("start", {}).get("yardLine", 50)
        quarter = last_play.get("period", {}).get("number", 0)
        clock_str = last_play.get("clock", {}).get("displayValue", "15:00")
        
        # Parse clock to seconds
        try:
            parts = clock_str.split(":")
            clock_seconds = int(parts[0]) * 60 + int(parts[1])
        except:
            clock_seconds = 900
        
        # Get team info
        poss_team_data = last_play.get("start", {}).get("team", {})
        poss_team_name = poss_team_data.get("displayName", "")
        poss_team = TEAM_ABBREVS.get(poss_team_name, poss_team_name)
        
        # Determine if it's a red zone situation
        is_red_zone = last_play.get("start", {}).get("yardsToEndzone", 100) <= 20
        yardline_100 = 100 - last_play.get("start", {}).get("yardsToEndzone", 50)
        
        # Check for turnover
        play_type = last_play.get("type", {}).get("text", "")
        had_turnover = "intercept" in play_type.lower() or "fumble" in play_type.lower()
        
        # Now get scores from scoreboard (we already have this data)
        # We'll need to pass it in or fetch separately
        # For now, return what we have
        
        return {
            "possession_team": poss_team,
            "defense_team": "",  # Will determine from game data
            "quarter": quarter,
            "clock_seconds": clock_seconds,
            "clock_display": clock_str,
            "down": down,
            "yards_to_go": distance,
            "yardline_100": yardline_100,
            "score_offense": 0,  # Will get from game data
            "score_defense": 0,
            "timeouts_offense": 3,
            "timeouts_defense": 3,
            "had_turnover": had_turnover,
            "home_team": "",
            "away_team": "",
            "home_score": 0,
            "away_score": 0,
            "play_text": last_play.get("text", "")
        }
    except Exception as e:
        return None

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
            for c in competitors:
                name = c.get("team", {}).get("displayName", "")
                team_name = TEAM_ABBREVS.get(name, name)
                score = int(c.get("score", 0) or 0)
                if c.get("homeAway") == "home":
                    home_team, home_score = team_name, score
                else:
                    away_team, away_score = team_name, score
            status_obj = event.get("status", {})
            status_type = status_obj.get("type", {}).get("name", "STATUS_SCHEDULED")
            clock = status_obj.get("displayClock", "")
            period = status_obj.get("period", 0)
            
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
                "total": away_score + home_score,
                "period": period, "clock": clock, "status_type": status_type,
                "game_date": game_date
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
        injury_list = data.get("injuries", [])
        for team_data in injury_list:
            team_name = team_data.get("displayName", "")
            team_key = TEAM_ABBREVS.get(team_name, team_name)
            if not team_key:
                continue
            injuries[team_key] = []
            player_list = team_data.get("injuries", [])
            for player in player_list:
                athlete = player.get("athlete", {})
                name = athlete.get("displayName", "")
                status = player.get("status", "")
                position = athlete.get("position", {}).get("abbreviation", "")
                if name:
                    injuries[team_key].append({"name": name, "status": status, "position": position})
    except Exception as e:
        st.sidebar.error(f"Injury fetch error: {e}")
    return injuries

# Simplified team stats (keeping essential data)
TEAM_STATS = {
    "Arizona": {"dvoa": -8.5, "def_rank": 28, "home_win_pct": 0.45},
    "Atlanta": {"dvoa": 2.5, "def_rank": 20, "home_win_pct": 0.55},
    "Baltimore": {"dvoa": 12.5, "def_rank": 2, "home_win_pct": 0.72},
    "Buffalo": {"dvoa": 15.8, "def_rank": 4, "home_win_pct": 0.78},
    "Carolina": {"dvoa": -12.5, "def_rank": 26, "home_win_pct": 0.38},
    "Chicago": {"dvoa": -5.2, "def_rank": 18, "home_win_pct": 0.48},
    "Cincinnati": {"dvoa": 5.8, "def_rank": 12, "home_win_pct": 0.58},
    "Cleveland": {"dvoa": -2.5, "def_rank": 15, "home_win_pct": 0.52},
    "Dallas": {"dvoa": 3.2, "def_rank": 14, "home_win_pct": 0.62},
    "Denver": {"dvoa": 4.5, "def_rank": 8, "home_win_pct": 0.68},
    "Detroit": {"dvoa": 18.5, "def_rank": 6, "home_win_pct": 0.75},
    "Green Bay": {"dvoa": 8.2, "def_rank": 10, "home_win_pct": 0.70},
    "Houston": {"dvoa": 6.5, "def_rank": 16, "home_win_pct": 0.58},
    "Indianapolis": {"dvoa": -6.8, "def_rank": 22, "home_win_pct": 0.48},
    "Jacksonville": {"dvoa": -4.5, "def_rank": 19, "home_win_pct": 0.45},
    "Kansas City": {"dvoa": 22.5, "def_rank": 7, "home_win_pct": 0.82},
    "Las Vegas": {"dvoa": -8.2, "def_rank": 25, "home_win_pct": 0.45},
    "LA Chargers": {"dvoa": 7.8, "def_rank": 9, "home_win_pct": 0.55},
    "LA Rams": {"dvoa": 1.5, "def_rank": 17, "home_win_pct": 0.52},
    "Miami": {"dvoa": 5.2, "def_rank": 13, "home_win_pct": 0.62},
    "Minnesota": {"dvoa": 10.5, "def_rank": 11, "home_win_pct": 0.68},
    "New England": {"dvoa": -10.5, "def_rank": 24, "home_win_pct": 0.42},
    "New Orleans": {"dvoa": -3.8, "def_rank": 21, "home_win_pct": 0.55},
    "NY Giants": {"dvoa": -15.5, "def_rank": 30, "home_win_pct": 0.35},
    "NY Jets": {"dvoa": -7.5, "def_rank": 23, "home_win_pct": 0.42},
    "Philadelphia": {"dvoa": 14.8, "def_rank": 3, "home_win_pct": 0.75},
    "Pittsburgh": {"dvoa": 2.8, "def_rank": 5, "home_win_pct": 0.65},
    "San Francisco": {"dvoa": 16.5, "def_rank": 1, "home_win_pct": 0.78},
    "Seattle": {"dvoa": 0.5, "def_rank": 27, "home_win_pct": 0.58},
    "Tampa Bay": {"dvoa": 4.2, "def_rank": 29, "home_win_pct": 0.55},
    "Tennessee": {"dvoa": -9.8, "def_rank": 31, "home_win_pct": 0.42},
    "Washington": {"dvoa": 9.5, "def_rank": 8, "home_win_pct": 0.62}
}

STAR_PLAYERS = {
    "Arizona": ["Kyler Murray", "Marvin Harrison Jr."],
    "Atlanta": ["Kirk Cousins", "Bijan Robinson"],
    "Baltimore": ["Lamar Jackson", "Derrick Henry"],
    "Buffalo": ["Josh Allen", "James Cook"],
    "Carolina": ["Bryce Young"],
    "Chicago": ["Caleb Williams", "D.J. Moore"],
    "Cincinnati": ["Joe Burrow", "Ja'Marr Chase"],
    "Cleveland": ["Deshaun Watson", "Nick Chubb"],
    "Dallas": ["Dak Prescott", "CeeDee Lamb"],
    "Denver": ["Bo Nix", "Pat Surtain II"],
    "Detroit": ["Jared Goff", "Amon-Ra St. Brown", "Aidan Hutchinson"],
    "Green Bay": ["Jordan Love", "Josh Jacobs"],
    "Houston": ["C.J. Stroud", "Nico Collins"],
    "Indianapolis": ["Anthony Richardson", "Jonathan Taylor"],
    "Jacksonville": ["Trevor Lawrence", "Travis Etienne"],
    "Kansas City": ["Patrick Mahomes", "Travis Kelce"],
    "Las Vegas": ["Gardner Minshew", "Brock Bowers"],
    "LA Chargers": ["Justin Herbert", "J.K. Dobbins"],
    "LA Rams": ["Matthew Stafford", "Puka Nacua"],
    "Miami": ["Tua Tagovailoa", "Tyreek Hill"],
    "Minnesota": ["Sam Darnold", "Justin Jefferson"],
    "New England": ["Drake Maye"],
    "New Orleans": ["Derek Carr", "Alvin Kamara"],
    "NY Giants": ["Daniel Jones", "Malik Nabers"],
    "NY Jets": ["Aaron Rodgers", "Garrett Wilson"],
    "Philadelphia": ["Jalen Hurts", "A.J. Brown", "Saquon Barkley"],
    "Pittsburgh": ["Russell Wilson", "T.J. Watt"],
    "San Francisco": ["Brock Purdy", "Christian McCaffrey", "Nick Bosa"],
    "Seattle": ["Geno Smith", "DK Metcalf"],
    "Tampa Bay": ["Baker Mayfield", "Mike Evans"],
    "Tennessee": ["Will Levis", "Tony Pollard"],
    "Washington": ["Jayden Daniels", "Terry McLaurin"]
}

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
            else:
                score += 0.5
    
    return score, out_players, qb_out

def calc_ml_score(home_team, away_team, injuries):
    home = TEAM_STATS.get(home_team, {})
    away = TEAM_STATS.get(away_team, {})
    
    score_home, score_away = 0, 0
    reasons_home, reasons_away = [], []
    
    # DVOA
    home_dvoa = home.get('dvoa', 0)
    away_dvoa = away.get('dvoa', 0)
    dvoa_diff = home_dvoa - away_dvoa
    if dvoa_diff > 8:
        score_home += 1.0
        reasons_home.append(f"📊 DVOA +{home_dvoa:.1f}")
    elif dvoa_diff < -8:
        score_away += 1.0
        reasons_away.append(f"📊 DVOA +{away_dvoa:.1f}")
    
    # Defense
    home_def = home.get('def_rank', 16)
    away_def = away.get('def_rank', 16)
    if home_def <= 5:
        score_home += 1.0
        reasons_home.append(f"🛡️ #{home_def} DEF")
    if away_def <= 5:
        score_away += 1.0
        reasons_away.append(f"🛡️ #{away_def} DEF")
    
    # Home field
    score_home += 1.0
    
    # Injuries
    home_inj, home_out, home_qb_out = get_injury_score(home_team, injuries)
    away_inj, away_out, away_qb_out = get_injury_score(away_team, injuries)
    
    if away_qb_out:
        score_home += 2.5
        reasons_home.append(f"🏥 QB Out")
    
    if home_qb_out:
        score_away += 2.5
        reasons_away.append(f"🏥 QB Out")
    
    # Home win %
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

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("⚡ LiveState")
    st.caption("Pre-resolution stress detection")
    st.markdown("""
| State | Leak | Action |
|-------|------|--------|
| 🔴 **MAX** | 3-7¢ | High Alert |
| 🟠 **ELEVATED** | 1-4¢ | Watch |
| 🟢 **NORMAL** | — | Hold |
""")
    st.caption("NOT predictions • NOT play-by-play")
    st.divider()
    
    st.header("🔢 TRIGGER FACTORS")
    st.markdown("""
| Trigger | Points |
|---------|--------|
| 4th Down | +2 |
| 3rd & 7+ | +1 |
| Conversion Zone | +2 |
| Red Zone + 2nd+ | +1 |
| 2-Min Zone | +1 |
| Sudden Change | +2 |
| Score Compress | +2 |
| Goal Line | +1 |
| Crunch Time | +2 |
""")
    st.divider()
    
    st.header("📖 ML LEGEND")
    st.markdown("🟢 **STRONG** → 8.0+\n\n🔵 **BUY** → 6.5-7.9\n\n🟡 **LEAN** → 5.5-6.4")
    st.divider()
    st.caption("v1.4 NFL EDGE + LiveState")

# ========== FETCH DATA ==========
games = fetch_espn_scores()
game_list = sorted(list(games.keys()))
injuries = fetch_espn_injuries()
now = datetime.now(eastern)

# ========== TITLE ==========
st.title("🏈 NFL EDGE FINDER")
st.caption("Pre-game picks + LiveState in-game stress detection")

# ========== LIVESTATE ==========
# LiveState: Pre-resolution stress detection
# NOT GameCast. NOT play-by-play. NOT predictions.
# Sole purpose: Surface moments where market prices soften BEFORE the snap.

live_games = {k: v for k, v in games.items() if v['status_type'] == "STATUS_IN_PROGRESS"}

if live_games:
    st.subheader("⚡ LiveState — Live Uncertainty Tracker")
    st.caption("Pre-resolution stress detection • Not predictions • Not play-by-play")
    
    hdr1, hdr2, hdr3 = st.columns([3, 1, 1])
    hdr1.caption(f"{auto_status} | {now.strftime('%I:%M:%S %p ET')} | v1.4")
    if hdr2.button("🔄 Auto" if not st.session_state.auto_refresh else "⏹️ Stop", use_container_width=True, key="auto_live"):
        st.session_state.auto_refresh = not st.session_state.auto_refresh
        st.rerun()
    if hdr3.button("🔄 Now", use_container_width=True, key="refresh_live"):
        st.query_params["r"] = str(int(time.time()))
        st.rerun()
    
    for game_key, g in live_games.items():
        event_id = g.get("event_id")
        if not event_id:
            continue
        
        # Fetch live situation from plays endpoint
        sit = fetch_live_situation(event_id)
        
        # Merge with game data for scores
        if sit and sit.get("down", 0) > 0:
            # Fill in scores from game data
            sit["home_team"] = g["home_team"]
            sit["away_team"] = g["away_team"]
            sit["home_score"] = g["home_score"]
            sit["away_score"] = g["away_score"]
            
            # Determine defense team and scores
            poss_team = sit["possession_team"]
            if poss_team == g["home_team"]:
                sit["defense_team"] = g["away_team"]
                sit["score_offense"] = g["home_score"]
                sit["score_defense"] = g["away_score"]
            else:
                sit["defense_team"] = g["home_team"]
                sit["score_offense"] = g["away_score"]
                sit["score_defense"] = g["home_score"]
            
            # Get previous state for score compression detection
            prev_state = st.session_state.livestate_prev.get(game_key, {})
            prev_score_pressure = prev_state.get("score_pressure")
            
            # Calculate uncertainty
            score_diff = sit["score_offense"] - sit["score_defense"]
            uncertainty_score, triggers = calculate_uncertainty(
                sit["down"], sit["yards_to_go"], sit["yardline_100"],
                sit["quarter"], sit["clock_seconds"], score_diff,
                sit.get("had_turnover", False), prev_score_pressure
            )
            
            state_label, state_color, expected_leak = get_uncertainty_state(uncertainty_score)
            field_band, field_color = get_field_position_band(sit["yardline_100"])
            score_pressure, _ = get_score_pressure(score_diff)
            clock_pressure, clock_color = get_clock_pressure(sit["quarter"], sit["clock_seconds"])
            
            # Store current state for next LiveState cycle
            st.session_state.livestate_prev[game_key] = {
                "score_pressure": score_pressure,
                "score_diff": score_diff
            }
            
            # Build display
            down_str = f"{sit['down']}" + ("st" if sit['down']==1 else "nd" if sit['down']==2 else "rd" if sit['down']==3 else "th")
            situation_line = f"Q{sit['quarter']} {sit['clock_display']} | {down_str} & {sit['yards_to_go']} | {sit['possession_team']} ball"
            
            # Determine CSS class
            if state_label == "MAX UNCERTAINTY":
                css_class = "uncertainty-max"
            elif state_label == "ELEVATED":
                css_class = "uncertainty-elevated"
            else:
                css_class = ""
            
            st.markdown(f"""
            <div class="{css_class}" style="background:linear-gradient(135deg,#1a1a2e,#0a0a1e);padding:18px;border-radius:12px;border:2px solid {state_color};margin-bottom:15px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                    <div>
                        <b style="color:#fff;font-size:1.3em">{g['away_team']} {g['away_score']} @ {g['home_team']} {g['home_score']}</b>
                    </div>
                    <div style="text-align:right">
                        <b style="color:{state_color};font-size:1.4em">{state_label}</b>
                        <div style="color:#888;font-size:0.9em">Leak: {expected_leak}</div>
                    </div>
                </div>
                <div style="background:#000;padding:12px;border-radius:8px;font-family:monospace;margin-bottom:12px">
                    <span style="color:#fff;font-size:1.1em">{situation_line}</span>
                </div>
                <div style="display:flex;gap:15px;flex-wrap:wrap">
                    <span style="color:{field_color}">📍 {field_band}</span>
                    <span style="color:{clock_color}">⏱️ Clock: {clock_pressure}</span>
                    <span style="color:#ffaa44">📊 {score_pressure}</span>
                    <span style="color:#88aaff">⏰ {sit['timeouts_offense']} TO</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Show triggers if elevated
            if triggers:
                trigger_html = " • ".join([f"<span style='color:#ffaa44'>{t}</span>" for t in triggers])
                st.markdown(f"<div style='padding:8px 12px;background:#1a1a1a;border-radius:6px;margin-bottom:10px'>🎯 <b>Triggers:</b> {trigger_html}</div>", unsafe_allow_html=True)
            
            # Show last play text if available
            if sit.get("play_text"):
                st.caption(f"📝 {sit['play_text'][:100]}...")
            
            # Kalshi link
            parts = game_key.split("@")
            kalshi_url = build_kalshi_ml_url(parts[0], parts[1], g.get('game_date'))
            st.link_button(f"🔗 Trade {game_key.replace('@', ' @ ')}", kalshi_url, use_container_width=True)
            
        else:
            # No situation data - show basic score + debug info
            st.markdown(f"""
            <div style="background:#1a1a2e;padding:15px;border-radius:10px;border:1px solid #333;margin-bottom:10px">
                <b style="color:#fff">{g['away_team']} {g['away_score']} @ {g['home_team']} {g['home_score']}</b>
                <span style="color:#888"> — Q{g['period']} {g['clock']}</span>
                <span style="color:#666;float:right">Awaiting play data...</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Debug: Show what ESPN is returning
            if st.checkbox(f"🔍 Debug {game_key}", key=f"debug_{game_key}"):
                try:
                    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={event_id}"
                    resp = requests.get(url, timeout=8)
                    data = resp.json()
                    
                    st.code(f"Event ID: {event_id}")
                    st.code(f"Has 'situation': {'situation' in data}")
                    
                    if "situation" in data:
                        st.json(data["situation"])
                    else:
                        st.write("Available keys:", list(data.keys()))
                        
                        # Check for drives/plays
                        if "drives" in data:
                            drives = data.get("drives", {})
                            current = drives.get("current", {})
                            st.write("Current drive:", current)
                            plays = current.get("plays", [])
                            if plays:
                                st.write("Last play:", plays[-1])
                except Exception as e:
                    st.error(f"Debug error: {e}")
    
    st.divider()

# ========== ACTIVE POSITIONS ==========
st.subheader("📈 ACTIVE POSITIONS")

if not live_games:
    hdr1, hdr2, hdr3 = st.columns([3, 1, 1])
    hdr1.caption(f"{auto_status} | {now.strftime('%I:%M:%S %p ET')} | v1.4")
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
            game_date = g.get('game_date')
            kalshi_url = build_kalshi_ml_url(parts[0], parts[1], game_date)
            btn1.link_button("🔗 Trade on Kalshi", kalshi_url, use_container_width=True)
            if btn2.button("✏️", key=f"edit_{idx}"):
                st.session_state.editing_position = idx if st.session_state.editing_position != idx else None
                st.rerun()
            if btn3.button("🗑️", key=f"del_{idx}"):
                st.session_state.positions.pop(idx)
                st.session_state.editing_position = None
                save_positions(st.session_state.positions)
                st.rerun()
            
            if st.session_state.editing_position == idx:
                with st.container():
                    st.markdown("##### ✏️ Edit Position")
                    e1, e2, e3 = st.columns(3)
                    new_price = e1.number_input("Entry ¢", min_value=1, max_value=99, value=pos.get('price', 50), key=f"price_{idx}")
                    new_contracts = e2.number_input("Contracts", min_value=1, value=pos.get('contracts', 1), key=f"contracts_{idx}")
                    
                    pick_options = [parts[1], parts[0]]
                    current_pick = pos.get('pick', parts[1])
                    pick_idx = pick_options.index(current_pick) if current_pick in pick_options else 0
                    new_pick = e3.radio("Pick", pick_options, index=pick_idx, horizontal=True, key=f"pick_{idx}")
                    
                    save_col, cancel_col = st.columns(2)
                    if save_col.button("💾 Save", key=f"save_{idx}", use_container_width=True, type="primary"):
                        st.session_state.positions[idx]['price'] = new_price
                        st.session_state.positions[idx]['contracts'] = new_contracts
                        st.session_state.positions[idx]['pick'] = new_pick
                        st.session_state.editing_position = None
                        save_positions(st.session_state.positions)
                        st.rerun()
                    if cancel_col.button("❌ Cancel", key=f"cancel_{idx}", use_container_width=True):
                        st.session_state.editing_position = None
                        st.rerun()
                    st.divider()
        else:
            st.markdown(f"<div style='background:#1a1a2e;padding:15px;border-radius:10px;border:1px solid #444;margin-bottom:10px;color:#888'>{game_key.replace('@', ' @ ')} — ⏳ Game not loaded</div>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"del_orphan_{idx}"):
                st.session_state.positions.pop(idx)
                save_positions(st.session_state.positions)
                st.rerun()
    
    if st.button("🗑️ Clear All", use_container_width=True):
        st.session_state.positions = []
        st.session_state.editing_position = None
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
        game_date = g.get('game_date')
        ml_results.append({
            "pick": pick, "score": score, "color": color, "reasons": reasons,
            "away": away, "home": home, "game_date": game_date, "game_key": game_key
        })
    except Exception as e:
        continue

ml_results.sort(key=lambda x: x["score"], reverse=True)

if ml_results:
    for r in ml_results:
        if r["score"] < 5.5:
            continue
        
        game_away = r["away"]
        game_home = r["home"]
        game_dt = r.get("game_date")
        pick_team = r["pick"]
        
        away_code = KALSHI_CODES.get(game_away, "XXX")
        home_code = KALSHI_CODES.get(game_home, "XXX")
        if game_dt:
            date_str = game_dt.strftime("%y%b%d").upper()
        else:
            date_str = datetime.now(eastern).strftime("%y%b%d").upper()
        ticker = f"KXNFLGAME-{date_str}{away_code}{home_code}"
        this_url = f"https://kalshi.com/markets/KXNFLGAME/{ticker}"
        
        reasons_str = " • ".join(r["reasons"])
        pick_code = KALSHI_CODES.get(pick_team, pick_team[:3].upper())
        opponent = game_away if pick_team == game_home else game_home
        
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
st.caption("⚠️ LiveState: Pre-resolution stress detection for educational analysis. Not financial advice. v1.4")
