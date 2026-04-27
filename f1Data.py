import os
import fastf1
import sqlite3
import pandas as pd
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Setup caching
os.makedirs("cache", exist_ok=True)
fastf1.Cache.enable_cache("cache")


# Database Initialization
def init_db():
    conn = sqlite3.connect('f1_custom.db')
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS custom_results
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       season
                       INTEGER,
                       race
                       TEXT,
                       name
                       TEXT,
                       team
                       TEXT,
                       lap_time_seconds
                       REAL,
                       total_race_time
                       TEXT
                   )
                   ''')
    conn.commit()
    conn.close()


init_db()


# get the data from the base at put it into a new format
def format_to_f1_standard(seconds):
    """Converts seconds to H:MM:SS.ms or MM:SS.ms"""
    if seconds == float('inf') or seconds is None:
        return ""

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:06.3f}"
    else:
        return f"{minutes}:{secs:06.3f}"


# 4. Routes
@app.route("/")
@app.route("/DataPage.html")
def datapage():
    return render_template("DataPage.html")


@app.route("/add_entry", methods=["POST"])
def add_entry():
    data = request.json
    try:
        # the time
        parts = data['time'].replace(',', '.').split(':')
        if len(parts) == 3:  # H:MM:SS
            total_seconds = (float(parts[0]) * 3600) + (float(parts[1]) * 60) + float(parts[2])
        elif len(parts) == 2:  # MM:SS
            total_seconds = (float(parts[0]) * 60) + float(parts[1])
        else:
            total_seconds = float(parts[0])

        conn = sqlite3.connect('f1_custom.db')
        cursor = conn.cursor()
        cursor.execute("""
                       INSERT INTO custom_results (season, race, name, team, lap_time_seconds, total_race_time)
                       VALUES (?, ?, ?, ?, ?, ?)
                       """, (data['season'], data['race'], data['name'], data['team'], total_seconds, data['time']))
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

    all_drivers_raw = []
    combined_fastest = []

    # Fetch Official Data
    try:
        session = fastf1.get_session(season, race, "R")
        session.load(laps=True, telemetry=False, weather=False)

        # Get winner's total time
        winner_row = session.results.loc[session.results['Position'] == 1].iloc[0]
        winner_total_seconds = winner_row['Time'].total_seconds()

        for _, row in session.results.iterrows():
            if pd.isnull(row['Time']):
                total_sec = float('inf')
            else:
                # Add gap to winner's time for everyone except P1 which is WINNER
                if row['Position'] == 1:
                    total_sec = winner_total_seconds
                else:
                    total_sec = winner_total_seconds + row['Time'].total_seconds()

            all_drivers_raw.append({
                "isUser": False,
                "SortKey": total_sec,
                "Abbreviation": row['Abbreviation'],
                "TeamName": row['TeamName'],
                "Status": row['Status']
            })

        # Fastest laps
        laps = session.laps.dropna(subset=["LapTime"])
        fastest_df = laps.groupby("Driver")["LapTime"].min().reset_index()
        for row in fastest_df.itertuples():
            team = session.results.loc[session.results["Abbreviation"] == row.Driver, "TeamName"].values[0]
            combined_fastest.append({
                "id": None, "Abbreviation": row.Driver, "TeamName": team, "Seconds": row.LapTime.total_seconds()
            })
    except Exception as e:
        print(f"F1 Error: {e}")

    # Fetch User Data
    try:
        conn = sqlite3.connect('f1_custom.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, team, lap_time_seconds FROM custom_results WHERE season=? AND race LIKE ?",
                       (season, f"%{race}%"))
        for row in cursor.fetchall():
            all_drivers_raw.append({
                "id": row[0], "isUser": True, "SortKey": row[3],
                "Abbreviation": f"{row[1]} (YOU)", "TeamName": row[2], "Status": "Finished"
            })
            combined_fastest.append({
                "id": row[0], "Abbreviation": f"{row[1]} (YOU)", "TeamName": row[2], "Seconds": row[3]
            })
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

    # Global Ranking
    all_drivers_raw.sort(key=lambda x: x['SortKey'])
    global_winner_time = all_drivers_raw[0]['SortKey'] if all_drivers_raw else 0

    final_finish_order = []
    for i, d in enumerate(all_drivers_raw, 1):
        if d['SortKey'] == float('inf'):
            display_time = d['Status']
            gap_str = "—"
        else:
            # This uses the H:MM:SS for time display
            display_time = format_to_f1_standard(d['SortKey'])
            gap_str = "WINNER" if i == 1 else f"+{d['SortKey'] - global_winner_time:.3f}s"

        final_finish_order.append({
            "Position": i,
            "isUser": d.get('isUser', False),
            "Abbreviation": d['Abbreviation'],
            "TeamName": d['TeamName'],
            "Time": display_time,
            "Gap": gap_str
        })

    # Fastest Laps
    combined_fastest.sort(key=lambda x: x['Seconds'])
    best_lap = combined_fastest[0]['Seconds'] if combined_fastest else 0
    final_fastest = []
    for i, d in enumerate(combined_fastest, 1):
        gap = d['Seconds'] - best_lap
        final_fastest.append({
            "id": d.get('id'),
            "Position": i,
            "Abbreviation": d['Abbreviation'],
            "TeamName": d['TeamName'],
            "LapTime": format_to_f1_standard(d['Seconds']),
            "Gap": "FASTEST" if gap < 0.001 else f"+{gap:.3f}"
        })

    return jsonify({
        "finish_order": final_finish_order,
        "fastest_laps": final_fastest
    })


if __name__ == "__main__":
    app.run(port=5000, debug=True)