import json
import os
import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app
from models import Tracker, week_start
from validation import validate_goal_form, validate_meal_form

TODAY = date.today()

GOOD_MEAL = {"title": "Chicken salad", "date": TODAY.isoformat(),
             "calories": "450", "protein": "35", "carbs": "20", "fat": "12.5"}


@pytest.fixture
def client(tmp_path):
    (tmp_path / "meals.json").write_text("[]")
    (tmp_path / "goals.json").write_text("[]")
    app.config["MEALS_PATH"] = str(tmp_path / "meals.json")
    app.config["GOALS_PATH"] = str(tmp_path / "goals.json")
    app.config["TESTING"] = True
    return app.test_client()


def test_home_page(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Meal Tracker" in r.data and b'name="calories"' in r.data


@pytest.mark.parametrize("data", [
    {"calories": "0", "protein": "100"},
    {"calories": "abc", "protein": "100"},
    {"calories": "2000", "protein": "-1"},
    {"calories": "2000", "protein": "1.5"},
    {},
])
def test_bad_goal_gives_400(client, data):
    r = client.post("/set-goal", data=data)
    assert r.status_code == 400 and b'class="errors"' in r.data


def test_setting_goal_twice_replaces_it(client):
    client.post("/set-goal", data={"calories": "2000", "protein": "100"})
    client.post("/set-goal", data={"calories": "1800", "protein": "120"})
    with open(app.config["GOALS_PATH"]) as f:
        goals = json.load(f)
    assert len(goals) == 1 and goals[0]["calories"] == 1800


def test_empty_post_gives_400(client):
    assert client.post("/log", data={}).status_code == 400


def test_title_is_escaped(client):
    client.post("/log", data={**GOOD_MEAL, "title": "<script>alert(1)</script>"})
    page = client.get("/meals").data
    assert b"<script>alert(1)" not in page and b"&lt;script&gt;" in page


def test_unknown_page_is_404(client):
    assert client.get("/nope").status_code == 404


def test_history_shows_past_week_with_its_own_goal(client):
    last_week = week_start(TODAY) - timedelta(days=7)
    tracker = Tracker(app.config["MEALS_PATH"], app.config["GOALS_PATH"])
    tracker.save_meal("Old pasta", last_week, 800, 20, 100, 10)
    tracker.save_goal(last_week, 1000, 50)
    tracker.save_goal(week_start(TODAY), 3000, 200)
    page = client.get("/history").data.decode()
    assert "Week of " + str(last_week) in page
    assert "200 left" in page
    assert "3000 left" in page


def test_validate_goal_form_clean_values():
    values, errors = validate_goal_form({"calories": "2000", "protein": "100"})
    assert errors == [] and values == {"calories": 2000, "protein": 100}


def test_progress_without_goal(client):
    client.post("/log", data=GOOD_MEAL)
    page = client.get("/progress").data
    assert b"450" in page and b"No goal set" in page


def test_get_on_post_routes_is_405(client):
    assert client.get("/log").status_code == 405
    assert client.get("/set-goal").status_code == 405


def test_set_goal_and_see_how_far_away(client):
    client.post("/log", data=GOOD_MEAL)
    r = client.post("/set-goal", data={"calories": "2000", "protein": "100"})
    assert r.status_code == 302
    page = client.get("/progress").data
    assert b"1550 left" in page and b"65.0 left" in page


def test_week_starts_on_monday():
    assert week_start(date(2026, 11, 16)) == date(2026, 11, 16)
    assert week_start(date(2026, 11, 22)) == date(2026, 11, 16)
    assert week_start(date(2026, 11, 23)) == date(2026, 11, 23)


def test_meal_ids_increase(client):
    client.post("/log", data=GOOD_MEAL)
    client.post("/log", data=GOOD_MEAL)
    with open(app.config["MEALS_PATH"]) as f:
        assert [m["id"] for m in json.load(f)] == [1, 2]


def test_log_meal_saves_json_and_redirects_to_progress(client):
    r = client.post("/log", data=GOOD_MEAL)
    assert r.status_code == 302 and r.headers["Location"].endswith("/progress")
    with open(app.config["MEALS_PATH"]) as f:
        saved = json.load(f)
    assert len(saved) == 1 and saved[0]["title"] == "Chicken salad"
    assert saved[0]["calories"] == 450 and saved[0]["fat"] == 12.5
    page = client.get("/meals").data
    assert b"Chicken salad" in page


def test_over_goal_says_over(client):
    client.post("/log", data={**GOOD_MEAL, "calories": "2500"})
    client.post("/set-goal", data={"calories": "2000", "protein": "10"})
    page = client.get("/progress").data
    assert b"500 over" in page and b"25.0 over" in page


def test_goal_carries_forward_to_later_weeks(tmp_path):
    tracker = Tracker(str(tmp_path / "m.json"), str(tmp_path / "g.json"))
    start = week_start(TODAY) - timedelta(days=14)
    tracker.save_goal(start, 2000, 100)
    assert tracker.get_goal(start - timedelta(days=7)) is None
    assert tracker.get_goal(start + timedelta(days=7)).calories == 2000
    tracker.save_goal(start + timedelta(days=7), 1800, 100)
    assert tracker.get_goal(start + timedelta(days=14)).calories == 1800


def test_validate_meal_form_clean_values():
    values, errors = validate_meal_form(GOOD_MEAL, TODAY)
    assert errors == [] and values["calories"] == 450 and values["fat"] == 12.5
    assert values["day"] == TODAY


@pytest.mark.parametrize("change", [
    {"title": ""},
    {"title": "x" * 61},
    {"date": "not a date"},
    {"date": (TODAY + timedelta(days=1)).isoformat()},
    {"date": (TODAY - timedelta(days=400)).isoformat()},
    {"calories": "abc"},
    {"calories": "12.5"},
    {"calories": "-5"},
    {"calories": "99999"},
    {"protein": "nan"},
    {"carbs": "inf"},
    {"fat": ""},
])
def test_bad_meal_gives_400_and_saves_nothing(client, change):
    r = client.post("/log", data={**GOOD_MEAL, **change})
    assert r.status_code == 400
    assert b'class="errors"' in r.data
    with open(app.config["MEALS_PATH"]) as f:
        assert json.load(f) == []


def test_data_survives_a_new_tracker(tmp_path):
    tracker = Tracker(str(tmp_path / "m.json"), str(tmp_path / "g.json"))
    tracker.save_meal("Oats", TODAY, 300, 10, 50, 5)
    tracker.save_goal(week_start(TODAY), 2000, 100)
    again = Tracker(str(tmp_path / "m.json"), str(tmp_path / "g.json"))
    assert again.meals[0].title == "Oats" and again.goals[0].calories == 2000