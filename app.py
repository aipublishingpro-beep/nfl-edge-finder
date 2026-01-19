import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz
import json
import os
import time
import uuid

# Use streamlit-autorefresh for smoother updates (replaces meta refresh)
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

st.set_page_config(page_title="NFL Edge Finder", page_icon="🏈", layout="wide")

if "sid" not in st.session_state:
    st.session_state["sid"] = str(uuid.uuid4())

# Session state for ball position tracking
if "last_ball_positions" not in st.session_state:
    st.session_state.last_ball_positions = {}  # {game_key: {"ball_yard": 50, "poss_team": "...", "poss_text": "..."}}

eastern = pytz.timezone("US/Eastern")
today_str = datetime.now(eastern).strftime("%Y-%m-%d")

st.markdown("""
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-NQKY5VQ376"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-NQKY5VQ376');
</script>
<style>
.stLinkButton > a {background-color: #00aa00 !important;border-color: #00aa00 !important;color: white !important;}
.stLinkButton > a:hover {background-color: #00cc00 !important;border-color: #00cc00 !important;}
</style>
""", unsafe_allow_html=True)

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

if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False
if "positions" not in st.session_state:
    st.session_state.positions = load_positions()
if "selected_ml_pick" not in st.session_state:
    st.session_state.selected_ml_pick = None
if "editing_position" not in st.session_state:
    st.session_state.editing_position = None

# Auto-refresh using streamlit-autorefresh (smoother than meta refresh)
if st.session_state.auto_refresh and HAS_AUTOREFRESH:
    st_autorefresh(interval=5000, limit=None, key="nfl_autorefresh")  # 5 second refresh
    auto_status = "🔄 Auto-refresh ON (5s)"
elif st.session_state.auto_refresh and not HAS_AUTOREFRESH:
    # Fallback to meta refresh if component not installed
    st.markdown(f'<meta http-equiv="refresh" content="5;url=?r={int(time.time()) + 5}">', unsafe_allow_html=True)
    auto_status = "🔄 Auto-refresh ON (5s)"
else:
    auto_status = "⏸️ Auto-refresh OFF"

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

# Stadium locations for weather
STADIUM_COORDS = {
    "Arizona": (33.5277, -112.2626), "Atlanta": (33.7553, -84.4006), "Baltimore": (39.2780, -76.6227),
    "Buffalo": (42.7738, -78.7870), "Carolina": (35.2258, -80.8528), "Chicago": (41.8623, -87.6167),
    "Cincinnati": (39.0955, -84.5161), "Cleveland": (41.5061, -81.6995), "Dallas": (32.7473, -97.0945),
    "Denver": (39.7439, -105.0201), "Detroit": (42.3400, -83.0456), "Green Bay": (44.5013, -88.0622),
    "Houston": (29.6847, -95.4107), "Indianapolis": (39.7601, -86.1639), "Jacksonville": (30.3239, -81.6373),
    "Kansas City": (39.0489, -94.4839), "Las Vegas": (36.0909, -115.1833), "LA Chargers": (33.9535, -118.3392),
    "LA Rams": (33.9535, -118.3392), "Miami": (25.9580, -80.2389), "Minnesota": (44.9737, -93.2577),
    "New England": (42.0909, -71.2643), "New Orleans": (29.9511, -90.0812), "NY Giants": (40.8128, -74.0742),
    "NY Jets": (40.8128, -74.0742), "Philadelphia": (39.9008, -75.1675), "Pittsburgh": (40.4468, -80.0158),
    "San Francisco": (37.4032, -121.9698), "Seattle": (47.5952, -122.3316), "Tampa Bay": (27.9759, -82.5033),
    "Tennessee": (36.1665, -86.7713), "Washington": (38.9076, -76.8645)
}

# Dome stadiums (no weather impact)
DOME_STADIUMS = ["Arizona", "Atlanta", "Dallas", "Detroit", "Houston", "Indianapolis", 
                  "Las Vegas", "LA Chargers", "LA Rams", "Minnesota", "New Orleans"]

# Pass-heavy vs run-heavy teams (for weather impact)
PASS_HEAVY_TEAMS = ["Buffalo", "Cincinnati", "Miami", "Tampa Bay", "LA Chargers", "Detroit", "Philadelphia"]
RUN_HEAVY_TEAMS = ["Baltimore", "San Francisco", "Cleveland", "Tennessee", "Denver"]

TEAM_STATS = {
    "Arizona": {"dvoa": -12.5, "def_rank": 27, "home_win_pct": 0.42, "away_win_pct": 0.30},
    "Atlanta": {"dvoa": 2.5, "def_rank": 18, "home_win_pct": 0.55, "away_win_pct": 0.42},
    "Baltimore": {"dvoa": 15.5, "def_rank": 6, "home_win_pct": 0.72, "away_win_pct": 0.62},
    "Buffalo": {"dvoa": 18.2, "def_rank": 5, "home_win_pct": 0.78, "away_win_pct": 0.68},
    "Carolina": {"dvoa": -18.5, "def_rank": 30, "home_win_pct": 0.35, "away_win_pct": 0.22},
    "Chicago": {"dvoa": -8.5, "def_rank": 22, "home_win_pct": 0.45, "away_win_pct": 0.35},
    "Cincinnati": {"dvoa": 5.8, "def_rank": 14, "home_win_pct": 0.58, "away_win_pct": 0.48},
    "Cleveland": {"dvoa": -25.0, "def_rank": 32, "home_win_pct": 0.38, "away_win_pct": 0.25},
    "Dallas": {"dvoa": -5.2, "def_rank": 20, "home_win_pct": 0.52, "away_win_pct": 0.38},
    "Denver": {"dvoa": 8.5, "def_rank": 8, "home_win_pct": 0.65, "away_win_pct": 0.50},
    "Detroit": {"dvoa": 22.5, "def_rank": 4, "home_win_pct": 0.78, "away_win_pct": 0.68},
    "Green Bay": {"dvoa": 12.2, "def_rank": 10, "home_win_pct": 0.70, "away_win_pct": 0.55},
    "Houston": {"dvoa": 16.5, "def_rank": 7, "home_win_pct": 0.68, "away_win_pct": 0.58},
    "Indianapolis": {"dvoa": 14.5, "def_rank": 12, "home_win_pct": 0.55, "away_win_pct": 0.48},
    "Jacksonville": {"dvoa": 10.5, "def_rank": 11, "home_win_pct": 0.55, "away_win_pct": 0.48},
    "Kansas City": {"dvoa": 18.5, "def_rank": 9, "home_win_pct": 0.82, "away_win_pct": 0.72},
    "Las Vegas": {"dvoa": -10.2, "def_rank": 25, "home_win_pct": 0.42, "away_win_pct": 0.28},
    "LA Chargers": {"dvoa": 11.8, "def_rank": 3, "home_win_pct": 0.62, "away_win_pct": 0.52},
    "LA Rams": {"dvoa": 24.5, "def_rank": 5, "home_win_pct": 0.72, "away_win_pct": 0.62},
    "Miami": {"dvoa": -2.5, "def_rank": 16, "home_win_pct": 0.55, "away_win_pct": 0.38},
    "Minnesota": {"dvoa": 8.5, "def_rank": 13, "home_win_pct": 0.68, "away_win_pct": 0.52},
    "New England": {"dvoa": 12.5, "def_rank": 8, "home_win_pct": 0.62, "away_win_pct": 0.50},
    "New Orleans": {"dvoa": -8.8, "def_rank": 23, "home_win_pct": 0.48, "away_win_pct": 0.35},
    "NY Giants": {"dvoa": -15.5, "def_rank": 29, "home_win_pct": 0.35, "away_win_pct": 0.22},
    "NY Jets": {"dvoa": -12.5, "def_rank": 26, "home_win_pct": 0.42, "away_win_pct": 0.28},
    "Philadelphia": {"dvoa": 14.8, "def_rank": 6, "home_win_pct": 0.75, "away_win_pct": 0.60},
    "Pittsburgh": {"dvoa": 4.8, "def_rank": 10, "home_win_pct": 0.62, "away_win_pct": 0.45},
    "San Francisco": {"dvoa": 6.5, "def_rank": 15, "home_win_pct": 0.58, "away_win_pct": 0.48},
    "Seattle": {"dvoa": 28.5, "def_rank": 2, "home_win_pct": 0.78, "away_win_pct": 0.68},
    "Tampa Bay": {"dvoa": -3.2, "def_rank": 19, "home_win_pct": 0.52, "away_win_pct": 0.40},
    "Tennessee": {"dvoa": -14.8, "def_rank": 28, "home_win_pct": 0.40, "away_win_pct": 0.25},
    "Washington": {"dvoa": -4.5, "def_rank": 21, "home_win_pct": 0.52, "away_win_pct": 0.42}
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

# ========== WEATHER API ==========
@st.cache_data(ttl=1800)
def fetch_weather(lat, lon):
    """Fetch weather from Open-Meteo (free, no API key)"""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m,precipitation,weather_code&wind_speed_unit=mph&temperature_unit=fahrenheit"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        current = data.get("current", {})
        return {
            "temp": current.get("temperature_2m", 70),
            "wind": current.get("wind_speed_10m", 0),
            "precip": current.get("precipitation", 0),
            "code": current.get("weather_code", 0)
        }
    except:
        return {"temp": 70, "wind": 0, "precip": 0, "code": 0}

def get_weather_for_game(home_team):
    """Get weather impact for a game"""
    if home_team in DOME_STADIUMS:
        return {"wind": 0, "precip": 0, "temp": 72, "dome": True, "impact": "none"}
    
    coords = STADIUM_COORDS.get(home_team)
    if not coords:
        return {"wind": 0, "precip": 0, "temp": 70, "dome": False, "impact": "none"}
    
    weather = fetch_weather(coords[0], coords[1])
    wind = weather.get("wind", 0)
    precip = weather.get("precip", 0)
    temp = weather.get("temp", 70)
    
    # Determine impact level
    if wind >= 20 or precip > 0.5:
        impact = "severe"
    elif wind >= 15 or precip > 0.1:
        impact = "moderate"
    elif wind >= 10:
        impact = "light"
    else:
        impact = "none"
    
    return {"wind": wind, "precip": precip, "temp": temp, "dome": False, "impact": impact}

# ========== RECENT FORM (Last 5 Games) ==========
@st.cache_data(ttl=3600)
def fetch_team_records():
    """Fetch current season records from ESPN"""
    records = {}
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/standings"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        for group in data.get("children", []):
            for team_standing in group.get("standings", {}).get("entries", []):
                team_info = team_standing.get("team", {})
                team_name = team_info.get("displayName", "")
                team_key = TEAM_ABBREVS.get(team_name, team_name)
                
                stats = team_standing.get("stats", [])
                wins, losses, streak = 0, 0, "—"
                
                for stat in stats:
                    if stat.get("name") == "wins":
                        wins = int(stat.get("value", 0))
                    elif stat.get("name") == "losses":
                        losses = int(stat.get("value", 0))
                    elif stat.get("name") == "streak":
                        streak = stat.get("displayValue", "—")
                
                records[team_key] = {
                    "wins": wins,
                    "losses": losses,
                    "streak": streak,
                    "win_pct": wins / (wins + losses) if (wins + losses) > 0 else 0.5
                }
    except:
        pass
    return records

@st.cache_data(ttl=3600)
def fetch_last_5_records():
    """Fetch last 5 game results for each team"""
    last_5 = {}
    try:
        # Get completed games from scoreboard
        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=2024&limit=300"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        team_games = {team: [] for team in KALSHI_CODES.keys()}
        
        for event in data.get("events", []):
            status = event.get("status", {}).get("type", {}).get("name", "")
            if status != "STATUS_FINAL":
                continue
            
            comp = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            
            game_date = event.get("date", "")
            
            for c in competitors:
                team_name = c.get("team", {}).get("displayName", "")
                team_key = TEAM_ABBREVS.get(team_name, team_name)
                winner = c.get("winner", False)
                
                if team_key in team_games:
                    team_games[team_key].append({
                        "date": game_date,
                        "win": winner
                    })
        
        # Get last 5 for each team
        for team, games in team_games.items():
            games.sort(key=lambda x: x['date'], reverse=True)
            recent = games[:5]
            wins = sum(1 for g in recent if g['win'])
            losses = len(recent) - wins
            
            # Create form string (W/L pattern)
            form = "".join(["W" if g['win'] else "L" for g in recent])
            
            last_5[team] = {
                "wins": wins,
                "losses": losses,
                "form": form,
                "hot": wins >= 4,
                "cold": losses >= 4
            }
    except:
        pass
    return last_5

# ========== REST DAYS CALCULATION ==========
@st.cache_data(ttl=3600)
def fetch_team_schedules():
    """Get last game date for each team to calculate rest"""
    last_games = {}
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=2024&limit=100"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        for event in data.get("events", []):
            status = event.get("status", {}).get("type", {}).get("name", "")
            if status != "STATUS_FINAL":
                continue
            
            game_date_str = event.get("date", "")
            try:
                game_date = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
            except:
                continue
            
            comp = event.get("competitions", [{}])[0]
            for c in comp.get("competitors", []):
                team_name = c.get("team", {}).get("displayName", "")
                team_key = TEAM_ABBREVS.get(team_name, team_name)
                
                if team_key not in last_games or game_date > last_games[team_key]:
                    last_games[team_key] = game_date
    except:
        pass
    return last_games

def get_rest_days(team, game_date, last_games):
    """Calculate days since last game"""
    if team not in last_games:
        return 7  # Default to normal rest
    
    last_game = last_games[team]
    if game_date.tzinfo is None:
        game_date = eastern.localize(game_date)
    if last_game.tzinfo is None:
        last_game = eastern.localize(last_game)
    
    delta = (game_date - last_game).days
    return max(0, delta)


def detect_scoring_play(last_play):
    """
    Detect if the last play was a scoring play.
    Returns: (is_scoring, play_type, scoring_team_code)
    """
    if not last_play:
        return False, None, None
    
    play_text = last_play.get("text", "") or last_play.get("description", "") or ""
    is_scoring = last_play.get("scoringPlay", False)
    play_type_info = last_play.get("type", {})
    play_type_text = play_type_info.get("text", "") if isinstance(play_type_info, dict) else ""
    
    text_lower = play_text.lower()
    
    # Detect scoring types
    if is_scoring or "touchdown" in text_lower or play_type_text == "Touchdown":
        return True, "touchdown", None
    elif "field goal" in text_lower and ("good" in text_lower or "made" in text_lower):
        return True, "field_goal", None
    elif "extra point" in text_lower and "good" in text_lower:
        return True, "extra_point", None
    elif "safety" in text_lower:
        return True, "safety", None
    elif "two-point" in text_lower and ("good" in text_lower or "success" in text_lower):
        return True, "two_point", None
    
    return False, None, None


def get_ball_position_with_fallback(game_key, g, away_team, home_team):
    """
    Calculate ball position with smart fallbacks for empty poss_text situations.
    
    FIX FROM EARLIER TODAY: Use ESPN's actual abbreviations (away_abbrev, home_abbrev)
    instead of KALSHI_CODES for matching poss_text team codes.
    
    Returns: (ball_yard, display_mode, poss_team, poss_text)
    display_mode: "normal", "scoring", "between_plays", "kickoff"
    """
    poss_text = g.get('poss_text', '')
    yards_to_endzone = g.get('yards_to_endzone', 50)
    possession_team = g.get('possession_team')
    is_home_possession = g.get('is_home_possession')
    last_play = g.get('last_play', {})
    period = g.get('period', 0)
    clock = g.get('clock', '')
    
    # KEY FIX: Use ESPN's actual abbreviations for comparison
    home_abbrev = g.get('home_abbrev', KALSHI_CODES.get(home_team, home_team[:3].upper()))
    away_abbrev = g.get('away_abbrev', KALSHI_CODES.get(away_team, away_team[:3].upper()))
    
    # Get last known position from session state
    last_known = st.session_state.last_ball_positions.get(game_key, {})
    
    # CASE 1: We have valid poss_text - parse it directly
    if poss_text and poss_text.strip():
        parts_poss = poss_text.strip().split()
        if len(parts_poss) >= 2:
            try:
                side_team = parts_poss[0].upper()
                yard_line = int(parts_poss[-1])
                
                # FIX: Compare against ESPN abbreviations, not KALSHI_CODES
                # Field layout: LEFT (0) = Away endzone, RIGHT (100) = Home endzone
                if side_team == away_abbrev.upper():
                    # Ball is on away team's side of field (e.g., "BUF 25" = 25 yards from away endzone)
                    ball_yard = yard_line
                elif side_team == home_abbrev.upper():
                    # Ball is on home team's side of field (e.g., "KC 25" = 25 yards from home endzone = 75 from left)
                    ball_yard = 100 - yard_line
                else:
                    # Unknown team code, use yards_to_endzone fallback
                    if is_home_possession is not None and yards_to_endzone is not None:
                        ball_yard = yards_to_endzone if is_home_possession else 100 - yards_to_endzone
                    else:
                        ball_yard = last_known.get('ball_yard', 50)
                
                # Update session state with valid position
                st.session_state.last_ball_positions[game_key] = {
                    'ball_yard': ball_yard,
                    'poss_team': possession_team,
                    'poss_text': poss_text
                }
                
                return ball_yard, "normal", possession_team, poss_text
                
            except (ValueError, IndexError):
                pass
    
    # CASE 2: Empty poss_text - check if scoring play just happened
    is_scoring, score_type, _ = detect_scoring_play(last_play)
    
    if is_scoring:
        # Determine which endzone to show ball at
        # If we know who scored, show at their target endzone
        if last_known.get('poss_team'):
            scoring_team = last_known.get('poss_team')
            if scoring_team == home_team:
                ball_yard = 0  # Home scored - ball at away's endzone (left)
            else:
                ball_yard = 100  # Away scored - ball at home's endzone (right)
        else:
            # Use last known ball position direction
            last_yard = last_known.get('ball_yard', 50)
            ball_yard = 0 if last_yard < 50 else 100
        
        score_emoji = "🏈" if score_type == "touchdown" else "🥅" if score_type == "field_goal" else "⚡"
        return ball_yard, "scoring", None, f"{score_emoji} {score_type.upper().replace('_', ' ')}"
    
    # CASE 3: Check for kickoff/punt (ball in transition)
    if last_play:
        play_text = (last_play.get("text", "") or "").lower()
        if "kickoff" in play_text or "kicks off" in play_text:
            return 65, "kickoff", None, "⚡ KICKOFF"
        elif "punts" in play_text:
            return 50, "between_plays", None, "📤 PUNT"
    
    # CASE 4: Game in progress but no possession data - use last known or hide
    if period > 0:
        # Check if it's end of quarter
        if clock == "0:00":
            return last_known.get('ball_yard', 50), "between_plays", None, "⏱️ End of Quarter"
        
        # Use last known position as fallback
        if last_known.get('ball_yard') is not None:
            return last_known.get('ball_yard'), "between_plays", last_known.get('poss_team'), "Between Plays"
    
    # CASE 5: Game not started or no data - show at 50
    return 50, "between_plays", None, ""


def render_football_field(ball_yard, down, distance, possession_team, away_team, home_team, 
                          yards_to_endzone=None, poss_text=None, display_mode="normal"):
    """
    Render football field with ball position.
    
    Field layout:
    - Left (0-10%): Away team's END ZONE (where HOME attacks)
    - Right (90-100%): Home team's END ZONE (where AWAY attacks)
    
    display_mode: "normal", "scoring", "between_plays", "kickoff"
    """
    away_code = KALSHI_CODES.get(away_team, away_team[:3].upper())
    home_code = KALSHI_CODES.get(home_team, home_team[:3].upper())
    
    # Build situation text based on display mode
    if display_mode == "scoring":
        situation = poss_text or "🏈 SCORE!"
        poss_code = "—"
        ball_loc = ""
        direction = ""
        ball_style = "font-size:28px;text-shadow:0 0 20px #ffff00"
    elif display_mode == "kickoff":
        situation = poss_text or "⚡ KICKOFF"
        poss_code = "—"
        ball_loc = ""
        direction = ""
        ball_style = "font-size:24px;text-shadow:0 0 10px #fff"
    elif display_mode == "between_plays" or not possession_team:
        situation = poss_text if poss_text else "Between Plays"
        poss_code = "—"
        ball_loc = ""
        direction = ""
        ball_style = "font-size:24px;opacity:0.6;text-shadow:0 0 10px #fff"
    else:
        situation = f"{down} & {distance}" if down and distance else "—"
        poss_code = KALSHI_CODES.get(possession_team, possession_team[:3].upper() if possession_team else "???")
        ball_loc = poss_text if poss_text else ""
        is_home_poss = possession_team == home_team
        direction = "◀" if is_home_poss else "▶"
        ball_style = "font-size:24px;text-shadow:0 0 10px #fff"
    
    ball_yard = max(0, min(100, ball_yard))
    # Scale ball_yard (0-100) to visual field (10%-90%) since endzones are 0-10% and 90-100%
    ball_pct = 10 + (ball_yard / 100) * 80
    
    return f"""<div style="background:#1a1a1a;padding:15px;border-radius:10px;margin:10px 0">
<div style="display:flex;justify-content:space-between;margin-bottom:8px">
<span style="color:#ffaa00;font-weight:bold">🏈 {poss_code} Ball {direction}</span>
<span style="color:#aaa">{ball_loc}</span>
<span style="color:#fff;font-weight:bold">{situation}</span></div>
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
<div style="position:absolute;left:{ball_pct}%;top:50%;transform:translate(-50%,-50%);{ball_style}">🏈</div>
<div style="position:absolute;left:5%;top:50%;transform:translate(-50%,-50%);color:#fff;font-weight:bold;font-size:12px">{away_code}</div>
<div style="position:absolute;left:95%;top:50%;transform:translate(-50%,-50%);color:#fff;font-weight:bold;font-size:12px">{home_code}</div></div>
<div style="display:flex;justify-content:space-between;margin-top:5px;color:#888;font-size:11px">
<span>← {away_code} EZ</span><span>10</span><span>20</span><span>30</span><span>40</span><span>50</span><span>40</span><span>30</span><span>20</span><span>10</span><span>{home_code} EZ →</span></div></div>"""


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
            home_abbrev, away_abbrev = None, None  # ESPN's actual abbreviations - KEY FIX
            for c in competitors:
                name = c.get("team", {}).get("displayName", "")
                team_name = TEAM_ABBREVS.get(name, name)
                team_id = c.get("team", {}).get("id", "")
                espn_abbrev = c.get("team", {}).get("abbreviation", "")  # Get ESPN's abbreviation
                score = int(c.get("score", 0) or 0)
                if c.get("homeAway") == "home":
                    home_team, home_score, home_id = team_name, score, team_id
                    home_abbrev = espn_abbrev
                else:
                    away_team, away_score, away_id = team_name, score, team_id
                    away_abbrev = espn_abbrev
            
            status_obj = event.get("status", {})
            status_type = status_obj.get("type", {}).get("name", "STATUS_SCHEDULED")
            clock = status_obj.get("displayClock", "")
            period = status_obj.get("period", 0)
            
            situation = comp.get("situation", {})
            down = situation.get("down")
            distance = situation.get("distance")
            yards_to_endzone = situation.get("yardsToEndzone", 50)
            possession_id = situation.get("possession", "")
            is_red_zone = situation.get("isRedZone", False)
            poss_text = situation.get("possessionText", "")
            
            # NEW: Get lastPlay for scoring detection
            last_play = situation.get("lastPlay", {})
            
            if possession_id == home_id:
                possession_team = home_team
                is_home_possession = True
            elif possession_id == away_id:
                possession_team = away_team
                is_home_possession = False
            else:
                possession_team = None
                is_home_possession = None
            
            game_date_str = event.get("date", "")
            try:
                game_date = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
            except:
                game_date = datetime.now(eastern)
            
            game_key = f"{away_team}@{home_team}"
            games[game_key] = {
                "event_id": event_id, "away_team": away_team, "home_team": home_team,
                "away_score": away_score, "home_score": home_score,
                "away_id": away_id, "home_id": home_id,
                "away_abbrev": away_abbrev, "home_abbrev": home_abbrev,  # KEY FIX: Store ESPN abbreviations
                "total": away_score + home_score,
                "period": period, "clock": clock, "status_type": status_type,
                "game_date": game_date, "down": down, "distance": distance,
                "yards_to_endzone": yards_to_endzone,
                "possession_team": possession_team, "is_red_zone": is_red_zone, "poss_text": poss_text,
                "is_home_possession": is_home_possession,
                "raw_possession_id": possession_id,
                "last_play": last_play  # NEW: Store lastPlay for scoring detection
            }
        return games
    except Exception as e:
        st.error(f"ESPN fetch error: {e}")
        return {}

def fetch_play_by_play(event_id):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={event_id}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        all_plays = []
        
        if "plays" in data:
            all_plays = data.get("plays", [])
        if not all_plays and "drives" in data:
            drives = data.get("drives", {})
            for drive in drives.get("previous", []):
                all_plays.extend(drive.get("plays", []))
            current = drives.get("current", {})
            if current:
                all_plays.extend(current.get("plays", []))
        
        if not all_plays:
            return []
        
        recent = list(reversed(all_plays[-5:] if len(all_plays) >= 5 else all_plays))
        plays = []
        
        for play in recent:
            play_text = play.get("text", "") or play.get("description", "") or ""
            is_scoring = play.get("scoringPlay", False)
            period_data = play.get("period", {})
            period = period_data.get("number", 0) if isinstance(period_data, dict) else (period_data or 0)
            clock_data = play.get("clock", {})
            clock = clock_data.get("displayValue", "") if isinstance(clock_data, dict) else str(clock_data or "")
            
            text_lower = play_text.lower()
            if is_scoring or "touchdown" in text_lower: icon = "🏈"
            elif "intercept" in text_lower or "fumble" in text_lower: icon = "🔴"
            elif "field goal" in text_lower: icon = "🥅"
            elif "punt" in text_lower or "kickoff" in text_lower: icon = "📤"
            elif "sack" in text_lower: icon = "💥"
            elif "incomplete" in text_lower: icon = "❌"
            elif "pass" in text_lower: icon = "🎯"
            elif any(x in text_lower for x in ["rush", "run ", "middle", "tackle", "guard", "end", "scramble"]): icon = "🏃"
            elif "kneel" in text_lower: icon = "🧎"
            elif "penalty" in text_lower: icon = "🚩"
            else: icon = "▶️"
            
            if play_text:
                plays.append({"text": play_text[:100] + "..." if len(play_text) > 100 else play_text,
                    "scoring": is_scoring, "period": period, "clock": clock, "icon": icon})
        return plays
    except:
        return []

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

# ========== ENHANCED ML SCORING ==========
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

def calc_ml_score(home_team, away_team, injuries, weather_data, last_5, last_games, game_date):
    """Enhanced 10-factor scoring system"""
    home = TEAM_STATS.get(home_team, {})
    away = TEAM_STATS.get(away_team, {})
    
    score_home, score_away = 0, 0
    reasons_home, reasons_away = [], []
    
    # FACTOR 1: DVOA (1.0 pts)
    home_dvoa = home.get('dvoa', 0)
    away_dvoa = away.get('dvoa', 0)
    dvoa_diff = home_dvoa - away_dvoa
    if dvoa_diff > 8:
        score_home += 1.0
        reasons_home.append(f"📊 DVOA +{home_dvoa:.0f}")
    elif dvoa_diff < -8:
        score_away += 1.0
        reasons_away.append(f"📊 DVOA +{away_dvoa:.0f}")
    
    # FACTOR 2: Defense Rank (1.0 pts)
    home_def = home.get('def_rank', 16)
    away_def = away.get('def_rank', 16)
    if home_def <= 5:
        score_home += 1.0
        reasons_home.append(f"🛡️ #{home_def} DEF")
    if away_def <= 5:
        score_away += 1.0
        reasons_away.append(f"🛡️ #{away_def} DEF")
    
    # FACTOR 3: Home Field (1.0 pts)
    score_home += 1.0
    reasons_home.append("🏠 Home")
    
    # FACTOR 4: Injuries (2.5 pts for QB out)
    home_inj, home_out, home_qb_out = get_injury_score(home_team, injuries)
    away_inj, away_out, away_qb_out = get_injury_score(away_team, injuries)
    
    if away_qb_out:
        score_home += 2.5
        reasons_home.append("🏥 Opp QB Out")
    if home_qb_out:
        score_away += 2.5
        reasons_away.append("🏥 Opp QB Out")
    
    # FACTOR 5: Home Win % (0.8 pts)
    home_hw = home.get('home_win_pct', 0.5)
    if home_hw > 0.65:
        score_home += 0.8
        reasons_home.append(f"🏟️ {int(home_hw*100)}% Home Win")
    
    # FACTOR 6: Away Win % (0.8 pts) - Road Warriors vs Road Kills
    away_aw = away.get('away_win_pct', 0.5)
    home_aw = home.get('away_win_pct', 0.5)
    if away_aw >= 0.60:
        score_away += 0.8
        reasons_away.append(f"✈️ {int(away_aw*100)}% Road Win")
    elif away_aw <= 0.35:
        score_home += 0.6
        reasons_home.append(f"✈️ Opp {int(away_aw*100)}% Road")
    
    # FACTOR 7: WEATHER GATE (1.5 pts)
    if weather_data and not weather_data.get("dome"):
        wind = weather_data.get("wind", 0)
        precip = weather_data.get("precip", 0)
        
        if wind >= 15 or precip > 0.1:
            # Penalize pass-heavy teams, boost run-heavy teams
            if away_team in PASS_HEAVY_TEAMS:
                score_home += 1.5
                reasons_home.append(f"🌧️ Wind {wind:.0f}")
            elif home_team in PASS_HEAVY_TEAMS:
                score_away += 1.5
                reasons_away.append(f"🌧️ Wind {wind:.0f}")
            
            if home_team in RUN_HEAVY_TEAMS:
                score_home += 0.8
                reasons_home.append("🏃 Run Game")
            elif away_team in RUN_HEAVY_TEAMS:
                score_away += 0.8
                reasons_away.append("🏃 Run Game")
    
    # FACTOR 8: REST DAYS (1.2 pts)
    if game_date and last_games:
        home_rest = get_rest_days(home_team, game_date, last_games)
        away_rest = get_rest_days(away_team, game_date, last_games)
        rest_diff = home_rest - away_rest
        
        if rest_diff >= 3:  # Home team more rested
            score_home += 1.2
            reasons_home.append(f"😴 +{rest_diff}d Rest")
        elif rest_diff <= -3:  # Away team more rested
            score_away += 1.2
            reasons_away.append(f"😴 +{abs(rest_diff)}d Rest")
        
        # Short week penalty (Thursday games)
        if home_rest <= 4:
            score_away += 0.5
            reasons_away.append("📅 Short Week")
        if away_rest <= 4:
            score_home += 0.5
            reasons_home.append("📅 Short Week")
    
    # FACTOR 9: RECENT FORM - Last 5 (1.5 pts)
    if last_5:
        home_form = last_5.get(home_team, {})
        away_form = last_5.get(away_team, {})
        
        if home_form.get("hot"):  # 4-1 or 5-0
            score_home += 1.5
            reasons_home.append(f"🔥 {home_form.get('form', '')}")
        elif home_form.get("cold"):  # 1-4 or 0-5
            score_away += 1.0
            reasons_away.append(f"❄️ Opp Cold")
        
        if away_form.get("hot"):
            score_away += 1.5
            reasons_away.append(f"🔥 {away_form.get('form', '')}")
        elif away_form.get("cold"):
            score_home += 1.0
            reasons_home.append(f"❄️ Opp Cold")
    
    # NORMALIZE TO 10-POINT SCALE
    total = score_home + score_away
    if total > 0:
        home_final = round((score_home / total) * 10, 1)
        away_final = round((score_away / total) * 10, 1)
    else:
        home_final, away_final = 5.0, 5.0
    
    if home_final >= away_final:
        return home_team, home_final, reasons_home[:5], home_out, away_out
    else:
        return away_team, away_final, reasons_away[:5], home_out, away_out

def get_signal_tier(score):
    if score >= 8.0:
        return "🟢 STRONG BUY", "#00ff00"
    elif score >= 6.5:
        return "🔵 BUY", "#00aaff"
    elif score >= 5.5:
        return "🟡 LEAN", "#ffff00"
    else:
        return "⚪ TOSS-UP", "#888888"

# ========== FETCH ALL DATA ==========
games = fetch_espn_scores()
game_list = sorted(list(games.keys()))
injuries = fetch_espn_injuries()
team_records = fetch_team_records()
last_5 = fetch_last_5_records()
last_games = fetch_team_schedules()
now = datetime.now(eastern)

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("⚡ LiveState")
    st.caption("Pre-resolution stress detection")
    st.markdown("""| State | Price Move |
|-------|------------|
| 🔴 **MAX** | 3-7¢ |
| 🟠 **ELEVATED** | 1-4¢ |
| 🟢 **NORMAL** | — |""")
    st.divider()
    st.header("📖 MONEYLINE LEGEND")
    st.markdown("🟢 **STRONG** → 8.0+\n\n🔵 **BUY** → 6.5-7.9\n\n🟡 **LEAN** → 5.5-6.4")
    st.divider()
    st.header("🧮 10-FACTOR MODEL")
    st.markdown("""
1. 📊 DVOA Rating
2. 🛡️ Defense Rank
3. 🏠 Home Field
4. 🏥 Injuries
5. 🏟️ Home Win %
6. ✈️ Away Win %
7. 🌧️ Weather Gate
8. 😴 Rest Days
9. 🔥 Recent Form
10. 📅 Short Week
""")
    st.divider()
    st.header("📊 DVOA GUIDE")
    st.caption("Defense-adjusted Value Over Average")
    st.markdown("""
| DVOA | Meaning |
|------|---------|
| **+20%+** | Elite |
| **+10-20%** | Playoff |
| **0-10%** | Above Avg |
| **-10-0%** | Below Avg |
| **-10%−** | Bad |
""")
    st.divider()
    
    # Show autorefresh status
    if HAS_AUTOREFRESH:
        st.caption("✅ streamlit-autorefresh installed")
    else:
        st.caption("⚠️ Install: pip install streamlit-autorefresh")
    
    st.caption("v2.1.1 NFL EDGE")

# ========== TITLE ==========
st.title("🏈 NFL EDGE FINDER")
st.caption("10-Factor ML Model + LiveState Tracker | v2.1.1")

# ========== LIVESTATE ==========
live_games = {k: v for k, v in games.items() if v['period'] > 0 and v['status_type'] != "STATUS_FINAL"}
final_games = {k: v for k, v in games.items() if v['status_type'] == "STATUS_FINAL"}

if live_games or final_games:
    st.subheader("⚡ LiveState — Live Uncertainty Tracker")
    
    hdr1, hdr2, hdr3 = st.columns([3, 1, 1])
    hdr1.caption(f"{auto_status} | {now.strftime('%I:%M:%S %p ET')} | v2.1.1")
    if hdr2.button("🔄 Auto" if not st.session_state.auto_refresh else "⏹️ Stop", use_container_width=True, key="auto_live"):
        st.session_state.auto_refresh = not st.session_state.auto_refresh
        st.rerun()
    if hdr3.button("🔄 Now", use_container_width=True, key="refresh_live"):
        st.rerun()
    
    for game_key, g in final_games.items():
        parts = game_key.split("@")
        winner = parts[1] if g['home_score'] > g['away_score'] else parts[0]
        winner_code = KALSHI_CODES.get(winner, winner[:3].upper())
        
        st.markdown(f"""<div style="background:linear-gradient(135deg,#1a2e1a,#0a1e0a);padding:18px;border-radius:12px;border:2px solid #44ff44;margin-bottom:15px">
            <div style="text-align:center"><b style="color:#fff;font-size:1.4em">{g['away_team']} {g['away_score']} @ {g['home_team']} {g['home_score']}</b>
                <span style="color:#44ff44;margin-left:20px;font-size:1.2em">✅ RESOLVED</span></div>
            <div style="background:#000;padding:12px;border-radius:8px;margin-top:12px;text-align:center">
                <span style="color:#44ff44;font-size:1.2em">FINAL | {winner_code} WIN</span></div></div>""", unsafe_allow_html=True)
    
    for game_key, g in live_games.items():
        quarter = g['period']
        clock_str = g['clock']
        score_diff = abs(g['home_score'] - g['away_score'])
        
        score_pressure = "Blowout" if score_diff >= 17 else "Two Poss" if score_diff >= 9 else "One Poss"
        
        if quarter >= 5:
            state_label, state_color, expected_leak, q_display = "MAX UNCERTAINTY", "#ff0000", "3-7¢", "🏈 OT"
        elif quarter == 4 and score_diff <= 8:
            state_label, state_color, expected_leak, q_display = "ELEVATED", "#ffaa00", "1-4¢", f"Q{quarter}"
        else:
            state_label, state_color, expected_leak, q_display = "NORMAL", "#44ff44", "—", f"Q{quarter}"
        
        clock_pressure = q_display + (" 🔴 RED ZONE" if g.get('is_red_zone') and g.get('possession_team') else "")
        
        st.markdown(f"""<div style="background:linear-gradient(135deg,#1a1a2e,#0a0a1e);padding:18px;border-radius:12px;border:2px solid {state_color};margin-bottom:15px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                <div style="flex:1"></div>
                <div style="text-align:center;flex:2"><b style="color:#fff;font-size:1.4em">{g['away_team']} {g['away_score']} @ {g['home_team']} {g['home_score']}</b></div>
                <div style="text-align:right;flex:1"><b style="color:{state_color};font-size:1.4em">{state_label}</b>
                    <div style="color:#888;font-size:0.85em">Move: {expected_leak}</div></div></div>
            <div style="background:#000;padding:15px;border-radius:8px;text-align:center">
                <span style="color:{state_color};font-size:1.3em;font-weight:bold">{q_display} {clock_str}</span></div>
            <div style="text-align:center;margin-top:12px"><span style="color:{state_color}">{clock_pressure}</span> • <span style="color:#ffaa44">{score_pressure}</span></div></div>""", unsafe_allow_html=True)
        
        # Use new ball position function with fallback logic
        parts = game_key.split("@")
        ball_yard, display_mode, poss_team, poss_text_display = get_ball_position_with_fallback(
            game_key, g, parts[0], parts[1]
        )
        
        st.markdown(render_football_field(
            ball_yard, g.get('down'), g.get('distance'), 
            poss_team, parts[0], parts[1], 
            g.get('yards_to_endzone'), poss_text_display, display_mode
        ), unsafe_allow_html=True)
        
        with st.expander("📋 Last 5 Plays", expanded=True):
            plays = fetch_play_by_play(g.get('event_id'))
            for p in plays:
                scoring_style = "background:#1a3d1a;border-left:3px solid #00ff00;" if p['scoring'] else ""
                st.markdown(f"""<div style="padding:8px;margin:4px 0;background:#111;border-radius:6px;{scoring_style}">
                    <span style="color:#888;font-size:0.8em">Q{p['period']} {p['clock']}</span>
                    <span style="margin-left:8px">{p['icon']}</span>
                    <span style="color:#fff;margin-left:8px">{p['text']}</span></div>""", unsafe_allow_html=True)
        
        st.link_button(f"🔗 Trade {game_key.replace('@', ' @ ')}", build_kalshi_ml_url(parts[0], parts[1], g.get('game_date')), use_container_width=True)
    
    st.divider()

# ========== ACTIVE POSITIONS ==========
st.subheader("📈 ACTIVE POSITIONS")

if not live_games and not final_games:
    hdr1, hdr2, hdr3 = st.columns([3, 1, 1])
    hdr1.caption(f"{auto_status} | {now.strftime('%I:%M:%S %p ET')} | v2.1.1")
    if hdr2.button("🔄 Auto" if not st.session_state.auto_refresh else "⏹️ Stop", use_container_width=True, key="auto_pos"):
        st.session_state.auto_refresh = not st.session_state.auto_refresh
        st.rerun()
    if hdr3.button("🔄 Refresh", use_container_width=True, key="refresh_pos"):
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
            pick_score = g['home_score'] if pick == home_team else g['away_score']
            opp_score = g['away_score'] if pick == home_team else g['home_score']
            lead = pick_score - opp_score
            is_final = g['status_type'] == "STATUS_FINAL"
            game_status = "FINAL" if is_final else f"Q{g['period']} {g['clock']}" if g['period'] > 0 else "SCHEDULED"
            
            if is_final:
                won = pick_score > opp_score
                status_label = "✅ WON!" if won else "❌ LOST"
                status_color = "#00ff00" if won else "#ff0000"
                pnl = f"+${potential_win:.2f}" if won else f"-${cost:.2f}"
                pnl_color = status_color
            elif g['period'] > 0:
                if lead >= 14: status_label, status_color = "🟢 CRUISING", "#00ff00"
                elif lead >= 7: status_label, status_color = "🟢 LEADING", "#00ff00"
                elif lead >= 1: status_label, status_color = "🟡 AHEAD", "#ffff00"
                elif lead >= -7: status_label, status_color = "🟠 CLOSE", "#ff8800"
                else: status_label, status_color = "🔴 BEHIND", "#ff0000"
                pnl, pnl_color = f"Win: +${potential_win:.2f}", "#888"
            else:
                status_label, status_color = "⏳ SCHEDULED", "#888"
                lead = 0
                pnl, pnl_color = f"Win: +${potential_win:.2f}", "#888"
            
            st.markdown(f"""<div style='background:linear-gradient(135deg,#1a1a2e,#16213e);padding:15px;border-radius:10px;border:2px solid {status_color};margin-bottom:10px'>
            <div style='display:flex;justify-content:space-between'><div><b style='color:#fff;font-size:1.2em'>{game_key.replace('@', ' @ ')}</b> <span style='color:#888'>{game_status}</span></div>
            <b style='color:{status_color};font-size:1.3em'>{status_label}</b></div>
            <div style='margin-top:10px;color:#aaa'>🎯 Pick: <b style='color:#fff'>{pick}</b> | 💵 {contracts}x @ {price}¢ (${cost:.2f}) | 📊 {pick_score}-{opp_score} | Lead: <b style='color:{status_color}'>{lead:+d}</b> | <span style='color:{pnl_color}'>{pnl}</span></div></div>""", unsafe_allow_html=True)
            
            btn1, btn2, btn3 = st.columns([3, 1, 1])
            btn1.link_button("🔗 Trade on Kalshi", build_kalshi_ml_url(parts[0], parts[1], g.get('game_date')), use_container_width=True)
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
                pick_idx = pick_options.index(pos.get('pick', parts[1])) if pos.get('pick', parts[1]) in pick_options else 0
                new_pick = e3.radio("Pick", pick_options, index=pick_idx, horizontal=True, key=f"pick_{idx}")
                
                if st.button("💾 Save", key=f"save_{idx}", type="primary"):
                    st.session_state.positions[idx].update({'price': new_price, 'contracts': new_contracts, 'pick': new_pick})
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

# ========== INJURY REPORT ==========
st.subheader("🏥 INJURY REPORT")

def get_key_injuries(injuries):
    key_injuries = []
    for team, team_injuries in injuries.items():
        stars = STAR_PLAYERS.get(team, [])
        for inj in team_injuries:
            name = inj.get("name", "")
            status = inj.get("status", "").upper()
            position = inj.get("position", "").upper()
            
            if "OUT" not in status and "DOUBTFUL" not in status:
                continue
            
            is_star = any(star.lower() in name.lower() for star in stars)
            is_qb = position == "QB"
            
            if is_qb:
                star_rating, icon = 3, "🏈"
            elif is_star:
                star_rating, icon = 2, "🔥"
            elif position in ["RB", "WR", "TE"]:
                star_rating, icon = 1, "🏈"
            else:
                continue
            
            key_injuries.append({"name": name, "team": team, "position": position,
                "status": "OUT" if "OUT" in status else "DOUBT", "stars": star_rating, "icon": icon, "is_qb": is_qb})
    
    key_injuries.sort(key=lambda x: (x['stars'], x['is_qb']), reverse=True)
    return key_injuries[:12]

key_injuries = get_key_injuries(injuries)

if key_injuries:
    cols = st.columns(3)
    for i, inj in enumerate(key_injuries):
        with cols[i % 3]:
            stars_display = "⭐" * inj['stars']
            st.markdown(f"""<div style="background:linear-gradient(135deg,#1a1a2e,#16213e);padding:12px;border-radius:8px;border-left:3px solid #ff4444;margin-bottom:8px">
                <div style="color:#ffaa00;font-size:0.9em">{stars_display} <b style="color:#fff">{inj['name']}</b> {inj['icon']}</div>
                <div style="color:#ff6666;font-size:0.85em;margin-top:4px">{inj['status']} • {inj['team']}</div></div>""", unsafe_allow_html=True)
    
    injury_counts = {}
    for inj in key_injuries:
        injury_counts[inj['team']] = injury_counts.get(inj['team'], 0) + 1
    
    multi_injury_teams = [t for t, c in injury_counts.items() if c >= 2]
    if multi_injury_teams:
        st.markdown(f"""<div style="background:#1a2a3a;padding:10px;border-radius:6px;margin-top:10px">
            <span style="color:#ff8888">⚠️ Multiple Key Injuries:</span> <span style="color:#ffaa00">{", ".join(multi_injury_teams)}</span></div>""", unsafe_allow_html=True)
else:
    st.info("No major injuries reported")

st.divider()

# ========== RECENT FORM ==========
st.subheader("🔥 TEAM FORM (Last 5)")

if last_5:
    hot_teams = [t for t, f in last_5.items() if f.get("hot")]
    cold_teams = [t for t, f in last_5.items() if f.get("cold")]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔥 HOT TEAMS (4-1 or better)**")
        if hot_teams:
            for team in hot_teams:
                form = last_5[team].get('form', '')
                st.markdown(f"""<div style="background:#1a3d1a;padding:8px 12px;border-radius:6px;margin-bottom:4px;border-left:3px solid #00ff00">
                    <b style="color:#00ff00">{team}</b> <span style="color:#888;margin-left:10px">{form}</span></div>""", unsafe_allow_html=True)
        else:
            st.caption("No hot teams")
    
    with col2:
        st.markdown("**❄️ COLD TEAMS (1-4 or worse)**")
        if cold_teams:
            for team in cold_teams:
                form = last_5[team].get('form', '')
                st.markdown(f"""<div style="background:#3d1a1a;padding:8px 12px;border-radius:6px;margin-bottom:4px;border-left:3px solid #ff4444">
                    <b style="color:#ff4444">{team}</b> <span style="color:#888;margin-left:10px">{form}</span></div>""", unsafe_allow_html=True)
        else:
            st.caption("No cold teams")

st.divider()

# ========== ML PICKS ==========
st.subheader("🎯 PRE-GAME NFL MONEYLINE PICKS")

ml_results = []
for game_key, g in games.items():
    if g['status_type'] != "STATUS_SCHEDULED":
        continue
    away = g["away_team"]
    home = g["home_team"]
    
    weather_data = get_weather_for_game(home)
    
    try:
        pick, score, reasons, home_out, away_out = calc_ml_score(home, away, injuries, weather_data, last_5, last_games, g.get('game_date'))
        tier, color = get_signal_tier(score)
        
        # Get DVOA for both teams
        home_dvoa = TEAM_STATS.get(home, {}).get('dvoa', 0)
        away_dvoa = TEAM_STATS.get(away, {}).get('dvoa', 0)
        
        ml_results.append({
            "pick": pick, "score": score, "color": color, "reasons": reasons,
            "away": away, "home": home, "game_date": g.get('game_date'), "game_key": game_key,
            "weather": weather_data, "home_out": home_out, "away_out": away_out,
            "home_dvoa": home_dvoa, "away_dvoa": away_dvoa
        })
    except:
        continue

ml_results.sort(key=lambda x: x["score"], reverse=True)

if ml_results:
    for r in ml_results:
        
        pick_team = r["pick"]
        pick_code = KALSHI_CODES.get(pick_team, pick_team[:3].upper())
        opponent = r["away"] if pick_team == r["home"] else r["home"]
        reasons_str = " • ".join(r["reasons"])
        
        # Weather badge
        weather = r.get("weather", {})
        if weather.get("dome"):
            weather_badge = "🏟️ Dome"
        elif weather.get("impact") == "severe":
            weather_badge = f"⛈️ {weather.get('wind', 0):.0f}mph"
        elif weather.get("impact") == "moderate":
            weather_badge = f"🌧️ {weather.get('wind', 0):.0f}mph"
        else:
            weather_badge = f"☀️ {weather.get('temp', 70):.0f}°F"
        
        away_code = KALSHI_CODES.get(r["away"], "XXX")
        home_code = KALSHI_CODES.get(r["home"], "XXX")
        date_str = r["game_date"].strftime("%y%b%d").upper() if r["game_date"] else datetime.now(eastern).strftime("%y%b%d").upper()
        ticker = f"KXNFLGAME-{date_str}{away_code}{home_code}"
        this_url = f"https://kalshi.com/markets/KXNFLGAME/{ticker}"
        
        # Build injury display
        home_out = r.get("home_out", [])
        away_out = r.get("away_out", [])
        injury_html = ""
        if home_out or away_out:
            injury_parts = []
            if away_out:
                away_inj_str = ", ".join([p.replace("🚨 ", "") + " OUT" for p in away_out[:2]])
                injury_parts.append(f"<span style='color:#ff6666'>{KALSHI_CODES.get(r['away'], 'AWY')}: {away_inj_str}</span>")
            if home_out:
                home_inj_str = ", ".join([p.replace("🚨 ", "") + " OUT" for p in home_out[:2]])
                injury_parts.append(f"<span style='color:#ff6666'>{KALSHI_CODES.get(r['home'], 'HME')}: {home_inj_str}</span>")
            injury_html = f"<div style='color:#ff8888;font-size:0.8em;margin-top:4px'>🏥 {' | '.join(injury_parts)}</div>"
        
        # DVOA display for both teams (PICK first, then opponent)
        home_dvoa = r.get("home_dvoa", 0)
        away_dvoa = r.get("away_dvoa", 0)
        
        # Determine which is pick and which is opponent
        if pick_team == r["home"]:
            pick_dvoa = home_dvoa
            opp_dvoa = away_dvoa
            pick_code = KALSHI_CODES.get(r["home"], "HME")
            opp_code = KALSHI_CODES.get(r["away"], "AWY")
        else:
            pick_dvoa = away_dvoa
            opp_dvoa = home_dvoa
            pick_code = KALSHI_CODES.get(r["away"], "AWY")
            opp_code = KALSHI_CODES.get(r["home"], "HME")
        
        pick_dvoa_color = "#00ff00" if pick_dvoa >= 10 else "#ffff00" if pick_dvoa >= 0 else "#ff6666"
        opp_dvoa_color = "#00ff00" if opp_dvoa >= 10 else "#ffff00" if opp_dvoa >= 0 else "#ff6666"
        dvoa_html = f"<div style='font-size:0.8em;margin-top:4px'>📊 DVOA: <span style='color:{pick_dvoa_color}'>{pick_code} {pick_dvoa:+.1f}%</span> vs <span style='color:{opp_dvoa_color}'>{opp_code} {opp_dvoa:+.1f}%</span></div>"
        
        st.markdown(f"""<div style="background:linear-gradient(135deg,#0f172a,#020617);padding:10px 12px;margin-bottom:4px;border-radius:6px;border-left:3px solid {r['color']}">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <div><b style="color:#fff">{pick_team}</b> <span style="color:#666">vs {opponent}</span></div>
            <div><span style="background:#1e3a5f;padding:2px 8px;border-radius:4px;color:#88ccff;font-size:0.8em;margin-right:8px">{weather_badge}</span>
            <span style="color:#38bdf8;font-weight:bold">{r['score']}/10</span></div>
        </div>
        <div style="color:#777;font-size:0.85em;margin-top:4px">{reasons_str}</div>
        {dvoa_html}
        {injury_html}</div>""", unsafe_allow_html=True)
        
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
            "game": game_key, "type": "ml", "pick": st.session_state.selected_ml_pick,
            "price": price_paid, "contracts": contracts,
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
            status = "FINAL" if g['status_type'] == "STATUS_FINAL" else f"Q{g['period']} {g['clock']}" if g['period'] > 0 else "SCHEDULED"
            st.caption(f"{status} | {g['total']} pts")
else:
    st.info("No games this week")

st.divider()
st.caption("⚠️ Educational analysis only. Not financial advice. v2.1.1")
