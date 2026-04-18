import sqlite3

conn = sqlite3.connect('equipment_master.db')
cursor = conn.cursor()

# Alle Tabellennamen anzeigen
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Tabellen in der DB:", cursor.fetchall())

# Spaltennamen der ersten Tabelle anzeigen
cursor.execute("PRAGMA table_info(equipment);") # Falls die Tabelle 'equipment' heißt
print("Spalten in der Tabelle:", cursor.fetchall())
conn.close()
