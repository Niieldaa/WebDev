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
    if seconds == float('inf') or seconds is None:
        return ""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:06.3f}"
    else:
        return f"{minutes}:{secs:06.3f}"


# Routes in case we put all into a localhost
@app.route("/")
@app.route("/DataPage.html")
def datapage():
    return render_template("DataPage.html")


@app.route("/add_entry", methods=["POST"])
def add_entry():
    data = request.json
    try:
        parts = data['time'].replace(',', '.').split(':')
        if len(parts) == 3:
            total_seconds = (float(parts[0]) * 3600) + (float(parts[1]) * 60) + float(parts[2])
        elif len(parts) == 2:
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

    official_drivers = []
    user_entries = []
    combined_fastest = []

    try:
        session = fastf1.get_session(season, race, "R")
        session.load(laps=True, telemetry=False, weather=False)

        winner_row = session.results.loc[session.results['Position'] == 1].iloc[0]
        winner_total_seconds = winner_row['Time'].total_seconds()
        total_laps_race = winner_row['Laps']

        for _, row in session.results.iterrows():
            status = str(row['Status'])
            laps_completed = row['Laps']
            lap_diff = int(total_laps_race - laps_completed)

            # Decide if they are truly "Lapped" or just finished with a time gap
            # If Time is null but they are still "Finished", they are lapped
            if pd.isnull(row['Time']) or lap_diff > 0:
                total_sec = float('inf')
                # Overwrite generic "Lapped" with the specific count
                if "Lap" in status or status == "Finished":
                    status = f"+{lap_diff} {'Lap' if lap_diff == 1 else 'Laps'}"
            else:
                total_sec = winner_total_seconds if row['Position'] == 1 else winner_total_seconds + row[
                    'Time'].total_seconds()

            official_drivers.append({
                "isUser": False,
                "SortKey": total_sec,
                "Abbreviation": row['Abbreviation'],
                "TeamName": row['TeamName'],
                "Status": status
            })

        laps = session.laps.dropna(subset=["LapTime"])
        last_laps = laps.groupby("Driver").tail(1)
        for row in last_laps.itertuples():
            team_search = session.results.loc[session.results["Abbreviation"] == row.Driver, "TeamName"]
            team = team_search.values[0] if not team_search.empty else "Unknown"
            combined_fastest.append({
                "id": None,
                "Abbreviation": row.Driver,
                "TeamName": team,
                "Seconds": row.LapTime.total_seconds()
            })
    except Exception as e:
        print(f"F1 Error: {e}")

    try:
        conn = sqlite3.connect('f1_custom.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, team, lap_time_seconds FROM custom_results WHERE season=? AND race LIKE ?",
                       (season, f"%{race}%"))
        for row in cursor.fetchall():
            user_entries.append({
                "id": row[0],
                "isUser": True,
                "SortKey": row[3],
                "Abbreviation": f"{row[1]} (YOU)",
                "TeamName": row[2],
                "Status": "Finished"
            })
            combined_fastest.append({
                "id": row[0], "Abbreviation": f"{row[1]} (YOU)", "TeamName": row[2], "Seconds": row[3]
            })
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

    user_entries.sort(key=lambda x: x['SortKey'])
    final_combined = list(official_drivers)

    for user in user_entries:
        inserted = False
        for idx, off in enumerate(final_combined):
            if user['SortKey'] < off['SortKey']:
                final_combined.insert(idx, user)
                inserted = True
                break
        if not inserted:
            dnf_idx = next((i for i, d in enumerate(final_combined) if d['SortKey'] == float('inf')),
                           len(final_combined))
            final_combined.insert(dnf_idx, user)

    final_finish_order = []
    for i, d in enumerate(final_combined):
        if d['SortKey'] == float('inf'):
            display_time = ""
            gap_str = d['Status']  # Shows "+1 Lap", "+2 Laps", or "Retired"
        else:
            display_time = format_to_f1_standard(d['SortKey'])
            if i == 0:
                gap_str = "WINNER"
            else:
                prev = final_combined[i - 1]
                if prev['SortKey'] != float('inf'):
                    diff = d['SortKey'] - prev['SortKey']
                    gap_str = f"+{diff:.3f}s"
                else:
                    gap_str = "—"

        final_finish_order.append({
            "id": d.get('id'),
            "Position": i + 1,
            "isUser": d.get('isUser', False),
            "Abbreviation": d['Abbreviation'],
            "TeamName": d['TeamName'],
            "Time": display_time,
            "Gap": gap_str
        })

    combined_fastest.sort(key=lambda x: x['Seconds'])
    best_lap = combined_fastest[0]['Seconds'] if combined_fastest else 0
    final_fastest = []
    for i, d in enumerate(combined_fastest, 1):
        gap = d['Seconds'] - best_lap
        final_fastest.append({
            "id": d.get('id'), "Position": i, "Abbreviation": d['Abbreviation'],
            "TeamName": d['TeamName'], "LapTime": format_to_f1_standard(d['Seconds']),
            "Gap": "FASTEST" if gap < 0.001 else f"+{gap:.3f}"
        })

    return jsonify({"finish_order": final_finish_order, "fastest_laps": final_fastest})


if __name__ == "__main__":
    app.run(port=5000, debug=True)