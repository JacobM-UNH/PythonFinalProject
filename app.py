import os
from datetime import date

from flask import Flask, redirect, render_template, request, url_for

from models import Tracker, week_start
from validation import validate_goal_form, validate_meal_form

from menu_db import init_menu_db, restaurants, search_items

init_menu_db()

BASE = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["MEALS_PATH"] = os.path.join(BASE, "data", "meals.json")
app.config["GOALS_PATH"] = os.path.join(BASE, "data", "goals.json")


def get_tracker():
    return Tracker(app.config["MEALS_PATH"], app.config["GOALS_PATH"])

#changed by Jacob Miller on 11/21
@app.route("/")
def index():
    return render_template("index.html", errors=[], values = request.args,
                           today=date.today().isoformat()) #added request.args to links can prefill the form

#added by Jacob Miller on 11/21
def _num(name, cast):
    try:
        return cast(request.args.get(name, ""))
    except ValueError:
        return None

@app.route("/menu")
def menu():
    avoid = [a.strip().lower() for a in request.args.get("avoid", "").split(",")
             if a.strip()]
    items = search_items(
        restaurant=request.args.get("restaurant", ""),
        max_calories=_num("max_calories", int),
        min_protein=_num("min_protein", float),
        avoid=avoid,
        text=request.args.get("q", "").strip(),
    )
    return render_template("menu.html", items=items,
                           restaurants=restaurants(), args=request.args)


@app.route("/log", methods=["POST"])
def log():
    values, errors = validate_meal_form(request.form, date.today())
    if errors:
        return render_template("index.html", errors=errors, values=request.form,
                               today=date.today().isoformat()), 400
    get_tracker().save_meal(**values)
    return redirect(url_for("progress"))


@app.route("/history")
def history():
    return render_template("history.html",
                           weeks=get_tracker().history(date.today()))


@app.route("/progress")
def progress():
    summary = get_tracker().summary(week_start(date.today()))
    return render_template("progress.html", summary=summary)


@app.route("/goal")
def goal():
    tracker = get_tracker()
    current = tracker.get_goal(week_start(date.today()))
    return render_template("goal.html", errors=[], values={}, current=current,
                           goals=tracker.newest_goals())


@app.route("/meals")
def meals():
    return render_template("meals.html", meals=get_tracker().newest_meals())


@app.route("/set-goal", methods=["POST"])
def set_goal():
    tracker = get_tracker()
    values, errors = validate_goal_form(request.form)
    if errors:
        current = tracker.get_goal(week_start(date.today()))
        return render_template("goal.html", errors=errors, values=request.form,
                               current=current,
                               goals=tracker.newest_goals()), 400
    tracker.save_goal(week_start(date.today()), values["calories"],
                      values["protein"])
    return redirect(url_for("progress"))


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)