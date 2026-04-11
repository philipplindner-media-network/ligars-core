import sqlite3
import os
import json
import time
from datetime import datetime

# --- DATENBANK KONFIGURATION ---

def get_db():
    """Stellt die Verbindung zur zentralen Datenbank her."""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialisiert die Datenbankstruktur und führt notwendige Migrationen durch."""
    # Ordnerstruktur sicherstellen
    if not os.path.exists('uploads'): os.makedirs('uploads')
    if not os.path.exists('core'): os.makedirs('core')
    if not os.path.exists('backups'): os.makedirs('backups')

    with get_db() as conn:
        # 1. Tabelle: Einträge (Biometrische Daten & Körpermaße)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS eintraege (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datum TEXT,
                taille REAL,
                brust REAL,
                hals REAL,
                notizen TEXT,
                datei TEXT
            )""")

        # 2. Tabelle: Settings (System-Konfiguration)
        conn.execute("CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, wert TEXT)")

        # 3. Tabelle: Einkäufe (Logistik & Equipment)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS einkaeufe (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT,
                link TEXT,
                preis TEXT,
                phase TEXT,
                status INTEGER DEFAULT 0
            )""")

        # 4. Tabelle: Aktive Missionen (Überwachung & Befehle)
        # HINWEIS: mail_gesendet trackt, ob die Sanktions-Mail bereits raus ist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS aktive_missionen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                befehl_text TEXT,
                equipment_genutzt TEXT,
                status TEXT DEFAULT 'AKTIV',
                start_zeit TEXT,
                ablauf_zeit TEXT,
                mail_gesendet INTEGER DEFAULT 0
            )""")

        # 5. Tabelle: Tagespläne (Stundenplan-Daten)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tagesplaene (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                woche INTEGER,
                tag_nr INTEGER,
                plan_inhalt TEXT
            )""")

        # --- AUTOMATISCHE MIGRATION (Spalten-Check) ---

        # Check für 'eintraege'
        cursor = conn.execute("PRAGMA table_info(eintraege)")
        cols = [row['name'] for row in cursor.fetchall()]
        for c in ["brust", "hals", "datei"]:
            if c not in cols:
                conn.execute(f"ALTER TABLE eintraege ADD COLUMN {c} TEXT")
                print(f">>> DB_UPDATE: Spalte '{c}' in 'eintraege' nachgerüstet.")

        # Check für 'einkaeufe'
        cursor = conn.execute("PRAGMA table_info(einkaeufe)")
        einkauf_cols = [row['name'] for row in cursor.fetchall()]
        for c in ["phase", "preis"]:
            if c not in einkauf_cols:
                conn.execute(f"ALTER TABLE einkaeufe ADD COLUMN {c} TEXT")
                print(f">>> DB_UPDATE: Spalte '{c}' in 'einkaeufe' nachgerüstet.")

        # Check für 'aktive_missionen' (Wichtig für Mail-System)
        cursor = conn.execute("PRAGMA table_info(aktive_missionen)")
        mission_cols = [row['name'] for row in cursor.fetchall()]

        # Die neue Spalte für den Mail-Status
        if "mail_gesendet" not in mission_cols:
            conn.execute("ALTER TABLE aktive_missionen ADD COLUMN mail_gesendet INTEGER DEFAULT 0")
            print(">>> DB_MIGRATION: Spalte 'mail_gesendet' erfolgreich nachgerüstet.")

        conn.commit()

    print(">>> LIGARS_DB_MANAGER: System-Check abgeschlossen. database.db ist bereit.")

if __name__ == "__main__":
    # Falls man die Datei direkt ausführt, wird die DB initialisiert
    init_db()
