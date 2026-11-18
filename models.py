import json
import os
from datetime import date, timedelta


class Meal:
    def __init__(self, meal_id, title, day, calories, protein, carbs, fat):
        self.id = meal_id
        self.title = title
        self.day = day
        self.calories = calories
        self.protein = protein
        self.carbs = carbs
        self.fat = fat

    def __repr__(self):
        return f"Meal({self.id}, {self.title!r})"

    def label(self):
        return f"P {self.protein}g / C {self.carbs}g / F {self.fat}g"

    def to_dict(self):
        return {"id": self.id, "title": self.title, "date": self.day.isoformat(),
                "calories": self.calories, "protein": self.protein,
                "carbs": self.carbs, "fat": self.fat}

    @classmethod
    def from_dict(cls, d):
        return cls(d["id"], d["title"], date.fromisoformat(d["date"]),
                   d["calories"], d["protein"], d["carbs"], d["fat"])


class Goal:

    def __init__(self, week, calories, protein):
        self.week = week
        self.calories = calories
        self.protein = protein

    def __repr__(self):
        return f"Goal({self.week}, {self.calories} cal, {self.protein}g protein)"

    def to_dict(self):
        return {"week": self.week.isoformat(), "calories": self.calories,
                "protein": self.protein}

    @classmethod
    def from_dict(cls, d):
        return cls(date.fromisoformat(d["week"]), d["calories"], d["protein"])


class Tracker:

    def __init__(self, meals_path, goals_path):
        self.meals_path = meals_path
        self.goals_path = goals_path
        self.meals = [Meal.from_dict(d) for d in self._load(meals_path)]
        self.goals = [Goal.from_dict(d) for d in self._load(goals_path)]

    def history(self, today):
        this_week = week_start(today)
        starts = [week_start(m.day) for m in self.meals]
        starts += [g.week for g in self.goals]
        week = min(starts + [this_week])
        weeks = []
        while week <= this_week:
            weeks.append(self.summary(week))
            week += timedelta(days=7)
        return list(reversed(weeks))

    def save_goal(self, week, calories, protein):
        self.goals = [g for g in self.goals if g.week != week]
        self.goals.append(Goal(week, calories, protein))
        self._save(self.goals_path, self.goals)

    def _load(self, path):
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def summary(self, week):
        meals = [m for m in self.meals if week_start(m.day) == week]
        goal = self.get_goal(week)
        totals = {"week": week, "end": week + timedelta(days=6),
                  "count": len(meals),
                  "calories": sum(m.calories for m in meals),
                  "protein": round(sum(m.protein for m in meals), 1),
                  "carbs": round(sum(m.carbs for m in meals), 1),
                  "fat": round(sum(m.fat for m in meals), 1),
                  "goal": goal, "calories_left": None, "protein_left": None}
        if goal:
            totals["calories_left"] = goal.calories - totals["calories"]
            totals["protein_left"] = round(goal.protein - totals["protein"], 1)
        return totals

    def newest_goals(self):
        return sorted(self.goals, key=lambda g: g.week, reverse=True)

    def save_meal(self, title, day, calories, protein, carbs, fat):
        meal_id = max([m.id for m in self.meals], default=0) + 1
        meal = Meal(meal_id, title, day, calories, protein, carbs, fat)
        self.meals.append(meal)
        self._save(self.meals_path, self.meals)
        return meal

    def _save(self, path, items):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([i.to_dict() for i in items], f, indent=2)
        os.replace(tmp, path)

    def newest_meals(self):
        return sorted(self.meals, key=lambda m: (m.day, m.id), reverse=True)

    def get_goal(self, week):
        earlier = [g for g in self.goals if g.week <= week]
        return max(earlier, key=lambda g: g.week) if earlier else None


def week_start(day):
    return day - timedelta(days=day.weekday())