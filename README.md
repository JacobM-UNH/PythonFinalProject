In order to populate a database with the information in the menu.csv, run the following command in the project's terminal: 
python -c "from menu_db import init_menu_db, import_csv; init_menu_db(); import_csv('data/menu.csv')"
