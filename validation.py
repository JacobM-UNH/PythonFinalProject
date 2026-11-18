from datetime import datetime, timedelta


def _read_number(form, name, label, low, high, whole, errors):
    text = form.get(name, "").strip()
    try:
        value = int(text) if whole else round(float(text), 1)
    except ValueError:
        kind = "a whole number" if whole else "a number"
        errors.append(f"{label} must be {kind}.")
        return None
    if not low <= value <= high:
        errors.append(f"{label} must be between {low} and {high}.")
    return value


def validate_meal_form(form, today):
    errors = []

    title = form.get("title", "").strip()
    if not 1 <= len(title) <= 60:
        errors.append("Meal title must be 1 to 60 characters.")

    try:
        day = datetime.strptime(form.get("date", ""), "%Y-%m-%d").date()
        if day > today:
            errors.append("Date cannot be in the future.")
        elif day < today - timedelta(days=365):
            errors.append("Date cannot be more than a year ago.")
    except ValueError:
        day = None
        errors.append("Date must look like 2026-11-16.")

    calories = _read_number(form, "calories", "Calories", 0, 5000, True, errors)
    protein = _read_number(form, "protein", "Protein (g)", 0, 500, False, errors)
    carbs = _read_number(form, "carbs", "Carbs (g)", 0, 1000, False, errors)
    fat = _read_number(form, "fat", "Fat (g)", 0, 500, False, errors)

    return {"title": title, "day": day, "calories": calories,
            "protein": protein, "carbs": carbs, "fat": fat}, errors


def validate_goal_form(form):
    errors = []
    calories = _read_number(form, "calories", "Weekly calories", 1, 50000, True, errors)
    protein = _read_number(form, "protein", "Weekly protein (g)", 0, 5000, True, errors)
    return {"calories": calories, "protein": protein}, errors