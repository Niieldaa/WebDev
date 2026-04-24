import os
import fastf1
from flask import Flask, jsonify, render_template, request
import pandas as pd

app = Flask(__name__)

# Setup caching
os.makedirs("cache", exist_ok=True)
fastf1.Cache.enable_cache("cache")
fastf1.set_log_level("INFO")


def clean_time_str(td):
    """Formats Timedelta to MM:SS.ms"""
    if pd.isna(td): return "N/A"
    ts = str(td).split()[-1]
    if ts.startswith("00:"):
        return ts[3:-3]
    return ts[:-3]


@app.route("/results")
def results():
    season = request.args.get("season", default=2026, type=int)
    race = request.args.get("race", type=str)

    if not race:
        return jsonify({"error": "Race name is required"})

    try:
        session = fastf1.get_session(season, race, "R")
        session.load()

        # 1. --- RACE TABLE (Removed Gap) ---
        laps = session.laps.dropna(subset=["LapTime"])
        last_laps = (
            laps.sort_values("LapNumber")
            .groupby("Driver")
            .tail(1)[["Driver", "LapTime"]]
        )

        race_list = []
        for _, row in session.results.iterrows():
            driver_abb = row["Abbreviation"]
            driver_lap_row = last_laps.loc[last_laps["Driver"] == driver_abb, "LapTime"]

            # Use the actual last lap time, or the status if they retired
            lap_display = clean_time_str(driver_lap_row.iloc[0]) if not driver_lap_row.empty else row["Status"]

            race_list.append({
                "Position": int(row["Position"]),
                "Abbreviation": driver_abb,
                "TeamName": row["TeamName"],
                "LapTime": lap_display,
                "LastLapGap": ""  # Sending empty string to remove gap from the first table
            })

        # 2. --- FASTEST LAP TABLE (Keeping Gap for ranking) ---
        fastest_df = laps.groupby("Driver")["LapTime"].min().reset_index().sort_values("LapTime")
        best_overall = fastest_df["LapTime"].min()

        fastest_list = []
        for i, row in enumerate(fastest_df.itertuples(), 1):
            f_delta = (row.LapTime - best_overall).total_seconds()
            team = session.results.loc[session.results["Abbreviation"] == row.Driver, "TeamName"].values[0]

            fastest_list.append({
                "Position": i,
                "Abbreviation": row.Driver,
                "TeamName": team,
                "FastestLap": clean_time_str(row.LapTime),
                "FastestLapGap": "FASTEST" if f_delta < 0.0001 else f"+{f_delta:.3f}"
            })

        return jsonify({"race": race_list, "fastest": fastest_list})

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(port=5000, debug=True)