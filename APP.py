from flask import Flask, render_template

app = Flask(__name__)

from Schedule import schedule_bp
from f1Data import data_bp

app.register_blueprint(schedule_bp, url_prefix="/schedule")
app.register_blueprint(data_bp, url_prefix="/data")


@app.route("/homepage")
def home():
    return render_template("homePage.html")

@app.route("/drivers")
def about():
    return render_template("Drivers.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)