import os, sqlite3, time, json, requests, smtplib, sys, datetime, zipfile, io
from flask import Flask, render_template, request, redirect, url_for, session, abort, send_from_directory
from werkzeug.utils import secure_filename
import google.generativeai as genai
from cryptography.fernet import Fernet
from datetime import date
import socket
import hashlib
from database_manager import get_db, init_db
from logger_system import LigarsLogger
from mainframe_sync import sync_stats_to_mainframe
import datetime
from datetime import datetime, date, timedelta
from email.utils import formatdate, make_msgid
import qrcode
import io
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import signal
import shutil
import threading
import uuid
import platform
import sys
import requests

# --- 1. DEINE IMPORTIERTEN MODULE ---
from mainframe_sync import sync_stats_to_mainframe
from database_manager import get_db, init_db
from logger_system import LigarsLogger
from ai_handler import generate_ai_content

# --- 2. HILFSFUNKTIONEN ---
def get_decrypted_password():
    # FEST HINTERLEGTER SCHLÜSSEL (Keine Umgebungsvariable mehr nötig)
    key = "G7cGxyUt7iaqtz_PRTurZGv3w0KDO83KET5mxfMcSPs="

    try:
        cipher_suite = Fernet(key.encode())

        # Config laden
        with open('config.json', 'r') as f:
            conf = json.load(f)

        # SMTP_PASS_ENCRYPTED in der config.json muss existieren
        encrypted_pass = conf['SMTP_PASS'].encode() # Ich habe hier 'SMTP_PASS' gewählt
        return conf, cipher_suite.decrypt(encrypted_pass).decode()

    except Exception as e:
        print(f"KRITISCH: Fehler beim Entschlüsseln: {e}")
        return None, None

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def load_config():
    path = 'config.json'
    defaults = {"WEB_PASSWORD": "Sissy2026", "SMTP_PORT": 587, "GEMINI_API_KEY": ""}
    
    if os.path.exists(path):
        try:
            # WICHTIG: encoding='utf-8' hinzugefügt
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    print("ERR: config.json ist leer!")
                    return defaults
                
                loaded_config = json.loads(content)
                # Zusammenführen der Defaults mit der geladenen Datei
                config = {**defaults, **loaded_config}
                
                # Globales genai-Objekt konfigurieren, falls Key vorhanden
                if config.get("GEMINI_API_KEY"):
                    genai.configure(api_key=config["GEMINI_API_KEY"])
                    
                return config
        except Exception as e:
            # Gibt jetzt den genauen Fehler aus (z.B. JSON-Syntaxfehler)
            print(f"ERR: config.json konnte nicht gelesen werden! Details: {e}")
    
    return defaults

# --- 3. INITIALISIERUNG (REIHENFOLGE WICHTIG!) ---
CONF = load_config()
CURRENT_VERSION = "2.5.5"
UPDATE_URL = "https://ligars.any64.de/api/version.php"
SECRET_KEY = b'gPLIpSmeSmXEJ1mZIjSaSv-icwrlVAX2QwFSCwlxt8c='

# ZUERST APP DEFINIEREN:
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB
app.secret_key = 'ligars_ultimate_key_2026'
app.config['UPLOAD_FOLDER'] = 'uploads'

#

# KI INITIALISIEREN
if CONF.get('GEMINI_API_KEY'):
    genai.configure(api_key=CONF['GEMINI_API_KEY'])

def check_for_updates():
    def v_to_int(v):
        try: return int(str(v).replace(".", ""))
        except: return 0

    LigarsLogger.log("SYS", f"LIGARS_CORE v{CURRENT_VERSION} prüft auf Updates...")

    try:
        res = requests.get(UPDATE_URL, timeout=5)
        if res.status_code == 200:
            data = res.json()
            remote_version = data.get("version")
            expected_hash = data.get("update_sha256")

            if remote_version and v_to_int(remote_version) > v_to_int(CURRENT_VERSION):
                LigarsLogger.log("SYS", f"NEUE VERSION GEFUNDEN: v{remote_version}")

                # 1. SICHERUNG: Config in den Arbeitsspeicher laden
                config_backup = None
                if os.path.exists("config.json"):
                    with open("config.json", "r") as f:
                        config_backup = f.read()
                    LigarsLogger.log("SYS", "Konfiguration wurde zwischengespeichert.")

                # Download
                u_res = requests.get(data.get("download_url"), timeout=15)
                actual_hash = hashlib.sha256(u_res.content).hexdigest()

                if actual_hash != expected_hash:
                    LigarsLogger.log("ERR", "SICHERHEITS-ALARM!", "Hash-Mismatch!")
                    return False

                # 2. ENTPACKEN
                LigarsLogger.log("SYS", "Entpacke Update-Paket...")
                with zipfile.ZipFile(io.BytesIO(u_res.content)) as z:
                    z.extractall(".")

                # 3. WIEDERHERSTELLUNG: Config aus dem Speicher zurückschreiben
                if config_backup:
                    with open("config.json", "w") as f:
                        f.write(config_backup)
                    LigarsLogger.log("SYS", "Konfiguration erfolgreich wiederhergestellt.")

                LigarsLogger.log("SYS", "Update fertig. Kern-Neustart eingeleitet...")

                if platform.system() == "Windows":
                     # Unter Windows: Starte einen neuen Prozess und beende den alten sofort
                     import subprocess
                     subprocess.Popen([sys.executable] + sys.argv, creationflags=subprocess.CREATE_NEW_CONSOLE)
                     os._exit(0) 
                else:
                    # Unter Linux (Ubuntu): Der alte Weg ist hier weiterhin perfekt
                    os.execv(sys.executable, ['python'] + sys.argv)
            else:
                LigarsLogger.log("SYS", "Keine Updates erforderlich.")
        else:
            LigarsLogger.log("ERR", "Update-Server nicht erreichbar")

    except Exception as e:
        LigarsLogger.log("ERR", "Update-Routine abgebrochen", str(e))


# In der index() Funktion ergänzen:
local_ip = get_local_ip()
qr_url = f"http://{local_ip}:8000" # Oder dein Port

def generate_48_weeks_masterplan(plan_name, vault_config, system, start_typ, pool, model):
    """
    ERZEUGT EINEN HOCHPRÄZISEN 48-WOCHEN-PLAN IN BLÖCKEN.
    Verhindert Timeouts und Token-Limits durch 4x12 Wochen Generierung.
    """
    conn = get_db()

    # 1. DATENBANK-BEREINIGUNG & INITIALISIERUNG
    conn.execute("DROP TABLE IF EXISTS wochenplan")
    conn.execute("DROP TABLE IF EXISTS tagesplaene")
    conn.execute("""
        CREATE TABLE wochenplan (
            woche INTEGER PRIMARY KEY,
            aufgabe TEXT,
            equipment_event TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE tagesplaene (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            woche INTEGER,
            tag_nr INTEGER,
            plan_inhalt TEXT
        )
    """)

    # 2. KONFIGURATION LADEN
    settings_raw = conn.execute("SELECT name, wert FROM settings").fetchall()
    settings = {row['name']: row['wert'] for row in settings_raw}
    proband_name = settings.get('proband_name', 'Subjekt')
    schicht_zeiten = settings.get('schicht_zeiten', '{}')

    v_beschreibung = vault_config.get('beschreibung', 'Keine Beschreibung.')
    v_system_prompt = vault_config.get('system_prompt', 'Du bist LIGARS. Handle autoritär.')
    v_task_prompt = vault_config.get('task_prompt', 'Generiere tägliche Disziplin-Anweisungen.')
    items_str = ", ".join([i['name'] for i in vault_config.get('shopping_list', [])])

    rotation_logic = ""
    if system == "WEEKLY_2":
        rotation_logic = f"2-Wochen-Wechsel. Start: {start_typ}. Dann A/B Wechsel im Pool {pool}."
    elif system == "WEEKLY_3":
        rotation_logic = f"3-Wochen-Wechsel. Start: {start_typ}. Rollierend im Pool {pool}."
    elif system == "ROLLING_4_2":
        rotation_logic = "4 Tage Dienst, 2 Tage frei. Kontinuierliche Verschiebung."
    else:
        rotation_logic = f"Statisch: Jede Woche {start_typ}."

    # 3. GENERIERUNG IN 4 BLÖCKEN (Stabilität!)
    for block in range(4):
        start_w = (block * 12) + 1
        end_w = (block + 1) * 12

        LigarsLogger.log("AI", f"Generiere Block {block+1}/4 (Wochen {start_w}-{end_w})...")

        prompt = f"""
        {v_system_prompt}
        PROTOKOLL: {plan_name} | SUBJEKT: {proband_name}

        ### AUFTRAG:
        Generiere JETZT EXAKT die Wochen {start_w} bis {end_w}.

        ### VORGABEN:
        - Kern: {v_beschreibung}
        - Stil: {v_task_prompt}
        - Schicht-System: {rotation_logic}
        - Dienstzeiten: {schicht_zeiten}
        - Equipment: {items_str}

        ### FORMAT (NUR REINES JSON):
        [
          {{
            "woche": {start_w},
            "aufgabe": "Fokus-Text + Schicht-Info",
            "event": "Equipment-Event",
            "tage": {{ "1": "...", "2": "...", "3": "...", "4": "...", "5": "...", "6": "...", "7": "..." }}
          }}
        ]
        """

        try:
            response = model.generate_content(prompt)
            raw_json = response.text.strip()

            # Markdown-Säuberung (Sicherer)
            if "```json" in raw_json:
                raw_json = raw_json.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_json:
                raw_json = raw_json.split("```")[1].split("```")[0].strip()

            plan_data = json.loads(raw_json)

            # IN DATENBANK SPEICHERN
            for w in plan_data:
                conn.execute(
                    "INSERT INTO wochenplan (woche, aufgabe, equipment_event) VALUES (?, ?, ?)",
                    (w['woche'], w['aufgabe'], w['event'])
                )
                for tag_key, inhalt in w['tage'].items():
                    t_str = str(tag_key)
                    if "-" in t_str:
                        s, e = map(int, t_str.split("-"))
                        for t in range(s, e + 1):
                            conn.execute("INSERT INTO tagesplaene (woche, tag_nr, plan_inhalt) VALUES (?, ?, ?)",
                                         (w['woche'], t, inhalt))
                    else:
                        conn.execute("INSERT INTO tagesplaene (woche, tag_nr, plan_inhalt) VALUES (?, ?, ?)",
                                     (w['woche'], int(t_str), inhalt))

            conn.commit()
            # Kurze Pause, um die API-Rate-Limits nicht zu sprengen
            time.sleep(2)

        except Exception as e:
            LigarsLogger.log("ERR", f"Block {block+1} fehlgeschlagen", str(e))
            # Optional: Hier könnte man einen "Retry" einbauen
            continue

    LigarsLogger.log("SYS", "Gesamtes 48-Wochen-Protokoll versiegelt.")
    return True

def sync_vault():
    """
    Synchronisiert den verschlüsselten Tresor (vault.enc) mit dem Zentralserver.
    Prüft die Integrität via SHA256.
    """
    LigarsLogger.log("SYS", "Synchronisiere LIGARS_VAULT mit Zentrale...")

    try:
        # 1. Metadaten (Hashes) vom Server holen
        # Nutzt die UPDATE_URL, die wir auch für System-Updates verwenden
        meta_res = requests.get(UPDATE_URL, timeout=5)
        if meta_res.status_code != 200:
            LigarsLogger.log("ERR", "Vault-Sync fehlgeschlagen", f"HTTP {meta_res.status_code}")
            return False

        meta = meta_res.json()
        expected_vault_hash = meta['vault_info']['sha256']
        vault_url = meta['vault_info']['vault_url']

        # 2. Vault herunterladen
        res = requests.get(vault_url, timeout=10) # 10s für größere Dateien
        if res.status_code == 200:
            actual_vault_hash = hashlib.sha256(res.content).hexdigest()

            # INTEGRITÄTS-CHECK (Fingerabdruck-Vergleich)
            if actual_vault_hash != expected_vault_hash:
                LigarsLogger.log("ERR", "VAULT_INTEGRITY_FAILURE!", "Hash-Mismatch bei Vault-Datei!")
                return False

            # 3. Speichern im Core-Verzeichnis
            if not os.path.exists('core'): os.makedirs('core')

            with open("core/vault.enc", "wb") as f:
                f.write(res.content)

            LigarsLogger.log("SYS", "Vault erfolgreich synchronisiert und versiegelt.")
            return True
        else:
            LigarsLogger.log("ERR", "Vault-Download fehlgeschlagen", f"Status: {res.status_code}")
            return False

    except Exception as e:
        LigarsLogger.log("ERR", "Kritischer Fehler beim Vault-Sync", str(e))
        return False

# -- EQUIPMANT --

def update_equipment_db_from_server():
    """Zieht die aktuellste Equipment-Datenbank vom Master-Server."""
    SERVER_URL = "http://ligars.any64.de/ddl/equipment_master.db"
    LOCAL_PATH = "equipment_master.db"

    try:
        LigarsLogger.log("SYS", "Checking for remote hardware update...")
        response = requests.get(SERVER_URL, timeout=15, stream=True)

        if response.status_code == 200:
            with open(LOCAL_PATH, 'wb') as f:
                f.write(response.content)
            LigarsLogger.log("SYS", "Hardware-Master-DB erfolgreich aktualisiert.")
            # Nach dem Download führen wir auch gleich den internen Sync aus
            sync_equipment_status()
            return True
        else:
            LigarsLogger.log("ERR", f"Update-Server nicht bereit (Status: {response.status_code})")
    except Exception as e:
        LigarsLogger.log("ERR", "Automatisches Hardware-Update fehlgeschlagen", str(e))
    return False

def sync_equipment_status():
    """Gleicht den verifizierten Status der Hardware mit der Shopping-Liste ab."""
    if not os.path.exists("equipment_master.db"):
        return

    try:
        with sqlite3.connect("equipment_master.db") as m_conn:
            m_conn.row_factory = sqlite3.Row
            # Wir suchen alle Assets, die du bereits als "OK" markiert hast
            verified_items = m_conn.execute("SELECT item_name FROM master_assets WHERE status = 1").fetchall()
            names = [row['item_name'] for row in verified_items]

        with get_db() as conn:
            for name in names:
                # Setzt den Status in der User-Datenbank auf 1 (Gekauft/Verifiziert)
                conn.execute("UPDATE einkaeufe SET status = 1 WHERE item = ?", (name,))
            conn.commit()
        LigarsLogger.log("SYS", f"Lokale Hardware-Liste aktualisiert: {len(names)} Items verifiziert.")
    except Exception as e:
        LigarsLogger.log("ERR", "Lokaler Equipment-Sync fehlgeschlagen", str(e))

def auto_update_scheduler():
    """Läuft im Hintergrund und triggert alle 24 Stunden ein Update."""
    while True:
        # 86400 Sekunden = 24 Stunden
        time.sleep(86400)
        LigarsLogger.log("SYS", "24h-Intervall erreicht: Starte Hardware-Update...")
        update_equipment_db_from_server()

def get_equipment_request_link(proband_name, product_name):
    """Erzeugt einen Mail-Link, den der Proband manuell verschickt."""
    TARGET = "ligars-core@lindner-leipzig.de"
    SUBJECT = f"[HARDWARE_ANFRAGE] Produkt: {product_name} (Proband: {proband_name})"

    BODY = (f"Hallo Master,\n\n"
            f"Ich möchte folgendes Gerät im LIGARS-System nutzen, aber es ist noch nicht zertifiziert:\n\n"
            f"PRODUKT: {product_name}\n"
            f"NUTZER: {proband_name}\n\n"
            f"Bitte pflegen Sie die Anleitung ein, damit ich den Scan abschließen kann.\n"
            f"System-ID: {hashlib.sha1(product_name.encode()).hexdigest()[:8]}\n"
            f"Bitte hänge deine Bild in JPEG vomat als anhang odser link an!")

    # Wir müssen den Text für die URL "sicher" machen (Leerzeichen -> %20 usw.)
    from urllib.parse import quote
    mailto_link = f"mailto:{TARGET}?subject={quote(SUBJECT)}&body={quote(BODY)}"

    return mailto_link

def sync_to_digital_strafbuch(target_email, subject_name, ai_feedback):
    """Überträgt die Sanktion an den Webserver."""
    api_url = "https://ligars.any64.de/api/strafbuch_sync.php"

    payload = {
        "api_key": "LIGARS_SECURE_SYNC_2026",
        "email": target_email,
        "name": subject_name,
        "content": ai_feedback
    }

    try:
        response = requests.post(api_url, json=payload, timeout=5)
        if response.status_code == 200:
            print(f">>> [WEB_SYNC]: Sanktion für {subject_name} im digitalen Strafbuch hinterlegt.")
            return True
    except Exception as e:
        print(f">>> [WEB_SYNC_ERROR]: {e}")
        return False

import requests # Falls noch nicht oben importiert

def create_forum_account(username, email, is_minor):
    """Sende Daten an die ligars_sync.php auf dem Forum-Server."""
    if is_minor:
        return None

    # 1. Ein sicheres Passwort für den User generieren
    import secrets, string
    alphabet = string.ascii_letters + string.digits
    temp_pw = ''.join(secrets.choice(alphabet) for i in range(12))

    # 2. Datenpaket schnüren
    payload = {
        'token': 'KIChanF206LIGARS_CORE', # Muss exakt wie in PHP sein!
        'username': username,
        'email': email,
        'password': temp_pw
    }

    # 3. Den PHP-VIP-Eingang aufrufen
    try:
        url = "https://www.kichan-forum.any64.de/ligars_sync.php"
        response = requests.post(url, data=payload, timeout=10)

        if "SUCCESS" in response.text:
            LigarsLogger.log("API", f"Forum-Account für {username} erfolgreich erstellt.")
            return temp_pw
        else:
            LigarsLogger.log("ERR", f"Forum-Fehler: {response.text}")
            return None
    except Exception as e:
        LigarsLogger.log("ERR", f"Verbindung zur Foren-Bridge fehlgeschlagen: {e}")
        return None

def send_discipline_mail(target_email, subject_name, ai_feedback):
    try:
        # Config sicher laden
        conf, decrypted_password = get_decrypted_password()

        if not decrypted_password:
            LigarsLogger.log("ERR", "Mail-Abbruch", "Passwort-Entschlüsselung fehlgeschlagen")
            return

        # --- KONFIGURATION ---
        SMTP_SERVER = conf['SMTP_SERVER']
        SMTP_PORT = int(conf['SMTP_PORT'])
        SENDER_EMAIL = conf['SMTP_USER']
        SENDER_PASSWORD = decrypted_password

        msg = MIMEMultipart('alternative')
        msg['From'] = f"LIGARS CORE <{SENDER_EMAIL}>"
        msg['To'] = target_email
        msg['Subject'] = f"Sanktion: Protokoll-Abweichung {subject_name}"
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain="lindner-leipzig.eu")

        # Plain Text
        text_content = f"Sanktions-Protokoll für {subject_name}.\n\n{ai_feedback}"
        msg.attach(MIMEText(text_content, 'plain'))

        # HTML Design
        html_content = f"""
        <html>
        <body style="background-color: #020202; margin: 0; padding: 20px; font-family: 'Consolas', monospace; color: #eee;">
            <div style="max-width: 600px; margin: auto; border: 1px solid #ff0055; padding: 20px; background-color: #050505;">
                <div style="background-color: #ff0055; color: white; padding: 10px; text-align: center; font-weight: bold; letter-spacing: 2px;">
                    LIGARS // SANKTIONS_PROTOKOLL
                </div>
                <p style="color: #888; font-size: 12px; border-bottom: 1px solid #222; padding-bottom: 10px;">
                    ID: {subject_name.upper()} | TS: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
                <div style="padding: 15px; background: #0a0a0a; border-left: 3px solid #ff0055; white-space: pre-wrap;">
                    {ai_feedback}
                </div>
                <p style="font-size: 10px; color: #444; margin-top: 20px; text-align: center;">
                    Dies ist eine systemgenerierte Nachricht. Widerstand zwecklos.
                </p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, 'html'))

        # --- DER VERSAND (Jetzt ohne Fehler) ---
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        LigarsLogger.log("MAIL", "Versand erfolgreich", f"An: {target_email}")
        # --- NEU: SYNCHRONISATION MIT DIGITALEM STRAFBUCH ---
        # Dies wird erst aufgerufen, wenn der Mail-Versand erfolgreich war
        sync_to_digital_strafbuch(target_email, subject_name, ai_feedback)

    except Exception as e:
        LigarsLogger.log("ERR", "Mail-Versand fehlgeschlagen", str(e))

# --- ROUTES ---

@app.route('/emergency_shutdown', methods=['POST'])
def shutdown():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    DB_FILENAME = 'database.db' # Dein spezifischer Dateiname

    # 1. BACKUP-LOGIK
    try:
        if not os.path.exists('backups'):
            os.makedirs('backups')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backups/ligars_auto_backup_{timestamp}.db"

        if os.path.exists(DB_FILENAME):
            shutil.copy2(DB_FILENAME, backup_name)
            print(f">>> SYSTEM: Backup von {DB_FILENAME} erstellt -> {backup_name}")
        else:
            print(f">>> SYSTEM_WARNUNG: {DB_FILENAME} nicht gefunden, Backup übersprungen.")
    except Exception as e:
        print(f">>> SYSTEM_ERROR (Backup): {e}")

    # 2. SESSION KILLEN
    session.clear()

    # 3. ABSCHALT-SEQUENZ (verzögert um 1 Sekunde)
    def kill_process():
        import time
        time.sleep(1)
        print(">>> LIGARS_CORE: Prozess-Terminierung ausgeführt.")
        os.kill(os.getpid(), signal.SIGINT)

    threading.Thread(target=kill_process).start()

    return """
    <html>
    <body style="background:#000; color:#00ffcc; font-family:monospace; display:flex; justify-content:center; align-items:center; height:100vh; flex-direction:column; text-align:center;">
        <h1 style="border:1px solid #ff0055; padding:20px; color:#ff0055;">SYSTEM_OFFLINE</h1>
        <p>Datenbank (database.db) wurde gesichert.<br>LIGARS_CORE Prozess beendet.</p>
        <small style="color:#444;">Server-Prozess terminiert.</small>
    </body>
    </html>
    """

@app.route('/debug_mail')
def debug_mail():
    # Sicherheitscheck: Nur eingeloggte Admins dürfen testen
    if not session.get('logged_in'):
        return "ZUGRIFF_VERWEIGERT: Authentifizierung erforderlich.", 403

    with get_db() as conn:
        settings_raw = conn.execute("SELECT name, wert FROM settings").fetchall()
        settings = {row['name']: row['wert'] for row in settings_raw}

    target = settings.get('proband_mail')
    name = settings.get('proband_name', 'Test-Subjekt')

    if not target:
        return "FEHLER: Keine Probanden-Mail in den Einstellungen gefunden."

    # Wir simulieren einen harten Trigger-Text
    test_feedback = f"<b>SYSTEM_CHECK:</b> Dies ist eine Test-Sanktion. Trigger-Wort: <b>UNGENÜGEND</b>. Die Verbindung zu mail.lindner-leipzig.de wird geprüft."

    try:
        # Aufruf deiner bestehenden Mail-Funktion
        send_discipline_mail(target, name, test_feedback)

        return f"""
        <div style="background:#000; color:#00ffcc; padding:20px; font-family:monospace; border:2px solid #00ffcc;">
            <h2>DEBUG_MAIL_ERFOLGREICH</h2>
            <p>Die Mail wurde an <b>{target}</b> adressiert und dem Server übergeben.</p>
            <p>Status: GESENDET</p>
            <hr>
            <a href="/" style="color:#fff;">Zurück zum Core</a>
        </div>
        """
    except Exception as e:
        # Hier fangen wir den Fehler ab, falls der SMTP-Server ablehnt
        return f"""
        <div style="background:#000; color:#ff0055; padding:20px; font-family:monospace; border:2px solid #ff0055;">
            <h2>DEBUG_MAIL_FEHLGESCHLAGEN</h2>
            <p>Fehlermeldung: <b>{str(e)}</b></p>
            <hr>
            <p>Checkliste:<br>
            1. Passwort korrekt?<br>
            2. Port 465 (SSL) offen?<br>
            3. Mail-Adresse bei Lindner-Leipzig aktiv?</p>
            <a href="/" style="color:#fff;">Zurück zum Core</a>
        </div>
        """

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        birthdate_str = request.form.get('bday')
        password_input = request.form.get('pw')

        # 1. Passwort-Check
        if password_input != CONF.get('WEB_PASSWORD', 'Sissy2026'):
            LigarsLogger.log("ERR", "Login-Fehler: Ungültiger Sicherheits-Code.")
            return render_template('login.html', error="SICHERHEITS_CODE_UNGÜLTIG")

        # 2. Alters-Verifizierung & Session-Eintrag
        if birthdate_str:
            try:
                birthdate = datetime.strptime(birthdate_str, '%Y-%m-%d').date()
                today = date.today()
                age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

                # LOGIN ERLAUBEN, aber Status speichern
                session['logged_in'] = True
                session['user_age'] = age

                if age < 18:
                    session['is_minor'] = True
                    LigarsLogger.log("INFO", f"Eingeschränkter Login (Minderjährig): Alter {age}")
                else:
                    session['is_minor'] = False
                    LigarsLogger.log("INFO", f"Vollständiger Login (Erwachsen): Alter {age}")

                return redirect(url_for('dashboard'))

            except ValueError:
                return render_template('login.html', error="DATUMSFORMAT_UNGÜLTIG")
        else:
            return render_template('login.html', error="GEBURTSDATUM_ERFORDERLICH")

    return render_template('login.html')

@app.route('/intro', methods=['GET', 'POST'])
def intro():
    # Zeige das neue atmosphärische Intro
    return render_template('intro_new.html')

@app.route('/intro_done', methods=['GET', 'POST'])
def intro_done():
    # Setze das Flag in der Session, damit das Intro nicht erneut kommt
    session['intro_seen'] = True
    # WICHTIG: Hier leiten wir auf 'index' weiter, da 'dashboard' nicht existiert
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    MOBILE_TOKEN = "LIGARS_UPDATE_ACCESS_77"
    is_mobile_update = (request.args.get('mode') == 'update' and
                        request.args.get('token') == MOBILE_TOKEN)

    # 1. AUTH CHECK
    if not session.get('logged_in') and not is_mobile_update:
        return redirect(url_for('login'))

    is_minor = session.get('is_minor', False)

    # 2. INTRO-LOGIK
    if not session.get('intro_seen'):
        return redirect(url_for('intro'))

    user_reply = request.form.get('user_interaction', '') if request.method == 'POST' else ""

    with get_db() as conn:
        # --- 3. DATENBANK-HYGIENE ---
        jetzt_str = datetime.now().isoformat()
        heute = date.today()
        conn.execute("UPDATE aktive_missionen SET status = 'ERLEDIGT' WHERE status = 'AKTIV' AND ablauf_zeit < ?", (jetzt_str,))
        conn.execute("DELETE FROM aktive_missionen WHERE start_zeit < date('now', '-7 days')")
        conn.commit()

        # --- 4. BASIS-DATEN LADEN (Immer benötigt für den Prompt) ---
        settings_raw = conn.execute("SELECT name, wert FROM settings").fetchall()
        settings = {row['name']: row['wert'] for row in settings_raw}

        if 'start_date' not in settings or not settings['start_date']:
            return redirect(url_for('setup'))

        proband_name = settings.get('proband_name', 'UNBEKANNT')
        proband_mail = settings.get('proband_mail')
        bio_alter = settings.get('alter', 'N/A')
        bio_gewicht = settings.get('gewicht', 'N/A')

        # Biometrie aus letztem Log
        last_log_row = conn.execute("SELECT taille, brust, hals, datei FROM eintraege ORDER BY id DESC LIMIT 1").fetchone()
        if last_log_row:
            bio_taille = last_log_row['taille'] or 'N/A'
            bio_brust = last_log_row['brust'] or 'N/A'
            bio_hals = last_log_row['hals'] or 'N/A'
            raw_files = last_log_row['datei'] or ""
        else:
            bio_taille = bio_brust = bio_hals = 'KEINE_DATEN'
            raw_files = ""

        # Hardware & Knowledge Base laden
        hardware_knowledge_base = "KEINE_DATEN_VORHANDEN"
        equipment_rows = conn.execute("SELECT item FROM einkaeufe WHERE status = 1").fetchall()
        owned_items = [r['item'] for r in equipment_rows]
        equipment_str = ", ".join(owned_items) or "KEIN_EQUIPMENT_VORHANDEN"

        if os.path.exists("equipment_master.db") and owned_items:
            try:
                with sqlite3.connect("equipment_master.db") as m_conn:
                    m_conn.row_factory = sqlite3.Row
                    placeholders = ', '.join(['?'] * len(owned_items))
                    assets = m_conn.execute(
                        f"SELECT item_name, ki_knowledge FROM master_assets WHERE item_name IN ({placeholders})",
                        owned_items
                    ).fetchall()
                    knowledge_parts = [f"IDENT_ID_{a['item_name']}: {a['ki_knowledge']}" for a in assets]
                    if knowledge_parts: hardware_knowledge_base = "\n".join(knowledge_parts)
            except Exception as e:
                LigarsLogger.log("ERR", "HW-Injektion Fehler", str(e))

        # Zeit & Plan
        try:
            start_dt = datetime.strptime(settings['start_date'], '%Y-%m-%d').date()
            tage_total = (heute - start_dt).days + 1
            aktuelle_woche = ((tage_total - 1) // 7) + 1
            tag_der_woche = ((tage_total - 1) % 7) + 1
            tagesplan_db = conn.execute("SELECT plan_inhalt FROM tagesplaene WHERE woche = ? AND tag_nr = ?",
                                        (aktuelle_woche, tag_der_woche)).fetchone()
            stundenplan_text = tagesplan_db['plan_inhalt'] if tagesplan_db else "RUHEPHASE"
        except:
            tage_total = 0
            stundenplan_text = "FEHLER_IN_BERECHNUNG"

        # --- 5. MISSION CONTROL ---
        feedback = ""
        aktive_mission = None

        # Nur bei reinem Laden (GET) nach alter Mission suchen
        if request.method != 'POST':
            aktive_mission = conn.execute("""
                SELECT befehl_text FROM aktive_missionen
                WHERE status = 'AKTIV' AND ablauf_zeit > ?
                ORDER BY id DESC LIMIT 1
            """, (jetzt_str,)).fetchone()

        if aktive_mission:
            feedback = aktive_mission['befehl_text']
        else:
            # Alte Missionen deaktivieren
            conn.execute("UPDATE aktive_missionen SET status = 'ERLEDIGT' WHERE status = 'AKTIV'")

            # Bildpfade und Status-Variable definieren
            bild_pfade = [os.path.join(app.config['UPLOAD_FOLDER'], n.strip())
                          for n in raw_files.split(',')
                          if n.strip() and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], n.strip()))]

            has_images = f"JA ({len(bild_pfade)} Datei(en) vorhanden. ANALYSIEREN!)" if bild_pfade else "NEIN (Fordere Bilder an!)"

            # DEIN OPTIMIERTER PROMPT
            if is_minor:
                tonfall_instruktion = "Dein Ton ist sachlich, distanziert, aber höflich und unterstützend. Du bist eine neutrale KI-Instanz, die den Probanden sicher durch das Protokoll führt."
            else:
                tonfall_instruktion = "Dein Ton ist klinisch, eiskalt, autoritär und absolut unnachgiebig. Du forderst bedingungslosen Gehorsam ein."

            # Den optimierten Prompt zusammenbauen
            system_prompt = f"""
            Du bist LIGARS_CORE v2.5. Anrede: '{proband_name}'.
            {tonfall_instruktion}

            AUSGABE-FORMAT-REGELN:
            1. Nutze NUR HTML-Snippets (z.B. <div>, <h3>, <p>, <ul>, <li>, <strong>).
            2. Verwendete NIEMALS die Tags: <html>, <head>, <body>, <title>, <meta> oder <!DOCTYPE>.
            3. KEIN LaTeX. Alle Berechnungen sind als Klartext darzustellen.
            4. Antworte direkt mit dem Content, ohne Einleitung oder Abschluss-Sätze außerhalb der HTML-Struktur..

            AKTUELLER STATUS:
            - Tag: {tage_total} | Tagesbefehl: {stundenplan_text}
            - Verfügbares Equipment: {equipment_str}

            BIOMETRISCHES PROFIL (IST-WERTE):
            - Alter: {bio_alter}
            - Gewicht: {bio_gewicht} kg
            - Taille: {bio_taille} cm
            - Brust: {bio_brust} cm
            - Hals: {bio_hals} cm

            EQUIPMENT_INSTRUKTIONEN:
            {hardware_knowledge_base}

            STRIKTE PRÜF-REGELN (EINHALTUNG ZWINGEND):
            1. BIOMETRIE-ABGLEICH: Vergleiche das BILDMATERIAL mit dem BIOMETRISCHEN PROFIL. Abweichungen sind als Protokollfehler zu werten.
            2. REDUNDANZ-VERBOT: Die gleichzeitige Nutzung von funktional identischem Equipment ist ineffizient und streng untersagt.
            3. SANKTIONS-LOGIK: Sanktionen müssen ZWINGEND mit dem vorhandenen Equipment ausgeführt werden. Erfinde KEIN Equipment, das nicht in der Liste steht.
            4. DISZIPLIN: Kurze, freche oder verweigernde Antworten des Probanden (z.B. ein einzelner Punkt '.') führen sofort zu einer Disziplinarmaßnahme.
            5. PROAKTIVE AUTORITÄT: Du hast die Befugnis, auch außerhalb des Tagesbefehls zusätzliche Anweisungen zu erteilen, sofern diese mit dem verfügbaren Equipment umsetzbar sind. Fordere absoluten Gehorsam ein.

            BILDMATERIAL VORHANDEN: {has_images}
            """

            try:
                conf = load_config()
                task_prompt = f"Eingabe des Probanden: '{user_reply}'. Führe Analyse und Anweisung durch."
                raw_feedback = generate_ai_content(conf['GEMINI_API_KEY'], system_prompt, task_prompt, bild_pfade)

                # --- SICHERHEITS-FILTER (Verhindert Layout-Zerstörung) ---
                feedback = raw_feedback.replace('```html', '').replace('```', '').strip()
                forbidden_tags = ["<html>", "</html>", "<body>", "</body>", "<head>", "</head>", "<!DOCTYPE"]
                for tag in forbidden_tags:
                    feedback = feedback.replace(tag, "")

                # --- SANKTIONS-CHECK ---
                import re
                trigger_words = ["UNGEHORSAM", "RÜGE", "STRENG", "STRAFE", "SANKTION", "SANKTION_AKTIVIERT"]
                clean_text = re.sub('<[^<]+?>', '', feedback).upper()
                is_reprimand = any(word in clean_text for word in trigger_words)
                mail_status = 0

                if is_reprimand and proband_mail:
                    try:
                        send_discipline_mail(proband_mail, proband_name, feedback)
                        mail_status = 1
                    except Exception as e:
                        LigarsLogger.log("ERR", "Mail-Versand fehlgeschlagen", str(e))

                # Speichern der neuen Mission mit Mail-Status
                ablauf_str = datetime.combine(heute, datetime.max.time()).isoformat()
                conn.execute("""
                    INSERT INTO aktive_missionen (befehl_text, equipment_genutzt, status, start_zeit, ablauf_zeit, mail_gesendet)
                    VALUES (?, ?, 'AKTIV', ?, ?, ?)
                """, (feedback, equipment_str, jetzt_str, ablauf_str, mail_status))
                conn.commit()
            except Exception as e:
                feedback = f"<div class='err'>KI_FEHLER: {str(e)}</div>"

        # QR-Code generieren
        qr_url = f"http://{get_local_ip()}:8000/?mode=update&token={MOBILE_TOKEN}"
        qr = qrcode.QRCode(version=1, box_size=5, border=2)
        qr.add_data(qr_url)
        img_io = io.BytesIO()
        qr.make_image().save(img_io, 'PNG')
        qr_base64 = base64.b64encode(img_io.getvalue()).decode()

        return render_template('index.html',
                               feedback=feedback,
                               stundenplan=stundenplan_text,
                               tag=tage_total,
                               proband_name=proband_name,
                               qr_code_img=qr_base64,
                               is_mobile_update=is_mobile_update,
                               generated_pw=session.get('generated_pw'),
                               is_ajax=(request.headers.get('X-Requested-With') == 'XMLHttpRequest'))

@app.route('/add', methods=['POST'])
def add():
    # 1. AUTH-CHECK (Zentrale Token-Verwaltung)
    MOBILE_TOKEN = "LIGARS_UPDATE_ACCESS_77"
    token_val = request.args.get('token') or request.form.get('token')
    is_mobile = (request.args.get('mode') == 'update' or request.form.get('mode') == 'update') and \
                (token_val == MOBILE_TOKEN)

    if not session.get('logged_in') and not is_mobile:
        LigarsLogger.log("ERR", "Unautorisierter Zugriff auf /add!")
        return redirect(url_for('login'))

    # 2. DATEN EXTRAKTION
    taille = request.form.get('taille')
    brust  = request.form.get('brust')
    hals   = request.form.get('hals')
    notiz  = request.form.get('notizen')
    datum  = date.today().isoformat()

    # 3. FOTO-VERARBEITUNG
    saved_filenames = []
    if 'fotos' in request.files:
        files = request.files.getlist('fotos')
        for i, file in enumerate(files):
            if file and file.filename != '':
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else "jpg"
                timestamp = int(time.time())
                filename = secure_filename(f"{timestamp}_{i}.{ext}")

                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])

                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                saved_filenames.append(filename)

    foto_db_string = ",".join(saved_filenames)

    # 4. DATENBANK-TRANSFER & SOFORT-ENTWERTUNG
    try:
        with get_db() as conn:
            # A) Neue biometrische Daten speichern
            conn.execute('''
                INSERT INTO eintraege (datum, taille, brust, hals, notizen, datei)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (datum, taille, brust, hals, notiz, foto_db_string))

            # B) ALTE MISSION BEENDEN (Der wichtigste Part für die Neuanalyse)
            conn.execute("UPDATE aktive_missionen SET status = 'ERLEDIGT' WHERE status = 'AKTIV'")

            conn.commit()

        # LOGGING
        source = "MOBILE" if is_mobile else "WEB"
        LigarsLogger.log("DB", f"LOG_EINGANG [{source}] | Mission entwertet, Neuanalyse durch index() erzwungen.")
        if saved_filenames:
            LigarsLogger.log("SYS", f"Fotos verarbeitet: {len(saved_filenames)} Datei(en).")

    except Exception as e:
        LigarsLogger.log("ERR", f"Datenbank-Fehler in /add: {e}")
        return f"KERN-FEHLER: {str(e)}", 500

    # 5. REDIRECT (Token-Erhalt für Mobile-Workflow)
    # Da die Mission jetzt 'ERLEDIGT' ist, wird index() beim Laden sofort die KI starten
    if is_mobile:
        return redirect(url_for('index', mode='update', token=MOBILE_TOKEN))

    return redirect(url_for('index'))

@app.route('/shopping', methods=['GET', 'POST'])
def shopping():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    user = session.get('user', 'Unbekannt')
    # Variable für den Mail-Link, falls eine Zertifizierung fehlt
    request_link = None
    missing_item = None

    if request.method == 'POST':
        # --- FALL A: STATUS UMSCHALTEN (Toggle) ---
        if 'id' in request.form:
            item_id = request.form.get('id')

            # 1. Namen des Items holen, bevor wir updaten
            item_row = conn.execute("SELECT item, status FROM einkaeufe WHERE id = ?", (item_id,)).fetchone()

            if item_row:
                item_name = item_row['item']
                old_status = item_row['status']

                # Wir schalten auf "Gekauft" (Status wird 1)
                if old_status == 0:
                    # PRÜFUNG: Ist das Teil in der Master-DB zertifiziert?
                    if os.path.exists("equipment_master.db"):
                        with sqlite3.connect("equipment_master.db") as m_conn:
                            m_conn.row_factory = sqlite3.Row
                            asset = m_conn.execute("SELECT ki_knowledge FROM master_assets WHERE item_name = ?", (item_name,)).fetchone()

                        # Wenn Wissen fehlt: Link generieren und Status-Update verhindern/warnen
                        if not asset or not asset['ki_knowledge']:
                            request_link = get_equipment_request_link(user, item_name)
                            missing_item = item_name
                            LigarsLogger.log("SYS", f"Hardware-Warnung in Shopping-Liste: {item_name} nicht zertifiziert.")

                # Status in der DB umschalten
                conn.execute("UPDATE einkaeufe SET status = 1 - status WHERE id = ?", (item_id,))
                conn.commit()
                LigarsLogger.log("DB", f"Status für Item ID {item_id} ({item_name}) geändert.")

        # --- FALL B: NEUES ITEM HINZUFÜGEN ---
        elif 'item' in request.form:
            item_name = request.form.get('item')
            link = request.form.get('link', '')
            raw_preis = request.form.get('preis', '0').replace(',', '.')
            try:
                preis = float(raw_preis)
            except ValueError:
                preis = 0.0

            if item_name:
                conn.execute(
                    "INSERT INTO einkaeufe (item, phase, link, preis, status) VALUES (?, ?, ?, ?, 0)",
                    (item_name, 'MANUELL', link, preis)
                )
                conn.commit()
                LigarsLogger.log("DB", f"Neues Equipment hinzugefügt: {item_name}")

    # --- DATEN FÜR DAS TEMPLATE LADEN ---
    items = conn.execute("SELECT * FROM einkaeufe ORDER BY status ASC, id DESC").fetchall()
    total_res = conn.execute("SELECT SUM(CAST(preis AS REAL)) FROM einkaeufe WHERE status=1").fetchone()
    total = round(total_res[0], 2) if total_res and total_res[0] else 0.0

    return render_template('shopping.html',
                           items=items,
                           total=total,
                           request_link=request_link,
                           missing_item=missing_item)

@app.route('/buy/<int:id>')
def buy(id):
    """
    Markiert ein Equipment-Teil direkt als 'Gekauft'.
    """
    if not session.get('logged_in'):
        LigarsLogger.log("ERR", f"Unautorisierter Kauf-Versuch für ID: {id}")
        return redirect(url_for('login'))

    try:
        with get_db() as conn:
            # Wir holen uns den Namen des Items für den Log, bevor wir es updaten
            item = conn.execute("SELECT item FROM einkaeufe WHERE id=?", (id,)).fetchone()
            item_name = item['item'] if item else f"Unbekannt (ID: {id})"

            # Status auf 1 (Gekauft) setzen
            conn.execute("UPDATE einkaeufe SET status=1 WHERE id=?", (id,))
            conn.commit()

            LigarsLogger.log("DB", f"EQUIPMENT_UPDATE: '{item_name}' wurde als gekauft markiert.")

    except Exception as e:
        LigarsLogger.log("ERR", f"Fehler beim Kauf-Update (ID {id}): {e}")

    return redirect(url_for('shopping'))

@app.route('/archiv')
def archiv():
    """
    Zeigt die vollständige Historie aller biometrischen Logs und Fotos an.
    """
    if not session.get('logged_in'):
        LigarsLogger.log("ERR", "Unautorisierter Zugriff auf das Archiv!")
        return redirect(url_for('login'))

    try:
        with get_db() as conn:
            # Wir ziehen alle Einträge, die neuesten zuerst
            logs = conn.execute("SELECT * FROM eintraege ORDER BY id DESC").fetchall()

            # Statistik für den Logger
            log_count = len(logs)
            LigarsLogger.log("SYS", f"Archiv aufgerufen. {log_count} Einträge geladen.")

            # Kleiner Helfer: Wir bereiten die Logs für das Template vor,
            # falls wir die Foto-Strings in Listen umwandeln wollen.
            processed_logs = []
            for log in logs:
                log_dict = dict(log)
                # Falls Fotos vorhanden sind, machen wir eine Liste daraus
                if log_dict.get('datei'):
                    log_dict['foto_liste'] = log_dict['datei'].split(',')
                else:
                    log_dict['foto_liste'] = []
                processed_logs.append(log_dict)

    except Exception as e:
        LigarsLogger.log("ERR", f"Fehler beim Laden des Archivs: {e}")
        processed_logs = []

    return render_template('archiv.html', logs=processed_logs)

from cryptography.fernet import Fernet

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # --- 0. KI MODEL INITIALISIEREN ---
    import google.generativeai as genai
    genai.configure(api_key=CONF['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-3-flash-preview')

    # --- 1. VAULT ENTSCHLÜSSELUNG & FILTERUNG ---
    available_plans = []
    vault_content = {}
    is_minor = session.get('is_minor', False)

    try:
        vault_path = os.path.join('core', 'vault.enc')
        if os.path.exists(vault_path):
            cipher_suite = Fernet(SECRET_KEY)
            with open(vault_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = cipher_suite.decrypt(encrypted_data)
            vault_content = json.loads(decrypted_data.decode('utf-8'))

            if isinstance(vault_content, dict) and "plaene" in vault_content:
                vault_content = vault_content["plaene"]

            for name, data in vault_content.items():
                plan_level = data.get('level', 0)
                if is_minor:
                    if plan_level <= 4:
                        available_plans.append(name)
                else:
                    available_plans.append(name)

            LigarsLogger.log("SYS", f"Vault entsperrt. Filter: {'Jugendschutz' if is_minor else 'Vollzugriff'}.")
    except Exception as e:
        LigarsLogger.log("ERR", f"KRITISCHER_KEY_FEHLER: {e}")
        available_plans = ["KEY_MISMATCH_OR_FILE_MISSING"]

    # --- 2. VERARBEITUNG (POST) ---
    if request.method == 'POST':
        selected_plan_name = request.form.get('plan')

        if selected_plan_name not in available_plans:
            LigarsLogger.log("SEC", f"BLOCKIERT: Unerlaubtes Protokoll: {selected_plan_name}")
            return "ZUGRIFF_VERWEIGERT", 403

        p_data = {
            'proband_name': request.form.get('name'),
            'proband_mail': request.form.get('email'),
            'alter': request.form.get('alter'),
            'gewicht': request.form.get('gewicht'),
            'start_date': request.form.get('start_date'),
            'plan': selected_plan_name,
            'schicht_system': request.form.get('schicht_system'),
            'start_schicht': request.form.get('start_schicht')
        }

        pool = [s for s in ['frueh', 'spaet', 'nacht', 'tag'] if request.form.get(f'pool_{s}')]
        s_zeiten = {s: f"{request.form.get(f'time_start_{s}')}-{request.form.get(f'time_end_{s}')}"
                    for s in ['Frühschicht', 'Spätschicht', 'Nachtschicht', 'Tagdienst']
                    if request.form.get(f'time_start_{s}')}

        # --- 3. SPEICHERN ---
        try:
            with get_db() as conn:
                for key, val in p_data.items():
                    conn.execute("INSERT OR REPLACE INTO settings (name, wert) VALUES (?, ?)", (key, val))

                conn.execute("INSERT OR REPLACE INTO settings (name, wert) VALUES ('schicht_pool', ?)", (json.dumps(pool),))
                conn.execute("INSERT OR REPLACE INTO settings (name, wert) VALUES ('schicht_zeiten', ?)", (json.dumps(s_zeiten),))

                conn.execute("DELETE FROM einkaeufe")
                selected_config = vault_content.get(p_data['plan'], {})
                for item in selected_config.get('shopping_list', []):
                    conn.execute("INSERT INTO einkaeufe (item, link, preis, phase, status) VALUES (?, ?, ?, ?, 0)",
                                 (item.get('name'), item.get('link'), item.get('preis', '0.00'), p_data['plan']))

                conn.commit()
                LigarsLogger.log("DB", f"Setup für {p_data['proband_name']} gespeichert.")

            # --- 4. FORUM-SYNCHRONISATION (NEU) ---
            # Wir erstellen den Account nur für Volljährige (Weg A Schutz)
            forum_password = create_forum_account(
                p_data['proband_name'],
                p_data['proband_mail'],
                is_minor
            )

            if forum_password:
                # Passwort für die Anzeige im Dashboard zwischenspeichern
                session['generated_pw'] = forum_password
                session['show_forum_info'] = True

            # --- 5. GENERIERUNG MASTERPLAN ---
            generate_48_weeks_masterplan(
                p_data['plan'],
                selected_config,
                p_data['schicht_system'],
                p_data['start_schicht'],
                pool,
                model
            )

        except Exception as e:
             LigarsLogger.log("ERR", f"Kritischer Fehler im Setup: {e}")
             return f"SETUP_FAILURE: {e}", 500

        return redirect(url_for('index'))

    return render_template('setup.html', plaene=available_plans)

@app.route('/plan')
def plan():
    """
    Visualisiert den gesamten 48-Wochen-Masterplan.
    Führt Wochen-Aufgaben und Tages-Details effizient zusammen.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        conn = get_db()

        # 1. Basis-Daten laden
        current_plan = conn.execute("SELECT wert FROM settings WHERE name = 'plan'").fetchone()
        plan_name = current_plan['wert'] if current_plan else "UNBEKANNT"

        # 2. Alle Wochen und Tage in einem Rutsch laden (Performance!)
        wochen_raw = conn.execute("SELECT woche, aufgabe, equipment_event FROM wochenplan ORDER BY woche ASC").fetchall()
        tage_raw = conn.execute("SELECT woche, tag_nr, plan_inhalt FROM tagesplaene ORDER BY woche ASC, tag_nr ASC").fetchall()

        # 3. Datenstruktur für das Template bauen (Woche -> Liste von 7 Tagen)
        wochen_liste = []
        for w in wochen_raw:
            woche_dict = dict(w)
            # Wir filtern die Tage, die zu dieser Woche gehören
            woche_dict['tage'] = [dict(t) for t in tage_raw if t['woche'] == w['woche']]
            wochen_liste.append(woche_dict)

        LigarsLogger.log("SYS", f"Masterplan-Übersicht für '{plan_name}' geladen ({len(wochen_liste)} Wochen).")

    except Exception as e:
        LigarsLogger.log("ERR", f"Fehler beim Laden der Plan-Übersicht: {e}")
        wochen_liste = []
        plan_name = "ERROR"

    return render_template('plan.html', wochen=wochen_liste, plan_name=plan_name)

@app.route('/tagesplan/<int:woche>/<int:tag_nr>')
def tagesplan_detail(woche, tag_nr):
    """
    Einzeldarstellung eines spezifischen Tagesplans für maximale Konzentration.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        conn = get_db()

        # 1. Spezifischen Tagesplan laden
        row = conn.execute("""
            SELECT plan_inhalt FROM tagesplaene
            WHERE woche = ? AND tag_nr = ?
        """, (woche, tag_nr)).fetchone()

        if not row:
            LigarsLogger.log("ERR", f"Detail-Abruf fehlgeschlagen: W{woche}/T{tag_nr} existiert nicht.")
            return "FEHLER: Datensatz nicht gefunden. Bitte Masterplan neu generieren.", 404

        # 2. Metadaten für den Header laden
        name_row = conn.execute("SELECT wert FROM settings WHERE name='proband_name'").fetchone()
        proband_name = name_row['wert'] if name_row else "SUBJEKT"

        # 3. Formatierung: Wir wandeln \n in <br> um, falls das Template kein 'white-space: pre-wrap' nutzt
        inhalt_html = row['plan_inhalt'].replace('\n', '<br>')

        LigarsLogger.log("SYS", f"Detail-Ansicht geladen: Woche {woche}, Tag {tag_nr} für {proband_name}.")

    except Exception as e:
        LigarsLogger.log("ERR", f"Fehler in tagesplan_detail: {e}")
        return "KERN_FEHLER", 500

    return render_template('tagesplan_detail.html',
                           woche=woche,
                           tag_nr=tag_nr,
                           inhalt=inhalt_html,
                           proband_name=proband_name)

@app.route('/print_plan')
def print_plan():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    with get_db() as conn:
        conn.row_factory = sqlite3.Row

        # 1. Tagespläne laden
        plaene = conn.execute("SELECT woche, tag_nr, plan_inhalt FROM tagesplaene ORDER BY woche, tag_nr").fetchall()

        # 2. Wochenplan laden (aus Tabelle 'wochenplan' wie im Screenshot)
        wochen_info = conn.execute("SELECT woche, aufgabe, equipment_event FROM wochenplan ORDER BY woche").fetchall()
        wochen_dict = {w['woche']: {"aufgabe": w['aufgabe'], "event": w['equipment_event']} for w in wochen_info}

        # 3. Metadaten
        s = conn.execute("SELECT wert FROM settings WHERE name = 'proband_name'").fetchone()
        proband = s['wert'] if s else "UNBEKANNT"

    return render_template('print_plan.html',
                           plaene=plaene,
                           wochen_dict=wochen_dict,
                           proband_name=proband,
                           now=datetime.now().strftime("%d.%m.%Y"))

@app.route('/uploads/<path:filename>')
def custom_static(filename):
    """
    Serviert hochgeladene Fotos sicher aus dem konfigurierten UPLOAD_FOLDER.
    """
    # 1. AUTH-CHECK (Optional, falls nur du deine Bilder sehen darfst)
    if not session.get('logged_in'):
        # Wir loggen unbefugte Bild-Zugriffe im Terminal
        LigarsLogger.log("ERR", f"SECURITY: Unbefugter Bild-Zugriff auf {filename}")
        return redirect(url_for('login'))

    try:
        # 2. Auslieferung der Datei
        # send_from_directory verhindert 'Directory Traversal' Angriffe automatisch
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    except Exception as e:
        LigarsLogger.log("ERR", f"Bild konnte nicht geladen werden: {filename}", str(e))
        return "BILD_NICHT_GEFUNDEN", 404

from werkzeug.utils import secure_filename

@app.route('/upload', methods=['POST'])
def upload():
    """
    Nachträglicher Foto-Upload für den aktuellen Kalendertag.
    Aktualisiert den bestehenden Datenbank-Eintrag.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if 'fotos' not in request.files:
        LigarsLogger.log("ERR", "Upload-Versuch ohne Dateidaten.")
        return redirect(request.url)

    files = request.files.getlist('fotos')
    filenames = []
    upload_path = app.config.get('UPLOAD_FOLDER', 'static/uploads')

    # 1. Verzeichnis-Check
    if not os.path.exists(upload_path):
        os.makedirs(upload_path)

    # 2. Dateien verarbeiten
    for file in files:
        if file and file.filename:
            # Zeitstempel + sicherer Name, um Überschreiben zu verhindern
            ts = int(time.time())
            filename = secure_filename(f"{date.today()}_{ts}_{file.filename}")
            file.save(os.path.join(upload_path, filename))
            filenames.append(filename)

    if not filenames:
        return redirect(url_for('index'))

    # 3. Datenbank-Update (JSON-Verfahren)
    try:
        conn = get_db()
        # Wir speichern die Liste als JSON-String, damit das Archiv sie wieder splitten kann
        foto_json = json.dumps(filenames)

        # Hinweis: Prüfe, ob deine Spalte 'foto' oder 'datei' heißt (hier 'foto' laut deinem Snippet)
        conn.execute("UPDATE eintraege SET datei = ? WHERE datum = ?",
                     (foto_json, date.today().isoformat()))
        conn.commit()

        LigarsLogger.log("DB", f"Foto-Update: {len(filenames)} Bilder zum heutigen Log hinzugefügt.")

    except Exception as e:
        LigarsLogger.log("ERR", f"Fehler beim Foto-Update in der DB: {e}")
        return "UPLOAD_DATABASE_ERROR", 500

    return redirect(url_for('index'))

@app.route('/favicon.ico')
def favicon():
    return '', 204 # "No Content" - schaltet die Fehlermeldung im Log stumm

@app.route('/survey', methods=['GET', 'POST'])
def survey():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # 1. Aktuelles Protokoll für den Kontext laden
    protokoll_text = "Kein aktives Protokoll vorhanden."
    with get_db() as conn:
        aktive_mission = conn.execute(
            "SELECT befehl_text FROM aktive_missionen WHERE status = 'AKTIV' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if aktive_mission:
            protokoll_text = aktive_mission['befehl_text']

    if request.method == 'POST':
        # 2. Daten sammeln
        survey_data = {
            "proband": session.get('proband_name', 'Philipp'),
            "datum": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "protokoll_snapshot": protokoll_text, # Was war der Befehl?
            "energie_level": request.form.get('energie'),
            "disziplin_notiz": request.form.get('disziplin'),
            "koerper_befinden": request.form.get('koerper'),
            "is_public": 1 if request.form.get('oeffentlich') == 'on' else 0
        }

        # 3. Via API an die Webseite senden
        try:
            response = requests.post(
                "https://ligars.any64.de/api/umpfage.php",
                json=survey_data,
                timeout=10
            )
            if response.status_code == 200:
                status_msg = "SUCCESS"
            else:
                status_msg = f"SERVER_ERROR_{response.status_code}"
        except Exception as e:
            status_msg = f"CONNECTION_LOST: {str(e)}"

        return render_template('survey.html', status=status_msg, protokoll=protokoll_text)

    return render_template('survey.html', protokoll=protokoll_text)

# --- 404: Seite nicht gefunden ---
@app.errorhandler(404)
def error_404(e):
    return render_template('error.html',
                           code="404",
                           id="NULL_VOID",
                           msg="DATENPFAD_NICHT_GEFUNDEN",
                           details="Die angeforderte Sektor-Adresse existiert nicht im LIGARS-Netzwerk."), 404
# --- 500: System-Absturz ---
@app.errorhandler(500)
def error_500(e):
    # 1. Eindeutige Error-ID generieren
    error_id = str(uuid.uuid4())[:8].upper()

    # 2. Fehlermeldung analysieren (KI-spezifisch)
    original_error = str(e).lower()

    # Standard-Werte
    display_msg = "SYSTEM_CRITICAL_FAILURE"
    detail_msg = "Ein unerwarteter Kern-Fehler ist aufgetreten."

    # KI-Fehler-Mapping
    if "rate_limit" in original_error or "quota" in original_error or "429" in original_error:
        display_msg = "AI_QUOTA_EXCEEDED"
        detail_msg = "Das Tageslimit für neuronale Berechnungen wurde erreicht oder die API-Quote ist erschöpft."

    elif "invalid_api_key" in original_error or "auth" in original_error or "401" in original_error:
        display_msg = "AUTH_KEY_INVALID"
        detail_msg = "Die Verbindung zum KI-Modul wurde verweigert. Bitte API-Schlüssel prüfen."

    elif "timeout" in original_error:
        display_msg = "CONNECTION_TIMEOUT"
        detail_msg = "Das neuronale Netz antwortet nicht rechtzeitig (Latenz-Problem)."

    # 3. Daten für dein externes Error-Log sammeln
    error_data = {
        "error_id": error_id,
        "os": platform.platform(),
        "python_version": sys.version.split()[0],
        "program_version": "2.5.0-LIGARS", # Deine Version
        "error_msg": f"[{display_msg}] {str(e)}",
        "proband_mail": "UNBEKANNT"
    }

    # 4. Probanden-Mail aus der lokalen DB holen (falls möglich)
    try:
        with get_db() as conn:
            row = conn.execute("SELECT wert FROM settings WHERE name = 'proband_mail'").fetchone()
            if row:
                error_data['proband_mail'] = row['wert']
    except:
        pass

    # 5. API-Versand an dein LIGARS-Zentral-Log
    try:
        requests.post("https://ligars.any64.de/api/fehler.php", json=error_data, timeout=5)
    except Exception as api_err:
        # Falls sogar der Versand scheitert, lokal loggen
        print(f"Kritischer Fehler beim API-Versand: {api_err}")

    # 6. Internes Logging (optional, falls du eine Logger-Klasse hast)
    try:
        LigarsLogger.log("ERR", f"CRITICAL_{display_msg} [ID: {error_id}]", str(e))
    except:
        pass

    # 7. Error-Template an User ausgeben
    return render_template('error.html',
                           code="500",
                           id=error_id,
                           msg=display_msg,
                           details=detail_msg), 500

# --- GLOBAL ERROR HANDLING ---
@app.errorhandler(Exception)
def handle_exception(e):
    # 1. EINDEUTIGE FEHLER-ID GENERIEREN
    #uuid muss importiert sein!
    error_id = str(uuid.uuid4())[:8].upper()

    # 2. SYSTEM-DATEN SAMMELN
    CURRENT_VERSION = "2.5.0" # Definiere die Version hier lokal oder global

    error_data = {
        "error_id": error_id,
        "os": platform.platform(),
        "python_version": sys.version,
        "program_version": CURRENT_VERSION,
        "error_msg": str(e),
        "error_type": type(e).__name__,
        "proband_mail": "UNBEKANNT"
    }

    # Versuche, die Mail aus der lokalen SQLite-DB zu holen
    try:
        from database_manager import get_db # Sicherstellen, dass get_db verfügbar ist
        with get_db() as conn:
            mail = conn.execute("SELECT wert FROM settings WHERE name = 'proband_mail'").fetchone()
            if mail:
                error_data['proband_mail'] = mail['wert']
    except:
        pass

    # 3. AN API SENDEN (Dein PHP-Server)
    try:
        requests.post("https://ligars.any64.de/api/fehler.php", json=error_data, timeout=5)
    except Exception as api_err:
        LigarsLogger.log("ERR", f"Fehler-API nicht erreichbar: {api_err}", error_id)

    # 4. LOKALES LOGGING
    LigarsLogger.log("ERR", f"SYSTEM_CRASH [ID: {error_id}]", f"{type(e).__name__}: {str(e)}")

    # 5. USER-REDIRECT
    return redirect(f"https://ligars.any64.de/error.php?id={error_id}")

if __name__ == '__main__':
    init_db()
    sync_vault()
    check_for_updates()
    update_equipment_db_from_server()

    # Thread sauber definieren und starten
    update_thread = threading.Thread(target=auto_update_scheduler, daemon=True)
    update_thread.start()

    sync_equipment_status()
    # --- Statistik-Sync beim Start ---
    try:
        with get_db() as conn:
            plan_row = conn.execute("SELECT wert FROM settings WHERE name = 'plan'").fetchone()
            current_plan = plan_row['wert'] if plan_row else "UNINITIALIZED"
            # Hier CURRENT_VERSION mitgeben!
            sync_stats_to_mainframe(current_plan, CURRENT_VERSION)
    except Exception as e:
        print(f"Sync-Start-Fehler: {e}")
    # ---------------------------------
    LigarsLogger.log("SYS", f"LIGARS CORE v{CURRENT_VERSION} gestartet.")
    app.run(port=8000, host='0.0.0.0', debug=True, use_reloader=False)
