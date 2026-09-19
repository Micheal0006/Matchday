"""
Matchday — real-data football match predictor (football-data.org edition).

Free tier of football-data.org gives you 12 major competitions and doesn't
require a card. It works by picking a league, then two teams within it,
rather than searching any team globally.

Setup:
1. Get your free token: https://www.football-data.org/client/register
   (arrives by email — no card needed)
2. Copy .env.example to .env and paste your token in
3. pip install -r requirements.txt
4. python app.py
5. Open http://localhost:5000
"""

import os
import math
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN", "")
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_TOKEN}

app = Flask(__name__)

LEAGUE_AVG_GOALS = 1.4
HOME_ADVANTAGE = 1.12
MAX_GOALS = 6

COMPETITIONS = [
    {"code": "PL", "name": "Premier League (England)"},
    {"code": "PD", "name": "La Liga (Spain)"},
    {"code": "BL1", "name": "Bundesliga (Germany)"},
    {"code": "SA", "name": "Serie A (Italy)"},
    {"code": "FL1", "name": "Ligue 1 (France)"},
    {"code": "DED", "name": "Eredivisie (Netherlands)"},
    {"code": "PPL", "name": "Primeira Liga (Portugal)"},
    {"code": "ELC", "name": "Championship (England)"},
    {"code": "BSA", "name": "Campeonato Brasileiro Série A (Brazil)"},
    {"code": "CL", "name": "UEFA Champions League"},
]


def api_get(path, params=None):
    if not API_TOKEN:
        raise RuntimeError(
            "No API token set. Add FOOTBALL_DATA_TOKEN to your .env file — "
            "see README.md for how to get a free one."
        )
    resp = requests.get(f"{BASE_URL}/{path}", headers=HEADERS, params=params or {}, timeout=15)
    if resp.status_code == 429:
        raise RuntimeError("Rate limit hit (free tier: 10 requests/minute) — wait a moment and try again.")
    resp.raise_for_status()
    return resp.json()


def get_teams(competition_code):
    data = api_get(f"competitions/{competition_code}/teams")
    return [
        {"id": t["id"], "name": t["name"], "crest": t.get("crest")}
        for t in data.get("teams", [])
    ]


def get_team_matches(team_id, limit=20):
    """Fetch this team's recent finished matches, most recent first."""
    data = api_get(f"teams/{team_id}/matches", {"status": "FINISHED", "limit": limit})
    matches = data.get("matches", [])
    matches.sort(key=lambda m: m["utcDate"], reverse=True)
    return matches


def compute_form(team_id, matches, last=5):
    recent = matches[:last]
    goals_for, goals_against, form_points = [], [], []

    for m in recent:
        home = m["homeTeam"]
        ft = m["score"]["fullTime"]
        if ft["home"] is None or ft["away"] is None:
            continue
        is_home = home["id"] == team_id
        gf = ft["home"] if is_home else ft["away"]
        ga = ft["away"] if is_home else ft["home"]
        goals_for.append(gf)
        goals_against.append(ga)
        if gf > ga:
            form_points.append(1.0)
        elif gf == ga:
            form_points.append(0.5)
        else:
            form_points.append(0.0)

    n = max(len(goals_for), 1)
    return {
        "games_found": len(goals_for),
        "avg_scored": sum(goals_for) / n if goals_for else LEAGUE_AVG_GOALS,
        "avg_conceded": sum(goals_against) / n if goals_against else LEAGUE_AVG_GOALS,
        "form": sum(form_points) / n if form_points else 0.5,
    }


def compute_h2h(home_id, away_id, home_matches, last=5):
    meetings = [
        m for m in home_matches
        if m["homeTeam"]["id"] == away_id or m["awayTeam"]["id"] == away_id
    ]
    meetings = meetings[:last]

    home_wins, played = 0, 0
    for m in meetings:
        ft = m["score"]["fullTime"]
        if ft["home"] is None or ft["away"] is None:
            continue
        played += 1
        home_team_id_in_match = m["homeTeam"]["id"]
        if ft["home"] > ft["away"]:
            winner_id = home_team_id_in_match
        elif ft["away"] > ft["home"]:
            winner_id = m["awayTeam"]["id"]
        else:
            winner_id = None
        if winner_id == home_id:
            home_wins += 1

    return {"played": played, "home_wins": home_wins}


def poisson_pmf(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def run_prediction(home_form, away_form, h2h):
    attack_home = (home_form["avg_scored"] / LEAGUE_AVG_GOALS) * (0.85 + home_form["form"] * 0.3)
    attack_away = (away_form["avg_scored"] / LEAGUE_AVG_GOALS) * (0.85 + away_form["form"] * 0.3)
    defense_home = home_form["avg_conceded"] / LEAGUE_AVG_GOALS
    defense_away = away_form["avg_conceded"] / LEAGUE_AVG_GOALS

    lambda_home = LEAGUE_AVG_GOALS * ((attack_home + defense_away) / 2) * HOME_ADVANTAGE
    lambda_away = LEAGUE_AVG_GOALS * ((attack_away + defense_home) / 2)

    if h2h["played"] > 0:
        h2h_ratio = h2h["home_wins"] / h2h["played"]
        skew = (h2h_ratio - 0.5) * 0.24
        lambda_home *= (1 + skew)
        lambda_away *= (1 - skew)

    lambda_home = max(0.15, lambda_home)
    lambda_away = max(0.15, lambda_away)

    p_home, p_draw, p_away = 0.0, 0.0, 0.0
    best = {"h": 0, "a": 0, "p": -1}

    for h in range(MAX_GOALS + 1):
        for a in range(MAX_GOALS + 1):
            p = poisson_pmf(h, lambda_home) * poisson_pmf(a, lambda_away)
            if h > a:
                p_home += p
            elif h == a:
                p_draw += p
            else:
                p_away += p
            if p > best["p

def compute_form(team_id, matches, last=5):
    recent = matches[:last]
    goals_for, goals_against, form_points = [], [], []

    for m in recent:
        home = m["homeTeam"]
        ft = m["score"]["fullTime"]
        if ft["home"] is None or ft["away"] is None:
            continue
        is_home = home["id"] == team_id
        gf = ft["home"] if is_home else ft["away"]
        ga = ft["away"] if is_home else ft["home"]
        goals_for.append(gf)
        goals_against.append(ga)
        if gf > ga:
            form_points.append(1.0)
        elif gf == ga:
            form_points.append(0.5)
        else:
            form_points.append(0.0)

    n = max(len(goals_for), 1)
    return {
        "games_found": len(goals_for),
        "avg_scored": sum(goals_for) / n if goals_for else LEAGUE_AVG_GOALS,
        "avg_conceded": sum(goals_against) / n if goals_against else LEAGUE_AVG_GOALS,
        "form": sum(form_points) / n if form_points else 0.5,
    }


def compute_h2h(home_id, away_id, home_matches, last=5):
    meetings = [
        m for m in home_matches
        if m["homeTeam"]["id"] == away_id or m["awayTeam"]["id"] == away_id
    ]
    meetings = meetings[:last]

    home_wins, played = 0, 0
    for m in meetings:
        ft = m["score"]["fullTime"]
        if ft["home"] is None or ft["away"] is None:
            continue
        played += 1
        home_team_id_in_match = m["homeTeam"]["id"]
        if ft["home"] > ft["away"]:
            winner_id = home_team_id_in_match
        elif ft["away"] > ft["home"]:
            winner_id = m["awayTeam"]["id"]
        else:
            winner_id = None
        if winner_id == home_id:
            home_wins += 1

    return {"played": played, "home_wins": home_wins}


def poisson_pmf(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def run_prediction(home_form, away_form, h2h):
    attack_home = (home_form["avg_scored"] / LEAGUE_AVG_GOALS) * (0.85 + home_form["form"] * 0.3)
    attack_away = (away_form["avg_scored"] / LEAGUE_AVG_GOALS) * (0.85 + away_form["form"] * 0.3)
    defense_home = home_form["avg_conceded"] / LEAGUE_AVG_GOALS
    defense_away = away_form["avg_conceded"] / LEAGUE_AVG_GOALS

    lambda_home = LEAGUE_AVG_GOALS * ((attack_home + defense_away) / 2) * HOME_ADVANTAGE
    lambda_away = LEAGUE_AVG_GOALS * ((attack_away + defense_home) / 2)

    if h2h["played"] > 0:
        h2h_ratio = h2h["home_wins"] / h2h["played"]
        skew = (h2h_ratio - 0.5) * 0.24
        lambda_home *= (1 + skew)
        lambda_away *= (1 - skew)

    lambda_home = max(0.15, lambda_home)
    lambda_away = max(0.15, lambda_away)

    p_home, p_draw, p_away = 0.0, 0.0, 0.0
    best = {"h": 0, "a": 0, "p": -1}

    for h in range(MAX_GOALS + 1):
        for a in range(MAX_GOALS + 1):
            p = poisson_pmf(h, lambda_home) * poisson_pmf(a, lambda_away)
            if h > a:
                p_home += p
            elif h == a:
                p_draw += p
            else:
                p_away += p
            if p > best["p
