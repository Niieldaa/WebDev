import fastf1
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

@app.route("/Shedule")
def schedule_page():
    return render_template("Shedule.html")


@app.route("/f1-schedule")
def schedule_data():
    season = request.args.get("season", default=2023, type=int)

    schedule = fastf1.get_event_schedule(season)

    data = []
    for _, row in schedule.iterrows():
        data.append({
            "round": int(row["RoundNumber"]),
            "name": row["EventName"],
            "country": row["Country"],
            "date": str(row["EventDate"])
        })

    return jsonify(data)


if __name__ == "__main__":
    app.run(port=5000, debug=True)