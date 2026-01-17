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

# ========== DATE INVALIDATION ==========
if "snapshot_date" not in st.session_state or st.session_state["snapshot_date"] != today_str:
    st.session_state["snapshot_date"] = today_str

if st.session_state.auto_refresh:
    cache_buster = int(time.time()) + 30
    st.markdown(f'<meta http-equiv="refresh" content="30;url=?r={cache_buster}">', unsafe_allow_html=True)
    auto_status = "🔄 Auto-refresh ON (30s)"
else:
    auto_status = "⏸️ Auto-refresh OFF"

# ========== KALSHI TEAM CODES ==========
KALSHI_CODES = {
    "Arizona": "ARI", "Atlanta": "ATL", "Baltimore": "BAL", "Buffalo": "BUF",
    "Carolina": "CAR", "Chicago": "CHI", "Cincinnati": "CIN", "Cleveland": "CLE",
    "Dallas": "DAL", "Denver": "DEN", "Detroit": "DET", "Green Bay": "GB",
    "Houston": "HOU", "Indianapolis": "IND", "Jacksonville": "JAX", "Kansas City": "KC",
    "Las Vegas": "LV", "LA Chargers": "LAC", "LA Rams": "LAR", "Miami": "MIA",
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

TEAM_STATS = {
    "Arizona": {"dvoa": -8.5, "def_rank": 28, "home_win_pct": 0.45, "division": "NFC West", "timezone": "MST"},
    "Atlanta": {"dvoa": 2.5, "def_rank": 20, "home_win_pct": 0.55, "division": "NFC South", "timezone": "EST"},
    "Baltimore": {"dvoa": 12.5, "def_rank": 2, "home_win_pct": 0.72, "division": "AFC North", "timezone": "EST"},
    "Buffalo": {"dvoa": 15.8, "def_rank": 4, "home_win_pct": 0.78, "division": "AFC East", "timezone": "EST"},
    "Carolina": {"dvoa": -12.5, "def_rank": 26, "home_win_pct": 0.38, "division": "NFC South", "timezone": "EST"},
    "Chicago": {"dvoa": -5.2, "def_rank": 18, "home_win_pct": 0.48, "division": "NFC North", "timezone": "CST"},
    "Cincinnati": {"dvoa": 5.8, "def_rank": 12, "home_win_pct": 0.58, "division": "AFC North", "timezone": "EST"},
    "Cleveland": {"dvoa": -2.5, "def_rank": 15, "home_win_pct": 0.52, "division": "AFC North", "timezone": "EST"},
    "Dallas": {"dvoa": 3.2, "def_rank": 14, "home_win_pct": 0.62, "division": "NFC East", "timezone": "CST"},
    "Denver": {"dvoa": 4.5, "def_rank": 8, "home_win_pct": 0.68, "division": "AFC West", "timezone": "MST"},
    "Detroit": {"dvoa": 18.5, "def_rank": 6, "home_win_pct": 0.75, "division": "NFC North", "timezone": "EST"},
    "Green Bay": {"dvoa": 8.2, "def_rank": 10, "home_win_pct": 0.70, "division": "NFC North", "timezone": "CST"},
    "Houston": {"dvoa": 6.5, "def_rank": 16, "home_win_pct": 0.58, "division": "AFC South", "timezone": "CST"},
    "Indianapolis": {"dvoa": -6.8, "def_rank": 22, "home_win_pct": 0.48, "division": "AFC South", "timezone": "EST"},
    "Jacksonville": {"dvoa": -4.5, "def_rank": 19, "home_win_pct": 0.45, "division": "AFC South", "timezone": "EST"},
    "Kansas City": {"dvoa": 22.5, "def_rank": 7, "home_win_pct": 0.82, "division": "AFC West", "timezone": "CST"},
    "Las Vegas": {"dvoa": -8.2, "def_rank": 25, "home_win_pct": 0.45, "division": "AFC West", "timezone": "PST"},
    "LA Chargers": {"dvoa": 7.8, "def_rank": 9, "home_win_pct": 0.55, "division": "AFC West", "timezone": "PST"},
    "LA Rams": {"dvoa": 1.5, "def_rank": 17, "home_win_pct": 0.52, "division": "NFC West", "timezone": "PST"},
    "Miami": {"dvoa": 5.2, "def_rank": 13, "home_win_pct": 0.62, "division": "AFC East", "timezone": "EST"},
    "Minnesota": {"dvoa": 10.5, "def_rank": 11, "home_win_pct": 0.68, "division": "NFC North", "timezone": "CST"},
    "New England": {"dvoa": -10.5, "def_rank": 24, "home_win_pct": 0.42, "division": "AFC East", "timezone": "EST"},
    "New Orleans": {"dvoa": -3.8, "def_rank": 21, "home_win_pct": 0.55, "division": "NFC South", "timezone": "CST"},
    "NY Giants": {"dvoa": -15.5, "def_rank": 30, "home_win_pct": 0.35, "division": "NFC East", "timezone": "EST"},
    "NY Jets": {"dvoa": -7.5, "def_rank": 23, "home_win_pct": 0.42, "division": "AFC East", "timezone": "EST"},
    "Philadelphia": {"dvoa": 14.8, "def_rank": 3, "home_win_pct": 0.75, "division": "NFC East", "timezone": "EST"},
    "Pittsburgh": {"dvoa": 2.8, "def_rank": 5, "home_win_pct": 0.65, "division": "AFC North", "timezone": "EST"},
    "San Francisco": {"dvoa": 16.5, "def_rank": 1, "home_win_pct": 0.78, "division": "NFC West", "timezone": "PST"},
    "Seattle": {"dvoa": 0.5, "def_rank": 27, "home_win_pct": 0.58, "division": "NFC West", "timezone": "PST"},
    "Tampa Bay": {"dvoa": 4.2, "def_rank": 29, "home_win_pct": 0.55, "division": "NFC South", "timezone": "EST"},
    "Tennessee": {"dvoa": -9.8, "def_rank": 31, "home_win_pct": 0.42, "division": "AFC South", "timezone": "CST"},
    "Washington": {"dvoa": 9.5, "def_rank": 8, "home_win_pct": 0.62, "division": "NFC East", "timezone": "EST"}
}

STAR_PLAYERS = {
    "Arizona": ["Kyler Murray", "Marvin Harrison Jr."],
    "Atlanta": ["Kirk Cousins", "Bijan Robinson", "Drake London"],
    "Baltimore": ["Lamar Jackson", "Derrick Henry", "Mark Andrews"],
    "Buffalo": ["Josh Allen", "Stefon Diggs", "James Cook"],
    "Carolina": ["Bryce Young", "Diontae Johnson"],
    "Chicago": ["Caleb Williams", "D.J. Moore", "Keenan Allen"],
    "Cincinnati": ["Joe Burrow", "Ja'Marr Chase", "Tee Higgins"],
    "Cleveland": ["Deshaun Watson", "Nick Chubb", "Amari Cooper"],
    "Dallas": ["Dak Prescott", "CeeDee Lamb", "Micah Parsons"],
    "Denver": ["Bo Nix", "Courtland Sutton", "Pat Surtain II"],
    "Detroit": ["Jared Goff", "Amon-Ra St. Brown", "Jahmyr Gibbs", "Aidan Hutchinson"],
    "Green Bay": ["Jordan Love", "Jayden Reed", "Josh Jacobs"],
    "Houston": ["C.J. Stroud", "Nico Collins", "Stefon Diggs", "Will Anderson Jr."],
    "Indianapolis": ["Anthony Richardson", "Jonathan Taylor", "Michael Pittman Jr."],
    "Jacksonville": ["Trevor Lawrence", "Travis Etienne", "Brian Thomas Jr."],
    "Kansas City": ["Patrick Mahomes", "Travis Kelce", "Isiah Pacheco", "Chris Jones"],
    "Las Vegas": ["Gardner Minshew", "Davante Adams", "Brock Bowers"],
    "LA Chargers": ["Justin Herbert", "Ladd McConkey", "J.K. Dobbins"],
    "LA Rams": ["Matthew Stafford", "Puka Nacua", "Cooper Kupp", "Kyren Williams"],
    "Miami": ["Tua Tagovailoa", "Tyreek Hill", "Jaylen Waddle", "De'Von Achane"],
    "Minnesota": ["Sam Darnold", "Justin Jefferson", "Jordan Addison", "Aaron Jones"],
    "New England": ["Drake Maye", "Rhamondre Stevenson"],
    "New Orleans": ["Derek Carr", "Chris Olave", "Alvin Kamara"],
    "NY Giants": ["Daniel Jones", "Malik Nabers", "Devin Singletary"],
    "NY Jets": ["Aaron Rodgers", "Garrett Wilson", "Breece Hall"],
    "Philadelphia": ["Jalen Hurts", "A.J. Brown", "DeVonta Smith", "Saquon Barkley"],
    "Pittsburgh": ["Russell Wilson", "George Pickens", "Najee Harris", "T.J. Watt"],
    "San Francisco": ["Brock Purdy", "Deebo Samuel", "George Kittle", "Christian McCaffrey", "Nick Bosa"],
    "Seattle": ["Geno Smith", "DK Metcalf", "Jaxon Smith-Njigba", "Kenneth Walker III"],
    "Tampa Bay": ["Baker Mayfield", "Mike Evans", "Chris Godwin"],
    "Tennessee": ["Will Levis", "Tony Pollard", "DeAndre Hopkins"],
    "Washington": ["Jayden Daniels", "Terry McLaurin", "Brian Robinson Jr."]
}

QB_TIERS = {
    "Patrick Mahomes": 3, "Josh Allen": 3, "Lamar Jackson": 3, "Joe Burrow": 3,
    "Jalen Hurts": 3, "C.J. Stroud": 3, "Brock Purdy": 2, "Jayden Daniels": 2,
    "Jordan Love": 2, "Jared Goff": 2, "Justin Herbert": 2, "Dak Prescott": 2,
    "Tua Tagovailoa": 2, "Matthew Stafford": 2, "Kirk Cousins": 2, "Baker Mayfield": 2,
    "Sam Darnold": 2, "Trevor Lawrence": 2, "Aaron Rodgers": 2, "Russell Wilson": 2,
    "Geno Smith": 2, "Derek Carr": 2, "Kyler Murray": 2, "Anthony Richardson": 1,
    "Caleb Williams": 1, "Bo Nix": 1, "Drake Maye": 1, "Bryce Young": 1,
    "Deshaun Watson": 1, "Will Levis": 1, "Daniel Jones": 1, "Gardner Minshew": 1
}

TEAM_LOCATIONS = {
    "Arizona": (33.528, -112.263), "Atlanta": (33.755, -84.401), "Baltimore": (39.278, -76.623),
    "Buffalo": (42.774, -78.787), "Carolina": (35.226, -80.853), "Chicago": (41.862, -87.617),
    "Cincinnati": (39.095, -84.516), "Cleveland": (41.506, -81.700), "Dallas": (32.748, -97.093),
    "Denver": (39.744, -105.020), "Detroit": (42.340, -83.046), "Green Bay": (44.501, -88.062),
    "Houston": (29.685, -95.411), "Indianapolis": (39.760, -86.164), "Jacksonville": (30.324, -81.638),
    "Kansas City": (39.049, -94.484), "Las Vegas": (36.091, -115.184), "LA Chargers": (33.953, -118.339),
    "LA Rams": (33.953, -118.339), "Miami": (25.958, -80.239), "Minnesota": (44.974, -93.258),
    "New England": (42.091, -71.264), "New Orleans": (29.951, -90.081), "NY Giants": (40.813, -74.074),
    "NY Jets": (40.813, -74.074), "Philadelphia": (39.901, -75.168), "Pittsburgh": (40.447, -80.016),
    "San Francisco": (37.713, -122.387), "Seattle": (47.595, -122.332), "Tampa Bay": (27.976, -82.503),
    "Tennessee": (36.166, -86.771), "Washington": (38.908, -76.865)
}

DIVISIONS = {
    "AFC East": ["Buffalo", "Miami", "New England", "NY Jets"],
    "AFC North": ["Baltimore", "Cincinnati", "Cleveland", "Pittsburgh"],
    "AFC South": ["Houston", "Indianapolis", "Jacksonville", "Tennessee"],
    "AFC West": ["Denver", "Kansas City", "LA Chargers", "Las Vegas"],
    "NFC East": ["Dallas", "NY Giants", "Philadelphia", "Washington"],
    "NFC North": ["Chicago", "Detroit", "Green Bay", "Minnesota"],
    "NFC South": ["Atlanta", "Carolina", "New Orleans", "Tampa Bay"],
    "NFC West": ["Arizona", "LA Rams", "San Francisco", "Seattle"]
}

def calc_distance(loc1, loc2):
    from math import radians, sin, cos, sqrt, atan2
    lat1, lon1 = radians(loc1[0]), radians(loc1[1])
    lat2, lon2 = radians(loc2[0]), radians(loc2[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 3959 * 2 * atan2(sqrt(a), sqrt(1-a))

def get_timezone_diff(away_tz, home_tz):
    tz_map = {"EST": 0, "CST": -1, "MST": -2, "PST": -3}
    return abs(tz_map.get(away_tz, 0) - tz_map.get(home_tz, 0))

def fetch_espn_scores():
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        games = {}
        for event in data.get("events", []):
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

def fetch_team_record(team_name):
    team_ids = {
        "Arizona": "22", "Atlanta": "1", "Baltimore": "33", "Buffalo": "2",
        "Carolina": "29", "Chicago": "3", "Cincinnati": "4", "Cleveland": "5",
        "Dallas": "6", "Denver": "7", "Detroit": "8", "Green Bay": "9",
        "Houston": "34", "Indianapolis": "11", "Jacksonville": "30", "Kansas City": "12",
        "Las Vegas": "13", "LA Chargers": "24", "LA Rams": "14", "Miami": "15",
        "Minnesota": "16", "New England": "17", "New Orleans": "18", "NY Giants": "19",
        "NY Jets": "20", "Philadelphia": "21", "Pittsburgh": "23", "San Francisco": "25",
        "Seattle": "26", "Tampa Bay": "27", "Tennessee": "10", "Washington": "28"
    }
    try:
        team_id = team_ids.get(team_name, "1")
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        record = data.get("team", {}).get("record", {}).get("items", [{}])[0]
        stats = record.get("stats", [])
        streak_val = 0
        for stat in stats:
            if stat.get("name") == "streak":
                streak_str = stat.get("displayValue", "W0")
                if streak_str.startswith("W"):
                    streak_val = int(streak_str[1:]) if len(streak_str) > 1 else 0
                elif streak_str.startswith("L"):
                    streak_val = -int(streak_str[1:]) if len(streak_str) > 1 else 0
        return {"streak": streak_val}
    except:
        return {"streak": 0}

def is_division_rival(team1, team2):
    for div, teams in DIVISIONS.items():
        if team1 in teams and team2 in teams:
            return True
    return False

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
        elif "DOUBTFUL" in status:
            if is_qb:
                score += 3.0
            elif is_star:
                score += 1.5
        elif "QUESTIONABLE" in status:
            if is_qb:
                score += 1.5
            elif is_star:
                score += 0.5
    
    return score, out_players, qb_out

def calc_ml_score(home_team, away_team, injuries, short_rest_teams=None):
    if short_rest_teams is None:
        short_rest_teams = set()
    
    home = TEAM_STATS.get(home_team, {})
    away = TEAM_STATS.get(away_team, {})
    home_loc = TEAM_LOCATIONS.get(home_team, (0, 0))
    away_loc = TEAM_LOCATIONS.get(away_team, (0, 0))
    
    score_home, score_away = 0, 0
    reasons_home, reasons_away = [], []
    
    if away_team in short_rest_teams and home_team not in short_rest_teams:
        score_home += 1.5
        reasons_home.append("🛏️ Opp Short Rest")
    elif home_team in short_rest_teams and away_team not in short_rest_teams:
        score_away += 1.5
        reasons_away.append("🛏️ Opp Short Rest")
    
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
        reasons_home.append(f"🏥 {away_out[0][:12]}")
    elif away_inj - home_inj > 3:
        score_home += 1.5
        if away_out:
            reasons_home.append(f"🏥 {away_out[0][:12]}")
    
    if home_qb_out:
        score_away += 2.5
        reasons_away.append(f"🏥 {home_out[0][:12]}")
    elif home_inj - away_inj > 3:
        score_away += 1.5
        if home_out:
            reasons_away.append(f"🏥 {home_out[0][:12]}")
    
    travel_miles = calc_distance(away_loc, home_loc)
    away_tz = away.get('timezone', 'EST')
    home_tz = home.get('timezone', 'EST')
    tz_diff = get_timezone_diff(away_tz, home_tz)
    
    if travel_miles > 2000 or tz_diff >= 2:
        score_home += 1.0
        if tz_diff >= 2:
            reasons_home.append(f"✈️ {tz_diff}hr TZ")
        else:
            reasons_home.append(f"✈️ {int(travel_miles)}mi")
    
    home_hw = home.get('home_win_pct', 0.5)
    if home_hw > 0.65:
        score_home += 0.8
        reasons_home.append(f"🏠 {int(home_hw*100)}%")
    
    if home_team == "Denver":
        score_home += 1.0
        reasons_home.append("🏔️ Mile High")
    
    home_record = fetch_team_record(home_team)
    away_record = fetch_team_record(away_team)
    home_streak = home_record.get('streak', 0)
    away_streak = away_record.get('streak', 0)
    
    if home_streak >= 3 and away_streak <= -2:
        score_home += 1.0
        reasons_home.append(f"🔥 W{home_streak}")
    elif away_streak >= 3 and home_streak <= -2:
        score_away += 1.0
        reasons_away.append(f"🔥 W{away_streak}")
    elif home_streak >= 4:
        score_home += 0.5
        reasons_home.append(f"🔥 W{home_streak}")
    elif away_streak >= 4:
        score_away += 0.5
        reasons_away.append(f"🔥 W{away_streak}")
    
    if is_division_rival(home_team, away_team):
        score_home += 0.5
        reasons_home.append("🆚 Division")
    
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
    elif score >= 4.5:
        return "⚪ TOSS-UP", "#888888"
    else:
        return "🔴 SKIP", "#ff0000"

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("🔗 KALSHI")
    st.caption("Track here → Execute on web")
    st.divider()
    
    st.header("📖 ML LEGEND")
    st.markdown("🟢 **STRONG BUY** → 8.0+\n\n🔵 **BUY** → 6.5-7.9\n\n🟡 **LEAN** → 5.5-6.4\n\n⚪ **TOSS-UP** → 4.5-5.4")
    st.divider()
    
    st.header("🎯 10 NFL FACTORS")
    st.markdown("""
| # | Factor | Max Pts |
|---|--------|---------|
| 1 | 🛏️ **Short Rest** | +1.5 |
| 2 | 📊 **DVOA Rating** | +1.0 |
| 3 | 🛡️ **Top 5 DEF** | +1.0 |
| 4 | 🏠 **Home Field** | +1.0 |
| 5 | 🏥 **QB OUT** | +2.5 |
| 6 | ✈️ **Travel/TZ** | +1.0 |
| 7 | 📈 **Home Win %** | +0.8 |
| 8 | 🏔️ **Mile High** | +1.0 |
| 9 | 🔥 **Win Streak** | +1.0 |
| 10 | 🆚 **Division** | +0.5 |
""")
    st.divider()
    
    st.header("⏰ TIMING EDGE")
    st.markdown("""
| Day | Action |
|-----|--------|
| **Fri 1 AM** | Lines posted, stale |
| **Sat** | Injury news |
| **Sun 9 AM** | Volume, prices move |
| **Sun 1 PM** | Kickoff |
""")
    st.divider()
    st.caption("v1.2 NFL EDGE")

# ========== FETCH DATA ==========
games = fetch_espn_scores()
game_list = sorted(list(games.keys()))
injuries = fetch_espn_injuries()
now = datetime.now(eastern)

# ========== TITLE ==========
st.title("🏈 NFL EDGE FINDER")

# ========== ACTIVE POSITIONS ==========
st.subheader("📈 ACTIVE POSITIONS")

hdr1, hdr2, hdr3 = st.columns([3, 1, 1])
hdr1.caption(f"{auto_status} | {now.strftime('%I:%M:%S %p ET')} | v1.2 NFL")
if hdr2.button("🔄 Auto" if not st.session_state.auto_refresh else "⏹️ Stop", use_container_width=True):
    st.session_state.auto_refresh = not st.session_state.auto_refresh
    st.rerun()
if hdr3.button("🔄 Refresh", use_container_width=True):
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
            
            tracking_line = ""
            if pos.get('added_at'):
                tracking_line = f"<div style='margin-top:5px;color:#666;font-size:0.85em'>⏰ Added: {pos.get('added_at')} | Score: {pos.get('score', 'N/A')}/10"
                if pos.get('morning_price'):
                    move = pos['morning_price'] - price
                    move_color = "#00ff00" if move > 0 else "#ff0000"
                    tracking_line += f" | 🌅 AM: <span style='color:{move_color}'>{pos['morning_price']}¢ ({'+' if move > 0 else ''}{move}¢)</span>"
                tracking_line += "</div>"
            
            st.markdown(f"""<div style='background:linear-gradient(135deg,#1a1a2e,#16213e);padding:15px;border-radius:10px;border:2px solid {status_color};margin-bottom:10px'>
            <div style='display:flex;justify-content:space-between'>
            <div><b style='color:#fff;font-size:1.2em'>{game_key.replace('@', ' @ ')}</b> <span style='color:#888'>{game_status}</span></div>
            <b style='color:{status_color};font-size:1.3em'>{status_label}</b>
            </div>
            <div style='margin-top:10px;color:#aaa'>🎯 Pick: <b style='color:#fff'>{pick}</b> | 💵 {contracts}x @ {price}¢ (${cost:.2f}) | 📊 {pick_score}-{opp_score} | Lead: <b style='color:{status_color}'>{lead:+d}</b> | <span style='color:{pnl_color}'>{pnl}</span></div>
            {tracking_line}</div>""", unsafe_allow_html=True)
            
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
                    e1, e2, e3, e4 = st.columns(4)
                    new_price = e1.number_input("Entry ¢", min_value=1, max_value=99, value=pos.get('price', 50), key=f"price_{idx}")
                    new_contracts = e2.number_input("Contracts", min_value=1, value=pos.get('contracts', 1), key=f"contracts_{idx}")
                    new_morning = e3.number_input("🌅 Sun AM ¢", min_value=0, max_value=99, value=pos.get('morning_price') or 0, key=f"morning_{idx}", help="Enter Sunday morning price to track move")
                    
                    pick_options = [parts[1], parts[0]]
                    current_pick = pos.get('pick', parts[1])
                    pick_idx = pick_options.index(current_pick) if current_pick in pick_options else 0
                    new_pick = e4.radio("Pick", pick_options, index=pick_idx, horizontal=True, key=f"pick_{idx}")
                    
                    save_col, cancel_col = st.columns(2)
                    if save_col.button("💾 Save", key=f"save_{idx}", use_container_width=True, type="primary"):
                        st.session_state.positions[idx]['price'] = new_price
                        st.session_state.positions[idx]['contracts'] = new_contracts
                        st.session_state.positions[idx]['morning_price'] = new_morning if new_morning > 0 else None
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
            btn1, btn2 = st.columns([4, 1])
            if btn2.button("🗑️", key=f"del_{idx}"):
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

# ========== INJURY REPORT ==========
st.subheader("🏥 INJURY REPORT")

with st.sidebar:
    total_injuries = sum(len(v) for v in injuries.values())
    st.caption(f"📊 {total_injuries} injuries loaded")

if game_list:
    teams_playing = set()
    for game_key in game_list:
        parts = game_key.split("@")
        teams_playing.add(parts[0])
        teams_playing.add(parts[1])
    
    key_injuries = []
    for team in sorted(teams_playing):
        team_injuries = injuries.get(team, [])
        stars = STAR_PLAYERS.get(team, [])
        for inj in team_injuries:
            name = inj.get("name", "")
            status = inj.get("status", "").upper()
            position = inj.get("position", "")
            is_star = any(star.lower() in name.lower() for star in stars)
            is_qb = position.upper() == "QB"
            
            if (is_qb or is_star) and ("OUT" in status or "DOUBTFUL" in status or "QUESTIONABLE" in status):
                key_injuries.append((team, name, position, status, is_qb))
    
    if key_injuries:
        cols = st.columns(3)
        for idx, (team, name, position, status, is_qb) in enumerate(key_injuries):
            with cols[idx % 3]:
                if "OUT" in status:
                    status_color = "#ff0000"
                    simple_status = "OUT"
                elif "DOUBTFUL" in status:
                    status_color = "#ff4400"
                    simple_status = "DOUBTFUL"
                else:
                    status_color = "#ffaa00"
                    simple_status = "Q"
                
                icon = "🚨" if is_qb else "⚠️"
                st.markdown(f"""<div style='background:linear-gradient(135deg,#2a1a1a,#1a1a2e);padding:10px;border-radius:8px;border-left:4px solid {status_color};margin-bottom:8px'>
                <b style='color:#fff'>{icon} {name}</b> ({position})<br>
                <span style='color:{status_color}'>{simple_status}</span> • {team}</div>""", unsafe_allow_html=True)
    else:
        st.info("✅ No key injuries for this week's games")
else:
    st.info("No games scheduled")

st.divider()

# ========== ML PICKS ==========
st.subheader("🎯 ML PICKS")

ml_results = []
for game_key, g in games.items():
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

for idx, r in enumerate(ml_results):
    if r["score"] < 5.5:
        continue
    
    # Build URL completely fresh for THIS game
    game_away = r["away"]
    game_home = r["home"]
    game_dt = r.get("game_date")
    pick_team = r["pick"]
    
    # Build Kalshi URL inline
    away_code = KALSHI_CODES.get(game_away, "XXX")
    home_code = KALSHI_CODES.get(game_home, "XXX")
    if game_dt:
        date_str = game_dt.strftime("%y%b%d").upper()
    else:
        date_str = datetime.now(eastern).strftime("%y%b%d").upper()
    ticker = f"KXNFLGAME-{date_str}{away_code}{home_code}"
    kalshi_url = f"https://kalshi.com/markets/KXNFLGAME/{ticker}"
    
    reasons_str = " • ".join(r["reasons"])
    pick_code = KALSHI_CODES.get(pick_team, pick_team[:3].upper())
    opponent = game_away if pick_team == game_home else game_home
    
    # Use columns with Streamlit's native link_button
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(f"""<div style="background:linear-gradient(135deg,#0f172a,#020617);padding:8px 12px;border-radius:6px;border-left:3px solid {r['color']}">
        <b style="color:#fff">{pick_team}</b> <span style="color:#666">vs {opponent}</span> <span style="color:#38bdf8">{r['score']}/10</span> <span style="color:#777;font-size:0.8em">{reasons_str}</span></div>""", unsafe_allow_html=True)
    with col2:
        st.link_button(f"BUY {pick_code}", kalshi_url, use_container_width=True)

strong_picks = [r for r in ml_results if r["score"] >= 6.5]
if strong_picks:
    if st.button(f"➕ Add {len(strong_picks)} Picks", use_container_width=True):
        added = 0
        for r in strong_picks:
            game_key = f"{r['away']}@{r['home']}"
            if not any(p.get('game') == game_key and p.get('pick') == r['pick'] for p in st.session_state.positions):
                st.session_state.positions.append({
                    "game": game_key,
                    "type": "ml",
                    "pick": r['pick'],
                    "price": 50,
                    "contracts": 1,
                    "cost": 0.50,
                    "score": r['score'],
                    "added_at": now.strftime("%a %I:%M %p")
                })
                added += 1
        if added:
            save_positions(st.session_state.positions)
            st.rerun()

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
if st.button("Show details"):
    log_diagnostic("show_details")
    st.caption(f"Session: {st.session_state['sid'][:8]}...")
st.caption("⚠️ Entertainment only. Not financial advice. v1.2 NFL EDGE")
