from flask import Blueprint, jsonify, render_template
import fastf1
import datetime

schedule_bp = Blueprint("schedule", __name__)


COUNTRY_CODES = {
    "Bahrain": "bh",
    "Saudi Arabia": "sa",
    "Australia": "au",
    "Japan": "jp",
    "China": "cn",
    "United States": "us",
    "United Kingdom": "gb",
    "Italy": "it",
    "Monaco": "mc",
    "Spain": "es",
    "Austria": "at",
    "Hungary": "hu",
    "Belgium": "be",
    "Netherlands": "nl",
    "Singapore": "sg",
    "Mexico": "mx",
    "Brazil": "br",
    "Qatar": "qa",
    "Abu Dhabi": "ae"
}


@schedule_bp.route("/")
def home():
    return render_template("/Schedule.html")


def get_schedule(year=None):
    if year is None:
        year = datetime.datetime.now().year

    schedule_df = fastf1.get_event_schedule(year)

    schedule = []

    for _, row in schedule_df.iterrows():
        schedule.append({
            "round": int(row["RoundNumber"]),
            "name": row["EventName"],
            "country": row["Country"],
            "country_code": COUNTRY_CODES.get(row["Country"], "un"),
            "location": row["Location"],
            "date": row["EventDate"].strftime("%Y-%m-%d")
        })

    return schedule


@schedule_bp.route("/api/schedule")
def schedule_api():
    return jsonify(get_schedule())


@schedule_bp.route("/race/<int:round_number>")
def race_details(round_number):
    schedule = get_schedule()
    race = next((r for r in schedule if r["round"] == round_number), None)

    if not race:
        return "Race not found", 404

    return render_template("RaceDetails.html", race=race)