from flask import Flask, render_template

from Service.Schedule import schedule_bp
from Service.f1Data import data_bp

app = Flask(__name__)

app.register_blueprint(schedule_bp, url_prefix="/api")
app.register_blueprint(data_bp, url_prefix="/api/data")

@app.route("/")
@app.route("/homepage")
def home():
    return render_template("homePage.html")


@app.route("/schedule")
def schedule_page():
    return render_template("Schedule.html")


@app.route("/drivers")
def drivers():
    return render_template("Drivers.html")

if __name__ == "__main__":
    app.run(debug=True, port=5000)