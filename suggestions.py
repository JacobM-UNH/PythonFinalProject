#created by Jacob Miller on 11/22
from datetime import timedelta

from menu_db import search_items

MEALS_PER_DAY = 3

def meals_left(today, week):
    days_left = (week + timedelta(days=6)- today).days + 1
    return max(days_left, 1) * MEALS_PER_DAY

def per_meal_target(summary, today):
    if summary["goal"] is None:
        return None
    n = meals_left(today, summary["goal"])
    calories = max(summary["calories_left"], 0) / n
    protein = max(summary["protein_left"], 0) / n
    return round(calories), round(protein, 1)

def suggest(summary, today, avoid =(), limit = 5):
    target = per_meal_target(summary, today)
    if target is None:
        return None, []
    cal_target, protein_target = target

    items = search_items(max_calories=int(cal_target * 1.25), avoid=avoid)

    def score(item):
        cal_gap = abs(item["calories_left"] - cal_target) / max(cal_target, 1)
        protein_gap = max(protein_target - item[:protein_target], 0) / max(protein_target, 1)
        return cal_gap + protein_gap

    return target, sorted(items, key = score, reverse = True)[:limit]