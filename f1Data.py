import os
import fastf1
import sqlite3
import pandas as pd
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Setup caching - faster data
os.makedirs("cache", exist_ok=True)
fastf1.Cache.enable_cache("cache")

# DATABASE
def init_db():
    conn = sqlite3.connect('f1_custom.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_results
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season INTEGER,
            race TEXT,
            name TEXT,
            team TEXT,
            lap_time_seconds REAL,
            total_race_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# as it says
def seconds_to_str(seconds):
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins}:{secs:06.3f}"

@app.route("/")
def home():
    return render_template("DataPage.html")

# all APP.ROUTE is flask doing its job
@app.route("/add_entry", methods=["POST"])
def add_entry():
    data = request.json
    try:
        # Parse lap time to seconds for sorting/math
        time_parts = data['time'].split(':')
        seconds = float(time_parts[0]) * 60 + float(time_parts[1])

        conn = sqlite3.connect('f1_custom.db')
        cursor = conn.cursor()
        # CHANGED: We now insert data['time'] instead of the hardcoded string "FINISHED"
        cursor.execute("""
            INSERT INTO custom_results (season, race, name, team, lap_time_seconds, total_race_time)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (data['season'], data['race'], data['name'], data['team'], seconds, data['time']))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/delete_entry", methods=["POST"])
def delete_entry():
    entry_id = request.json.get('id')
    conn = sqlite3.connect('f1_custom.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM custom_results WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})


@app.route("/results")
def results():
    season = request.args.get("season", default=2026, type=int)
    race = request.args.get("race", type=str)

    all_drivers = []
    combined_fastest = []

    # 1. Fetch Official FastF1 Data first (to get the winner's time)
    winner_seconds = 0
    try:
        session = fastf1.get_session(season, race, "R")
        session.load(laps=True, telemetry=False, weather=False)

        for _, row in session.results.iterrows():
            # Get winner's total time to calculate gaps later
            if row['Position'] == 1 and pd.notnull(row['Time']):
                winner_seconds = row['Time'].total_seconds()

            # Store driver info
            res_val = row['Status']
            sort_val = row['Position']  # Use official position for sorting

            if pd.notnull(row['Time']):
                td = row['Time']
                res_val = str(td).split('0 days ')[-1][:12] if row['Position'] == 1 else f"+{td.total_seconds():.3f}s"

            all_drivers.append({
                "id": None,
                "isUser": False,
                "SortKey": sort_val,
                "Abbreviation": row['Abbreviation'],
                "TeamName": row['TeamName'],
                "Result": res_val
            })

        # Fastest Lap Logic
        laps = session.laps.dropna(subset=["LapTime"])
        fastest_df = laps.groupby("Driver")["LapTime"].min().reset_index()
        for row in fastest_df.itertuples():
            team = session.results.loc[session.results["Abbreviation"] == row.Driver, "TeamName"].values[0]
            combined_fastest.append({
                "id": None, "Abbreviation": row.Driver, "TeamName": team, "Seconds": row.LapTime.total_seconds()
            })

    except Exception as f1_e:
        print(f"FastF1 Error: {f1_e}")

    # 2. Fetch User Data and Insert into the list
    try:
        conn = sqlite3.connect('f1_custom.db')
        cursor = conn.cursor()
        query = "SELECT id, name, team, lap_time_seconds, total_race_time FROM custom_results WHERE season=? AND race LIKE ?"
        cursor.execute(query, (season, f"%{race}%"))
        user_rows = cursor.fetchall()
        conn.close()

        for row in user_rows:
            user_label = f"{row[1]} (YOU)"
            user_seconds = row[3]

            # For the Race Classification: Calculate gap to F1 winner
            # Use a SortKey of 100 + seconds to place you after the winner
            gap_to_winner = user_seconds - winner_seconds if winner_seconds > 0 else 0
            display_result = row[4] if gap_to_winner <= 0 else f"+{gap_to_winner:.3f}s"

            all_drivers.append({
                "id": row[0],
                "isUser": True,
                "SortKey": 1.5 if gap_to_winner <= 0 else 2 + (gap_to_winner / 1000),
                "Abbreviation": user_label,
                "TeamName": row[2],
                "Result": display_result
            })

            combined_fastest.append({
                "id": row[0], "Abbreviation": user_label,
                "TeamName": row[2], "Seconds": user_seconds
            })
    except Exception as db_e:
        print(f"Database Error: {db_e}")

    if not all_drivers and not combined_fastest:
        return jsonify({"error": "No data found."}), 404

    # 3. Final Sorting
    # Sort Race Classification by the SortKey created
    all_drivers.sort(key=lambda x: x['SortKey'])

    # Re-assign positions based on the new sorted order
    for i, driver in enumerate(all_drivers, 1):
        driver['Position'] = i

    # Sort Fastest Laps
    combined_fastest.sort(key=lambda x: x['Seconds'])
    best_lap = combined_fastest[0]['Seconds'] if combined_fastest else 0
    fastest_list = []
    for i, d in enumerate(combined_fastest, 1):
        gap = d['Seconds'] - best_lap
        fastest_list.append({
            "id": d['id'], "Position": i, "Abbreviation": d['Abbreviation'],
            "TeamName": d['TeamName'], "LapTime": seconds_to_str(d['Seconds']),
            "Gap": "FASTEST" if gap < 0.0001 else f"+{gap:.3f}"
        })

    return jsonify({"finish_order": all_drivers, "fastest_laps": fastest_list})

if __name__ == "__main__":
    app.run(port=5000, debug=True)