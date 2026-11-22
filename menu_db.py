#created by Jacob Miller on 11/21
import csv
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "data", "menu.db")

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

#opens the csv file and database together
def import_csv(path):
    with open(path, newline="", encoding ="utf-8") as csvfile, get_connection() as connection:
        for r in csv.DictReader(csvfile): #read each row as a dictionary (key = name)
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
            """, (r["restaurant"], r["name"], int(r["calories"]),
                  float(r["protein"]), float(r["carbs"]), float(r["fat"]),#convert necessary items from text to numbers
                  r.get("allergens", "").strip().lower())) #remove spaces / force lowercase on the allergen list

#function to sort / return a list of restaurants
def restaurants():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT DISTINCT restaurant FROM menu_item ORDER BY restaurant")
        return [r["restaurant"] for r in rows]

#function to search for a menu item
def search_items(restaurant="", max_calories=None, min_protein=None, avoid = (), text=""):
    sql, params = "SELECT ROW FROM menu_item WHERE 1=1", []
    if restaurant:
        sql += " AND restaurant = ?";
        params.append(restaurant)
    if max_calories is not None: #adds an upper limit to the number of calories
        sql += " AND calories <= ?";
        params.append(max_calories)
    if min_protein is not None: #adds a lower limit to protein
        sql += " AND protein >= ?";
        params.append(min_protein)
    if text:
        sql += " AND name LIKE ?";
        params.append(f"%{text}%")
    for a in avoid: #excludes the commas separating the list of allergens
        sql += " AND (',' || allergens || ',') NOT LIKE ?"
        params.append(f"%,{a},%") #makes it so a word that's a part of another word is excluded exclusively
    sql += " ORDER BY restaurant, name"
    with get_connection() as connection:
        return connection.execute(sql, params).fetchall() #executes the SQL query