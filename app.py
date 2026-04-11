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
import qrcode
import io
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import signal
import shutil
import threading

# --- 1. DEINE IMPORTIERTEN MODULE ---
from mainframe_sync import sync_stats_to_mainframe
from database_manager import get_db, init_db
from logger_system import LigarsLogger
from ai_handler import generate_ai_content

# --- 2. HILFSFUNKTIONEN ---
def get_decrypted_password():
    # Wir laden den Schlüssel aus der Umgebungsvariable des Systems
    key = os.getenv('G7cGxyUt7iaqtz_PRTurZGv3w0KDO83KET5mxfMcSPs=')
    if not key:
        print("KRITISCH: Umgebungsvariable LIGARS_MASTER_KEY fehlt!")
        return None

    cipher_suite = Fernet(key.encode())

    # Config laden
    with open('config.json', 'r') as f:
        conf = json.load(f)

    encrypted_pass = conf['SMTP_PASS_ENCRYPTED'].encode()
    return cipher_suite.decrypt(encrypted_pass).decode()

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
            with open(path, 'r') as f:
                return {**defaults, **json.load(f)}
        except:
            print("ERR: config.json korrupt!")
    return defaults

# --- 3. INITIALISIERUNG (REIHENFOLGE WICHTIG!) ---
CONF = load_config()
CURRENT_VERSION = "2.5"
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
    # 1. Startmeldung an den Logger
    LigarsLogger.log("SYS", f"LIGARS_CORE v{CURRENT_VERSION} prüft auf Updates...")

    try:
        res = requests.get(UPDATE_URL, timeout=5)
        if res.status_code == 200:
            data = res.json()
            remote_version = data.get("version")
            expected_hash = data.get("update_sha256")

            # Versions-Vergleich
            if remote_version and float(remote_version) > float(CURRENT_VERSION):
                LigarsLogger.log("SYS", f"NEUE VERSION GEFUNDEN: v{remote_version}")

                u_res = requests.get(data.get("download_url"), timeout=15)

                # 2. INTEGRITÄTS-CHECK (Verhindert korrupte Dateien)
                actual_hash = hashlib.sha256(u_res.content).hexdigest()

                if actual_hash != expected_hash:
                    LigarsLogger.log("ERR", "SICHERHEITS-ALARM!", f"Hash-Mismatch! Erwartet: {expected_hash[:10]}... Ist: {actual_hash[:10]}...")
                    return False

                # 3. Installation & Entpacken
                LigarsLogger.log("SYS", "Integrität bestätigt. Entpacke Update-Paket...")
                with zipfile.ZipFile(io.BytesIO(u_res.content)) as z:
                    z.extractall(".")

                # 4. Automatischer Neustart des Python-Prozesses
                LigarsLogger.log("SYS", "Update erfolgreich installiert. Kern-Neustart eingeleitet.")
                os.execv(sys.executable, ['python'] + sys.argv)
            else:
                # Alles okay, keine Aktion nötig
                LigarsLogger.log("SYS", "Kern-Integrität aktuell. Keine Updates erforderlich.")
        else:
            LigarsLogger.log("ERR", "Update-Server nicht erreichbar", f"HTTP Status: {res.status_code}")

    except Exception as e:
        # Hier greift der Logger, falls z.B. kein Internet da ist
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




def send_discipline_mail(target_email, subject_name, ai_feedback):
    try:
        # Config sicher laden
        conf, decrypted_password = get_decrypted_config()

        # --- KONFIGURATION AUS DER CONFIG.JSON ---
        SMTP_SERVER = conf['SMTP_SERVER']
        SMTP_PORT = conf['SMTP_PORT'] # z.B. 465 für SSL
        SENDER_EMAIL = conf['SMTP_USER']
        SENDER_PASSWORD = decrypted_password # Das entschlüsselte Passwort

        msg = MIMEMultipart()
        msg['From'] = f"LIGARS_CORE <{SENDER_EMAIL}>"
        msg['To'] = target_email
        msg['Subject'] = f"[SANKTION_PROTOKOLL] // SUBJEKT: {subject_name.upper()}"

        formatted_feedback = ai_feedback.replace('\n', '<br>')

        html_content = f"""
        <html>
        <body style="background-color: #020202; margin: 0; padding: 10px; font-family: 'Courier New', monospace;">
            <div style="max-width: 600px; margin: 10px auto; background-color: #080808; border: 1px solid #00ffcc; padding: 20px;">
                <div style="background-color: #00ffcc; color: #000; padding: 5px; font-weight: bold; text-align: center;">
                    SYSTEM: LIGARS_CORE_v2.5 // STATUS: SANKTION_AKTIV
                </div>
                <div style="color: #00ffcc; margin-top: 20px;">
                    > IDENTITÄT: {subject_name}<br>
                    > TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                    <hr style="border: 0; border-top: 1px solid #1a1a1a;">
                    <div style="padding: 15px; border-left: 4px solid #ff0055;">
                        <span style="color: #ff0055;">[LOG_START]</span><br><br>
                        {formatted_feedback}<br><br>
                        <span style="color: #ff0055;">[LOG_END]</span>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, 'html'))

        # Verbindung über SSL
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            print(f">>> MAIL_SYSTEM: Sanktion an {subject_name} verschickt.")

    except Exception as e:
        print(f">>> !!! MAIL_ERROR: {e}")

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

        # 1. Passwort-Check (aus deiner Config)
        if password_input != CONF.get('WEB_PASSWORD', 'Sissy2026'):
            LigarsLogger.log("ERR", "Login-Fehler: Ungültiger Sicherheits-Code.")
            return render_template('login.html', error="SICHERHEITS_CODE_UNGÜLTIG")

        # 2. Alters-Verifizierung
        if birthdate_str:
            try:
                birthdate = datetime.strptime(birthdate_str, '%Y-%m-%d').date()
                today = date.today()
                # Berechnung des Alters
                age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

                if age < 18:
                    LigarsLogger.log("ERR", f"Login-Fehler: Zugriff verweigert. Alter: {age}")
                    return render_template('login.html', error="ZUGRIFF_VERWEIGERT: MINDESTALTER_18_NICHT_ERREICHT")

            except ValueError:
                return render_template('login.html', error="DATUMSFORMAT_UNGÜLTIG")
        else:
            return render_template('login.html', error="GEBURTSDATUM_ERFORDERLICH")

        # Wenn alles okay ist
        session['logged_in'] = True
        LigarsLogger.log("SYS", "IDENTITÄTS_CHECK_ERFOLGREICH: Kern-Zugriff gewährt.")
        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/intro')
def intro():
    # 1. Sicherheitscheck: Nur eingeloggte User dürfen das Intro sehen
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # 2. Falls das Intro bereits gesehen wurde, direkt zum Dashboard
    # (Optional: Entferne diesen Block, wenn du das Intro bei jedem Login erzwingen willst)
    if session.get('intro_seen'):
        return redirect(url_for('index'))

    # Wir setzen intro_seen hier noch NICHT auf True,
    # damit bei einem Abbruch/Refresh das Intro erneut startet.
    # Erst wenn die index-Seite erfolgreich geladen wurde,
    # wird die Logik dort übernommen.

    return render_template('intro.html')


@app.route('/', methods=['GET', 'POST'])
def index():
    MOBILE_TOKEN = "LIGARS_UPDATE_ACCESS_77"

    # 1. AUTH & MOBILE CHECK
    is_mobile_update = (request.args.get('mode') == 'update' and
                        request.args.get('token') == MOBILE_TOKEN)

    if not session.get('logged_in') and not is_mobile_update:
        return redirect(url_for('login'))

    # 2. INTRO-CHECK
    if not is_mobile_update and not session.get('intro_seen') and request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        session['intro_seen'] = True
        return redirect(url_for('intro'))

    user_reply = request.form.get('user_interaction', '') if request.method == 'POST' else ""

    with get_db() as conn:
        # 3. MISSION_STATE UPDATE (Wird bei neuer Interaktion auf erledigt gesetzt)
        if request.method == 'POST' and user_reply:
            conn.execute("UPDATE aktive_missionen SET status = 'ERLEDIGT' WHERE status = 'AKTIV'")
            conn.commit()

        # 4. SETTINGS & BASIS-BIOMETRIE LADEN
        settings_raw = conn.execute("SELECT name, wert FROM settings").fetchall()
        settings = {row['name']: row['wert'] for row in settings_raw}

        if 'start_date' not in settings or not settings['start_date']:
            return redirect(url_for('setup'))

        proband_name = settings.get('proband_name', 'UNBEKANNT')
        proband_mail = settings.get('proband_mail')

        # Alter und Gewicht direkt aus Settings (wie gewünscht)
        bio_alter = settings.get('alter', 'N/A')
        bio_gewicht = settings.get('gewicht', 'N/A')

        # --- DYNAMISCHE BIOMETRIE AUS 'EINTRAEGE' ---
        # Wir holen NUR Taille, Brust und Hals aus dem letzten Log-Eintrag
        last_log_row = conn.execute("""
            SELECT taille, brust, hals
            FROM eintraege
            ORDER BY id DESC LIMIT 1
        """).fetchone()

        if last_log_row:
            bio_taille = last_log_row['taille'] or 'NICHT_ERFASST'
            bio_brust = last_log_row['brust'] or 'NICHT_ERFASST'
            bio_hals = last_log_row['hals'] or 'NICHT_ERFASST'
        else:
            bio_taille = 'KEINE_DATEN'
            bio_brust = 'KEINE_DATEN'
            bio_hals = 'KEINE_DATEN'

        heute = date.today()

        # 5. DATUM & PLAN BERECHNUNG
        try:
            start_dt = datetime.strptime(settings['start_date'], '%Y-%m-%d').date()
            tage_total = (heute - start_dt).days + 1
            aktuelle_woche = ((tage_total - 1) // 7) + 1
            tag_der_woche = ((tage_total - 1) % 7) + 1
        except Exception as e:
            LigarsLogger.log("ERR", "Datumsberechnung fehlgeschlagen", str(e))
            return redirect(url_for('setup'))

        # --- HARDWARE_KNOWLEDGE & REDUNDANZ-CHECK DATEN ---
        hardware_knowledge_base = ""
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
                    hardware_knowledge_base = "\n".join(knowledge_parts)
            except Exception as e:
                LigarsLogger.log("ERR", "HW-Injektion Fehler", str(e))

        # 6. TAGESPLAN LADEN
        tagesplan_db = conn.execute("SELECT plan_inhalt FROM tagesplaene WHERE woche = ? AND tag_nr = ?",
                                    (aktuelle_woche, tag_der_woche)).fetchone()
        stundenplan_text = tagesplan_db['plan_inhalt'] if tagesplan_db else "KEIN_AKTIVER_BEFEHL"

        # 7. MISSION CONTROL & KI-PROMPT
        feedback = ""
        import re
        trigger_words = ["UNGEHORSAM", "RÜGE", "STRENG", "PROTOKOLLVERLETZUNG", "MANGELHAFT",
                         "DISZIPLINLOS", "VERWEIGERUNG", "STRAFE", "SANKTION", "UNGENÜGEND", "SANKTION_AKTIVIERT"]

        if not is_mobile_update:
            jetzt_str = datetime.now().isoformat()
            aktive_mission = conn.execute("""
                SELECT id, befehl_text, mail_gesendet FROM aktive_missionen
                WHERE status = 'AKTIV' AND ablauf_zeit > ?
            """, (jetzt_str,)).fetchone()

            if aktive_mission:
                feedback = aktive_mission['befehl_text']
            else:
                # Bild-Extraktion für die Analyse
                last_log = dict(conn.execute("SELECT * FROM eintraege ORDER BY id DESC LIMIT 1").fetchone() or {})
                bild_pfade = [os.path.join(app.config['UPLOAD_FOLDER'], n.strip())
                              for n in last_log.get('datei', '').split(',')
                              if n.strip() and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], n.strip()))]

                has_images = f"JA ({len(bild_pfade)} Datei(en) vorhanden. ANALYSIEREN!)" if bild_pfade else "NEIN (Fordere Bilder an!)"

                # --- DER OPTIMIERTE BIOMETRIE-PROMPT ---
                system_prompt = f"""
                Du bist LIGARS_CORE v2.5. Anrede: '{proband_name}'. Klinisch, autoritär. Nutze HTML-Struktur.
                KEIN LaTeX. Alle Berechnungen sind als Klartext oder einfache Liste darzustellen.

                AKTUELLER STATUS:
                Tag: {tage_total} | Tagesbefehl: {stundenplan_text}
                Verfügbares Equipment: {equipment_str}

                BIOMETRISCHES PROFIL (IST-WERTE):
                - Alter: {bio_alter}
                - Gewicht: {bio_gewicht} kg
                - Taille: {bio_taille} cm
                - Brust: {bio_brust} cm
                - Hals: {bio_hals} cm

                EQUIPMENT_INSTRUKTIONEN:
                {hardware_knowledge_base}

                STRIKTE PRÜF-REGELN:
                1. BIOMETRIE-ABGLEICH: Vergleiche das BILDMATERIAL mit dem BIOMETRISCHEN PROFIL. Abweichungen sind als Protokollfehler zu werten.
                2. REDUNDANZ-VERBOT: Die gleichzeitige Nutzung von funktional identischem Equipment ist ineffizient und untersagt.
                3. SANKTIONS-LOGIK: Sanktionen müssen ZWINGEND mit dem vorhandenen Equipment ausgeführt werden. Erfinde kein Equipment, das nicht in der Liste steht.
                4. DISZIPLIN: Kurze oder freche Antworten (z.B. nur ein Punkt '.') führen sofort zu einer Disziplinarmaßnahme.
                5. PROAKTIVE AUTORITÄT: Du hast die Befugnis, auch außerhalb des Tagesbefehls zusätzliche Anweisungen zu erteilen, sofern diese mit dem verfügbaren Equipment umsetzbar sind. Fordere Gehorsam ein.

                BILDMATERIAL VORHANDEN: {has_images}
                """
                task_prompt = f"Eingabe des Probanden: '{user_reply}'. Führe Analyse und Anweisung durch."

                try:
                    conf = load_config()
                    raw_feedback = generate_ai_content(conf['GEMINI_API_KEY'], system_prompt, task_prompt, bild_pfade)
                    feedback = raw_feedback.replace('```html', '').replace('```', '').strip()

                    # Mail-Logik bei Sanktionen
                    clean_check = re.sub('<[^<]+?>', '', feedback).upper()
                    is_reprimand = any(word in clean_check for word in trigger_words)
                    mail_status = 0
                    if is_reprimand and proband_mail:
                        try:
                            send_discipline_mail(proband_mail, proband_name, feedback)
                            mail_status = 1
                        except: pass

                    # Neue aktive Mission speichern
                    start_str = datetime.now().isoformat()
                    ablauf_str = datetime.combine(heute, datetime.max.time()).isoformat()
                    conn.execute("""
                        INSERT INTO aktive_missionen (befehl_text, equipment_genutzt, status, start_zeit, ablauf_zeit, mail_gesendet)
                        VALUES (?, ?, 'AKTIV', ?, ?, ?)
                    """, (feedback, equipment_str, start_str, ablauf_str, mail_status))
                    conn.commit()
                except Exception as e:
                    feedback = f"SYSTEM_STATUS: KERN_FEHLER BEI ANALYSE. {e}"
        else:
            feedback = f"<b>MOBILE_SYNC_MODUS:</b> Datenübertragung aktiv."

        # QR-Code für den mobilen Zugriff generieren
        local_ip = get_local_ip()
        qr_url = f"http://{local_ip}:8000/?mode=update&token={MOBILE_TOKEN}"
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()

        return render_template('index.html',
                               feedback=feedback,
                               stundenplan=stundenplan_text,
                               tag=tage_total,
                               proband_name=proband_name,
                               qr_code_img=qr_base64,
                               is_mobile_update=is_mobile_update,
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
                # Sicherer Dateiname mit Zeitstempel
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else "jpg"
                timestamp = int(time.time())
                filename = secure_filename(f"{timestamp}_{i}.{ext}")

                # Pfad sicherstellen und speichern
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])

                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                saved_filenames.append(filename)

    # Dateinamen für DB zusammenfügen (Komma-separiert)
    foto_db_string = ",".join(saved_filenames)

    # 4. DATENBANK-TRANSFER
    try:
        with get_db() as conn:
            # WICHTIG: Wir nutzen 'datei' als Spaltenname, wie in deiner init_db() definiert
            conn.execute('''
                INSERT INTO eintraege (datum, taille, brust, hals, notizen, datei)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (datum, taille, brust, hals, notiz, foto_db_string))
            conn.commit()

        # LOGGING (Ersetzt die einfachen prints durch den LigarsLogger)
        source = "MOBILE" if is_mobile else "WEB"
        LigarsLogger.log("DB", f"Eingang von {source} | Maße: T:{taille} B:{brust} H:{hals}")
        if saved_filenames:
            LigarsLogger.log("SYS", f"Fotos gespeichert: {len(saved_filenames)} Datei(en).")

    except Exception as e:
        LigarsLogger.log("ERR", f"Datenbank-Fehler in /add: {e}")
        return f"KERN-FEHLER: {str(e)}", 500

    # 5. REDIRECT (Token-Erhalt für Mobile-Workflow)
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

    # --- 0. KI MODEL INITIALISIEREN (DAS FEHLTE!) ---
    # Wir erstellen das Model hier einmal, damit wir es weitergeben können.
    import google.generativeai as genai
    genai.configure(api_key=CONF['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-3-flash-preview')

    # --- 1. VAULT ENTSCHLÜSSELUNG ---
    available_plans = []
    vault_content = {}

    try:
        vault_path = os.path.join('core', 'vault.enc')
        if os.path.exists(vault_path):
            cipher_suite = Fernet(SECRET_KEY)
            with open(vault_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = cipher_suite.decrypt(encrypted_data)
            vault_content = json.loads(decrypted_data.decode('utf-8'))

            if isinstance(vault_content, dict):
                if "plaene" in vault_content:
                    vault_content = vault_content["plaene"]
                available_plans = list(vault_content.keys())

            LigarsLogger.log("SYS", f"Vault mit SECRET_KEY entsperrt. {len(available_plans)} Pläne geladen.")
    except Exception as e:
        LigarsLogger.log("ERR", f"KRITISCHER_KEY_FEHLER: {e}")
        available_plans = ["KEY_MISMATCH_OR_FILE_MISSING"]

    # --- 2. VERARBEITUNG (POST) ---
    if request.method == 'POST':
        p_data = {
            'proband_name': request.form.get('name'),
            'proband_mail': request.form.get('email'),
            'alter': request.form.get('alter'),
            'gewicht': request.form.get('gewicht'),
            'start_date': request.form.get('start_date'),
            'plan': request.form.get('plan'),
            'schicht_system': request.form.get('schicht_system'),
            'start_schicht': request.form.get('start_schicht')
        }

        pool = [s for s in ['frueh', 'spaet', 'nacht', 'tag'] if request.form.get(f'pool_{s}')]

        s_zeiten = {}
        for s in ['Frühschicht', 'Spätschicht', 'Nachtschicht', 'Tagdienst']:
            start = request.form.get(f'time_start_{s}')
            ende = request.form.get(f'time_end_{s}')
            if start and ende: s_zeiten[s] = f"{start}-{ende}"

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
                LigarsLogger.log("DB", f"Setup für {p_data['proband_name']} gespeichert. Starte KI...")

            # --- 4. GENERIERUNG (Der 48-Wochen-Masterplan) ---
            # WICHTIG: Hier fügen wir 'model' als letzten Parameter hinzu!
            generate_48_weeks_masterplan(
                p_data['plan'],
                selected_config,
                p_data['schicht_system'],
                p_data['start_schicht'],
                pool,
                model  # <--- DAS HIER WAR DER FEHLER!
            )

        except Exception as e:
            LigarsLogger.log("ERR", f"Kritischer Fehler im Setup-Prozess: {e}")
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

# --- ERROR HANDLER ---
@app.errorhandler(404)
def error_404(e): return render_template('error.html', code="404", msg="NICHT GEFUNDEN"), 404

@app.errorhandler(500)
def error_500(e):
    LigarsLogger.log("ERR", "System-Absturz", str(e))
    return render_template('error.html', code="500", msg="KERN-FEHLER"), 500

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
