#created by Jacob Miller on 11/21
import csv
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "data", "menu.db")
CSV_PATH = os.path.join(BASE, "data", "menu.csv") #added by Darwin Sanchez on 11/23

#function to create / return a database folder
def get_connection():
    connection = sqlite3.connect(DB_PATH) #opens / creates a database file
    connection.row_factory = sqlite3.Row #makes each row accessible by column name
    return connection

#function to initialize the database
def init_menu_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) #creates a new database file
    with get_connection() as connection: #opens a connection and commits the changes in the loop
        connection.execute("""CREATE TABLE IF NOT EXISTS menu_item (
                id INTEGER PRIMARY KEY, 
                restaurant TEXT NOT NULL,
                name TEXT NOT NULL,
                calories INTEGER NOT NULL,
                protein REAL NOT NULL,
                carbs REAL NOT NULL,
                fat REAL NOT NULL,
                allergens TEXT DEFAULT '',
                UNIQUE (restaurant, name)
             )
        """) #gives each meal a primary key and some attributes; also prevents duplicate items
    # added by Darwin Sanchez on 11/23 import_csv was never called so the menu table stayed empty
        if os.path.exists(CSV_PATH):
             import_csv(CSV_PATH)
#opens the csv file and database together
def import_csv(path):
    with open(path, newline="", encoding ="utf-8") as csvfile, get_connection() as connection:
        for line, r in enumerate(csv.DictReader(csvfile),start=2):  # changed by Darwin Sanchez on 11/23

            try:
                values = (r["restaurant"], r["name"], int(r["calories"]),
                          float(r["protein"]), float(r["carbs"]), float(r["fat"]),#convert necessary items from text to numbers
                          ",".join(a.strip() for a in (r.get("allergens") or "").lower().split(",") if a.strip()))
            except (KeyError, ValueError, TypeError):
                print(f"menu.csv line {line} skipped: {r}")
                continue
            #execute an SQL command (?s as placeholders / prevent SQL injection)
            #add new items into menu.db, handles existing items
            connection.execute("""
                INSERT INTO menu_item
                    (restaurant, name, calories, protein, carbs, fat, allergens)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(restaurant, name) DO UPDATE SET
                    calories=excluded.calories, protein=excluded.protein,
                    carbs=excluded.carbs, fat=excluded.fat,
                    allergens=excluded.allergens
                       """, values) #changed by Darwin Sanchez on 11/23

#function to sort / return a list of restaurants
def restaurants():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT DISTINCT restaurant FROM menu_item ORDER BY restaurant")
        return [r["restaurant"] for r in rows]

#function to search for a menu item
def search_items(restaurant="", max_calories=None, min_protein=None, avoid = (), text=""):
    sql, params = "SELECT * FROM menu_item WHERE 1=1", []  # fixed by Darwin Sanchez on 11/23 SELECT ROW is not a column
    if restaurant:
        sql += " AND restaurant = ?";
        params.append(restaurant)
    if max_calories is not None: #adds an upper limit to the number of calories
        sql += " AND calories <= ?";
        params.append(max_calories)
    if min_protein is not None: #adds a lower limit to protein
        sql += " AND protein >= ?";
        params.append(min_protein)
    if text: #changed by Darwin on 11 / 23 a % and a _ are now treated as text
        escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        sql += " AND name LIKE ? ESCAPE '\\'";
        params.append(f"%{escaped}%")
    for a in avoid: #excludes the commas separating the list of allergens
        sql += " AND (',' || allergens || ',') NOT LIKE ?"
        params.append(f"%,{a},%") #makes it so a word that's a part of another word is excluded exclusively
    sql += " ORDER BY restaurant, name"
    with get_connection() as connection:
        return connection.execute(sql, params).fetchall() #executes the SQL query