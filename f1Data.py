import sqlite3
import os
import fastf1
from flask import Flask, jsonify, render_template, request
import pandas as pd

app = Flask(__name__)

DB_PATH = 'race_data.db'
os.makedirs("cache", exist_ok=True)
fastf1.Cache.enable_cache("cache")
fastf1.set_log_level("INFO")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS custom_results
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       driver_name
                       TEXT,
                       team_name
                       TEXT,
                       lap_time_seconds
                       REAL
                   )
                   ''')
    conn.commit()
    conn.close()


init_db()


def format_seconds_to_laptime(seconds):
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    return f"{minutes:02d}:{rem_seconds:06.3f}"


@app.route("/add")
def add_lap():
    driver = request.args.get('driver')
    team = request.args.get('team')
    time = request.args.get('time', type=float)
    if driver and team and time:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO custom_results (driver_name, team_name, lap_time_seconds) VALUES (?, ?, ?)",
                       (driver, team, time))
        conn.commit()
        conn.close()
        return f"Added {driver}"
    return "Error", 400


@app.route("/delete/<int:entry_id>")
def delete_entry(entry_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM custom_results WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    return "Deleted"


@app.route("/results")
def results():
    season = request.args.get("season", default=2026, type=int)
    race = request.args.get("race", type=str)
    all_drivers = []

    # A. Get FastF1 Data
    if race:
        try:
            session = fastf1.get_session(season, race, "R")
            session.load(laps=True, telemetry=False, weather=False, messages=False)
            laps_data = session.laps.dropna(subset=["LapTime"])
            last_laps = laps_data.sort_values("LapNumber").groupby("Driver").tail(1)
            for _, row in last_laps.iterrows():
                all_drivers.append({
                    "id": None, "Abbreviation": row["Driver"], "TeamName": row["Team"],
                    "Seconds": row["LapTime"].total_seconds(), "Source": "F1"
                })
        except:
            pass

    # B. Get SQL Data
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, driver_name, team_name, lap_time_seconds FROM custom_results")
    for row in cursor.fetchall():
        all_drivers.append({
            "id": row[0], "Abbreviation": row[1], "TeamName": row[2],
            "Seconds": row[3], "Source": "Manual"
        })
    conn.close()

    if not all_drivers: return jsonify({"race": [], "fastest": []})

    # C. Sort by time and identify the Absolute Leader (P1)
    combined_df = pd.DataFrame(all_drivers).sort_values("Seconds")
    leader_time = combined_df.iloc[0]["Seconds"]

    race_list = []
    fastest_list = []

    for i, row in enumerate(combined_df.itertuples(), 1):
        lap_str = format_seconds_to_laptime(row.Seconds)
        # GAP CALCULATION (Difference in pace to the fastest overall lap)
        gap_seconds = row.Seconds - leader_time
        gap_str = "LEADER" if i == 1 else f"+{gap_seconds:.3f}"

        # Data for Race Table
        race_list.append({
            "Position": i, "id": row.id, "Abbreviation": row.Abbreviation,
            "TeamName": row.TeamName, "LapTime": lap_str,
            "LastLapGap": gap_str, "Source": row.Source
        })

        # Data for Fastest Lap Table
        fastest_list.append({
            "Position": i, "Abbreviation": row.Abbreviation, "TeamName": row.TeamName,
            "FastestLap": lap_str, "FastestLapGap": gap_str, "Source": row.Source
        })

    return jsonify({"race": race_list, "fastest": fastest_list})


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(port=5000, debug=True)