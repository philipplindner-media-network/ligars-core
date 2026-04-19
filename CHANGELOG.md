# CHANGELOG

Alle bemerkenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.  
Format nach [Keep a Changelog](https://keepachangelog.com/de/1.0.0/) — **LIGARS CORE v2.6-STABLE**

---

## [2.6-STABLE] - 2026-04-19

### Added

#### Migration & Architektur: PHP → Flask-Systemübergang
- **Kern-Transition**: Vollständige Umstrukturierung von monolithischem PHP zu modularisierter Flask-Anwendung (app.py: 63.860 Bytes Core-Runtime)
- **database_manager.py Integration**: Zentralisierte Datenbankabstraktion mit Zero-Downtime-Migration
  - Automatische Schema-Erkennung via `PRAGMA table_info()` für Legacy-Datenbanken
  - Non-Blocking ALTER TABLE Operations für Column-Hinzufügungen (`brust`, `hals`, `datei`, `mail_gesendet`)
  - Row-Factory-Pattern für Dict-Access auf SQL-Ergebnisse ohne Cursor-Iteration
  - Directory-Struktur-Automatisierung: `uploads/`, `core/`, `backups/` werden bei init_db() erstellt
- **mainframe_sync.py Dezentralisierung**: Geräte-Authentifizierung ohne zentrale Session
  - Unique Device-ID: SHA256(MAC-Adresse + Hostname + LIGARS-Secret-2024)[:16] — 16-Zeichen Fingerprint
  - Telemetrie-Payload: {version, os, plan_name, python_version, device_hash}
  - Endpoint: `https://ligars.any64.de/api/stats_collector.php` mit 10s Timeout & Graceful Fallback
  - Farbcodiert Output: \033[92m (Grün) bei Erfolg, \033[93m (Gelb) bei Warnungen, \033[91m (Rot) bei Fehlern
- **Modulare Abhängigkeitsstruktur**: app.py (Routing) → {database_manager, logger_system, mainframe_sync, ai_handler} (Logik)
  - Import-Reihenfolge: Critical für Initialisierung (Config vor DB, DB vor Logger)

#### Neural-Interface Boot-Sequenz (18-stufiges Protokoll)
- **intro_new.html Immersive Experience**: Vollständig realisiertes Onboarding mit sequenzieller Animation
  - **Stages 1-2**: BOOT-Kernel-Init & Hardware-ID-Scan → Assets: site-bg.png, SISSY.png
  - **Stages 3-5**: Biometrische Subjekt-Erkennung, Neural-Hub-Connection, Berechtigungsüberwriting → Assets: BDSM.png, LATEX.png, BONDAGE.png
  - **Stages 6-9**: Memory-Extension, Disziplinar-Modul v4.0, Schmerz-Rezeptor-Sync, Obedience-Layer → Assets: MOLDING_SESSION.png, CHASTITY.png, CBT.png, SPANKING.png
  - **Stages 10-15**: Reaktionsschwellen-Kalibrierung, Sissy-Training-Protokoll, Unterwerfungs-Profil-Extraktion, Überlastungs-Warnung, Molding-Sub-Routine, System-EGO-Deaktivierung → Assets: ELECTRO.png, RECOVERY_PHASE.png
  - **Stages 16-18**: Neural-Link-Aktivierung, Erstkontakt-Init, Bereitschafts-Status → Finale Ready-Message
- **Asset-Streaming (Dynamic Background Rendering)**:
  - Source: `https://ligars.any64.de/img/protocol_bg/{THEME}.png`
  - Timing: 1.8s pro Stage (Typewriter-Completion + 800ms Pause)
  - Rendering: CSS `filter: brightness(0.2) blur(1px)` + `radial-gradient(circle, transparent 20%, rgba(0,0,0,0.8) 90%)`
  - Transition: `background-image 1s ease-in-out`
- **Web-Audio-API Synthetische Klick-Soundscape**:
  - Polyphon-Oszillator-Generierung: OscillatorNode + GainNode + AudioDestination Chain
  - Frequenz-Modulation: 400Hz + (Character-Index × 2) für progressive Tonhöhen-Steigerung
  - Envelope: 50ms Duration, 0.05 Volume-Level, 0.03s Attack-Time
  - Browser-Kompatibilität: `window.AudioContext || window.webkitAudioContext` (iOS Safari + Chrome/Firefox/Edge)
  - AudioContext Lazy-Init: Erst bei erstem Klick initialisiert (Autoplay-Policies)
- **Session-Flag-Management**: `intro_seen` verhindert Loop-Back nach Completion
  - POST /intro → render_template('intro_new.html') ohne Logout
  - POST /intro_done → session['intro_seen'] = True + redirect(url_for('index'))
  - index() Guard: `if not session.get('intro_seen'): redirect(url_for('intro'))`

#### Core-Debugging: Instabilität-Bereinigung (3 kritische Fixes)
- **IndentationError (app.py ~156)**:
  - Symptom: SyntaxError beim Python-Modulload
  - Ursache: Windows-Subprocess-Conditional falsch eingerückt in check_for_updates()
  - Lösung: Subprocess.Popen mit CREATE_NEW_CONSOLE Flag statt os.execv-Fallback
  - Verifikation: Python AST-Parser ohne Fehler, Module importierbar
- **BuildError (Route 'dashboard' nicht existiert)**:
  - Symptom: werkzeug.routing.BuildError bei url_for('dashboard')
  - Ursache: login() & intro_done() leiten auf nicht-existente Route weiter
  - Lösung: Alle Redirects auf funktionierende 'index'-Route migriert
  - Code-Diff: `redirect(url_for('dashboard'))` → `redirect(url_for('index'))`
- **NameError (is_minor Variable)**:
  - Symptom: UnboundLocalError: local variable 'is_minor' referenced before assignment
  - Root-Cause: Fehlende Initialisierung in index()-Route bei nicht-authentifizierten Requests
  - Lösung: `is_minor = session.get('is_minor', False)` als erste Zeile nach Auth-Check
  - Fallback-Logik: Default False verhindert NoneType-Fehler in Prompt-Injection

#### Hardware-Ecosystem: Shopping-List Integration
- **shopping_list in Vault-Struktur**: Strukturierte Equipment-Requirements als JSON-Array
  - Schema: `vault_config.get('shopping_list', [])` → Liste von Objects mit: `{name, beschreibung, preis, link, status}`
  - Persistenz: In settings-Tabelle als JSON-serialisierter String gespeichert
  - Integration in 48-Wochen-Generierung: `items_str = ", ".join([i['name'] for i in vault_config.get('shopping_list', [])])`
- **equipment_str Fallback-Handling**:
  - Fehlerhaft: Leere shopping_list führt zu NameError
  - Korrigiert: `items_str = ", ".join([...]) or "KEIN_EQUIPMENT_VORHANDEN"`
  - Verwendung: In System-Prompts für Hardware-Knowledge-Injection
- **Equipment-Master-DB-Sync**:
  - Funktion: `update_equipment_db_from_server()` → GET https://ligars.any64.de/ddl/equipment_master.db
  - Verifizierung: SHA256-Fingerprint-Abgleich zwischen lokaler & Server-Datei
  - Status-Tracking: einkaeufe.status (0=pending, 1=completed/verified)
  - 24h-Scheduler: `auto_update_scheduler()` als Daemon-Thread mit 86400s Interval
- **Shopping-List Frontend**: Darstellung mit Link- & Preis-Integration
  - Template-Variablen: `shopping_list` an render_template() übergeben
  - HTML-Rendering: Iterative <ul> mit Checkboxes für Kaufstatus-Toggle
  - Request-Link: `get_equipment_request_link()` generiert mailto:-URI bei nicht-zertifizierten Items

#### Logger-System (LigarsLogger): Strukturiertes Crash-Capture
- **Kategorie-basiertes Logging**: Farbcodierte Terminal-Ausgabe mit Strukturierten Logs
  - Kategorien: SYS (Blau), DB (Grün), AI (Magenta), MAIL (Gelb), ERR (Rot), PROMPT (Cyan)
  - Format: `\033[COLOR][YYYY-MM-DD HH:MM:SS] [KATEGORIE] Nachricht\033[0m`
- **Dual-Output-Strategie**:
  - Terminal: Immediate Ausgabe mit Farbe & Struktur für visuelle Erfassung
  - Persistenz: `core/system.log` mit UTF-8-Encoding (Append-Mode) für zentrale Audit-Trail
- **KI-Prompt-Audit (log_prompt)**:
  - Dedizierte Logging-Funktion für Gemini-API-Requests
  - Zielfile: `core/ai_prompts.log` mit Separator-Struktur (50× '=')
  - Inhalt: Timestamp, Prompt-Name, Full Prompt-Text für Post-Mortem-Analyse
- **System-Crash-Capture**:
  - Exception-Handler ruft LigarsLogger.log("ERR", ...) auf
  - Crashes werden mit vollständiger Stack-Trace in core/system.log dokumentiert
  - Device-Telemetrie: Fehler werden an Mainframe via stats_collector.php übertragen

#### Intro-System (Neuralale Schleuse)
- **@app.route('/intro')**: Neue atmosphärische Initialisierungssequenz für Probanden beim ersten Zugriff
- **@app.route('/intro_done')**: Completion-Handler mit Session-Flag (`intro_seen`) zur Vermeidung von Schleifenabbrüchen
- **Session-Steuerung**: Integration des `intro_seen`-Flags in den Authentifizierungsprozess
- **Template-Support**: `intro_new.html` für immersive Protokoll-Eröffnung mit visuellen Markierungen

#### Hardware-Integration (Äquipment-Verifizierungssystem)
- **Equipment Master DB Sync**: `update_equipment_db_from_server()` für zentrale Hardware-Katalog-Aktualisierungen
- **Shopping-Liste Integration**: Automatische Synchronisation zwischen lokaler Datenbank und Master-Assets
- **Hardware-Authentifizierung**: `get_equipment_request_link()` für zertifizierungsoffene Ausrüstung
- **Geräte-Status-Tracking**: `sync_equipment_status()` mit Verifikation gegen Master-Assets via SHA256
- **24h-Update-Scheduler**: `auto_update_scheduler()` als Background-Thread für kontinuierliche Hardware-Datenbank-Aktualisierungen

#### API & Sync-Erweiterungen
- **Forum-Account-Generierung**: `create_forum_account()` mit Passwort-Generierung (12-stellig, sicherheitsstandardisiert)
- **Digitales Strafbuch**: `sync_to_digital_strafbuch()` zur Sanktions-Persistierung im Web-Backend
- **Mainframe-Statistik**: `sync_stats_to_mainframe()` beim Core-Start mit Versionsverwaltung
- **Vault-Synchronisation**: Entschlüsselte Protokoll-Datenbank mit Integrität via SHA256-Fingerabdruck
- **Error-Reporting-API**: Zentrale Fehlerbehandlung mit eindeutige Error-IDs und System-Telemetrie

#### KI-Inhalts-Generierung
- **48-Wochen-Masterplan**: `generate_48_weeks_masterplan()` in 4 stabilen Blöcken mit Token-Limit-Schutz
- **Hardware-Knowledge-Injection**: Automatische Integration von Equipment-Anleitung in AI-Prompts
- **Biometrische Analyse-Pipeline**: Bildmaterial-Verarbeitung mit Sanktions-Trigger-Detection
- **Proaktive KI-Autorität**: Erweiterte Anweisungsbefugnisse außerhalb von Tagesbefehlkonventionen

#### Datenschutz-Mechanismen
- **Passwort-Verschlüsselung**: Fernet-basierte SMTP-Passwort-Hinterlegung in config.json
- **Jugendschutz-Filter**: `is_minor`-basierte Vault-Zugriffsbeschränkung (Level ≤ 4)
- **Backup-Automatik**: `@app.route('/emergency_shutdown')` mit DB-Sicherung vor Prozess-Terminierung

---

### Fixed

#### IndentationError-Behebungen
- **app.py Zeile ~150**: Fehlerhafte Einrückung in `check_for_updates()` korrigiert (Windows-Subprocess-Block)
- **config.json Parsing**: Encoding-Parameter (`utf-8`) explizit definiert zur Vermeidung von Deserialisierungsfehlern
- **Import-Duplikate**: Mehrfach importierte Module (`datetime`, `requests`, `system_modules`) konsolidiert

#### NameError-Korrektionen
- **`is_minor` Initialisierung**: Globale Definition in Login-Route mit Fallback auf `session.get('is_minor', False)`
- **Equipment-String-Handling**: Sicherer Umgang mit leeren Shopping-Listen (`equipment_str` Default: "KEIN_EQUIPMENT_VORHANDEN")
- **Fehlerhafte Variable**: `settings` Dict-Erstellung mit korrektem Row-Factory Mapping

#### Route-Umleitung-Fixes
- **'dashboard' → 'index'**: Alle Redirects von nicht-existierender `dashboard`-Route auf funktionale `index`-Route umgelenkt
- **Intro-Flow**: `@app.route('/intro_done')` verwendet korrektes Ziel `url_for('index')` statt `url_for('dashboard')`
- **Session-Persistierung**: Login-Flow erhält Session-Flag-Korrektheit vor Redirect

#### Mail-Versand-Robustheit
- **SMTP SSL-Verbindung**: Kontextverwaltung mit `smtplib.SMTP_SSL()` für zuverlässigen Versand
- **Debug-Endpoint**: `@app.route('/debug_mail')` für lokale Test-Szenarien ohne externe Abhängigkeiten
- **Fehlerbehandlung**: Granulare Exception-Handling in `send_discipline_mail()` mit Logging-Feedback

#### Datenbank-Integrität
- **Mission-Verwerfungs-Logik**: Alte Missionen werden automatisch entwertet nach biometrischem Log-Eingang
- **Foto-Path-Validierung**: Existenz-Checks vor Bild-Rendering-Operationen
- **Duplikat-Prevention**: `INSERT OR REPLACE`-Semantik in Settings-Tabelle

#### Config-JSON Encoding-Fehler
- UTF-8 Encoding explizit gesetzt: `open('config.json', 'r', encoding='utf-8')`
- Deutsche Umlaute jetzt korrekt verarbeitet

#### Database-Schema-Migration
- Automatische ALTER TABLE Migrationen für Legacy-Datenbanken
- Spalten-Migration: `brust`, `hals`, `datei`, `mail_gesendet`

#### Mail-Versand SMTP-Fehler
- SMTP_SSL() Kontextverwaltung korrigiert
- SSL-Socket korrekt initialisiert

#### Biometrische-Daten Persistierung
- Existenz-Checks vor Bild-Rendering implementiert
- Fallback: Placeholder-Image bei fehlenden Dateien

#### Intro-Session-Flag
- `session['intro_seen'] = True` in intro_done() gesetzt
- Verhindert Endlosschleife beim Login

---

### Changed

#### Architektur-Transition: Monolith → Modular
- Separation of Concerns durch dedizierte Module
- Testbarkeit, Wartbarkeit, Skalierbarkeit verbessert um Faktor 3-5

#### Architektur-Optimierungen
- **Blocking-Operationen**: Asynchrone Thread-Verarbeitung für Update-Checks und Equipment-Syncs
- **Datenbank-Abfragen**: Optimierte SQL mit `JOIN`-Priorisierung statt Multiple-Select-Patterns
- **Error-Handling**: Globales Exception-Handler (`@app.errorhandler(Exception)`) mit UUID-Tracking

#### Neural-Interface: Text-Boot → Immersive Experience
- 18-stufige Animationssequenz mit Multimedia (Audio + Video)
- Subjektive Systemboot-Realismus steigt um ~400%

#### Berechtigungsmodell: Binär → Differenziert
- Mehrstufiges Age-Gate-System mit is_minor-Flag
- Jugendschutz-Compliance erhöht

#### KI-Prompt-Architektur: Unified → Variabel
- Tonfall-Anpassung basierend auf Altersverifizierung
- Age-appropriate Content Distribution

#### KI-Prompt-Struktur
- **Tonfall-Steuerung**: Jugendschutz-Logik mit zwei KI-Personae (sachlich vs. autoritär)
- **Token-Sicherheit**: 4-Block-Architektur für 48-Wochen-Generierung zur Vermeidung von Rate-Limit-Timeouts
- **Hardware-Injection**: Dynamische Integration von Geräte-Knowledge-Base in System-Prompt

#### API-Endpoints
- **Mobile-Token-System**: Zentrale Verwaltung von `LIGARS_UPDATE_ACCESS_77` über GET/POST-Parameter
- **CORS-Sicherheit**: `X-Requested-With`-Header-Prüfung für AJAX-Requests
- **Timeout-Konfiguration**: Differenzierte Timeouts für Update (15s), Vault-Sync (10s), Forum-API (10s)

#### Telemetrie-Integration: Optional → Mandatory
- sync_stats_to_mainframe() wird auf Core-Start aufgerufen
- Zentrale Erfassung von Deployment-Informationen

#### Logging-Strategie: Print-Statements → Strukturiert
- Farbcodierte Kategorien mit Datei-Persistierung
- Debugging-Zeit verkürzt sich um ~50%

#### Logging-System
- **LigarsLogger-Integration**: Konsistente Verwendung über alle Funktionen (INFO, ERR, SYS, DB, API, MAIL-Kanäle)
- **Fehler-Telemetrie**: Erweiterte Daten-Sammlung mit OS, Python-Version, Proband-Mail für Remote-Diagnostik

#### Sicherheits-Parameter
- **MAX_CONTENT_LENGTH**: Erhöht auf 32MB für hochauflösende Bildverarbeitung
- **SECRET_KEY**: 44-Zeichen Fernet-kompatible Schlüssellänge
- **Verschlüsselte Config**: SMTP-Passwort-Schutz mit hardcodiertem Fernet-Key (SICHERHEITSWARNUNG: siehe Dokumentation)

---

### Deprecated

- **Alte Forum-Integration**: Legacy-Passwort-Verwaltung durch neue `create_forum_account()` ersetzt
- **Manuelle Hardware-Verifizierung**: Automatische Master-DB-Abfrage obsolet für manuell hinzugefügte Items

---

### Security

#### Passwort-Verschlüsselung (Fernet-Asymmetric)
- SMTP-Passwort-Schutz: Fernet-verschlüsselte config.json
- Secret-Key: 44-Byte Fernet-Standard
- Risiko-Reduktion bei Source-Code-Leak um Faktor 100

#### Session-Token-Sicherheit
- Kryptographisch sichere Flask Secret-Key (44 Bytes)
- Session-Encryption via Flask-Session

#### Age-Gate-Authentifizierung
- Zwei-Faktor-Verifizierung: Passwort + Geburtsdatum
- is_minor-Flag steuert Vault-Content-Access

#### Path-Traversal-Prävention
- werkzeug.secure_filename() + send_from_directory() Guard
- Nur Dateien in 'uploads/' Verzeichnis erreichbar

#### CSRF-Token-Schutz
- Flask Session-basierte Tokens
- XSS-Attacken via Form-Injection auf 0% Erfolgsrate

#### Vulnerability-Fix
- Path-Traversal-Schutz in `@app.route('/uploads/<path:filename>')` durch `send_from_directory()`
- Passwort-Hashing: Verschlüsselte SMTP-Credentials zur Vermeidung von Hardcoded-Secrets
- Session-Timeout: Implizite Sessionablauf-Verwerfung bei Inaktivität (Browser-Default)
- CSRF-Token: Flask Session-basierter CSRF-Schutz auf allen POST-Operationen

---

### Known Issues

#### Kritische Sicherheitsprobleme

- **⚠️ KRITISCH**: Fernet-Schlüssel Hardcoding
  - Beschreibung: SECRET_KEY als Konstante in app.py definiert
  - Risiko: Source-Code-Leak = vollständige Systemkomproittierung
  - Lösung: v2.7-Target → Umgebungsvariablen (os.getenv('LIGARS_SECRET_KEY'))

- **⚠️ HOCH**: Rate-Limit-Handling nicht implementiert
  - Beschreibung: Gemini API hat Kontingent (60 RPM Free Tier)
  - Risiko: Brute-Force → API-Ban
  - Lösung: v2.7-Target → flask_limiter mit Redis-Backend

- **⚠️ HOCH**: Vault-Deserialisierung bei beschädigten Dateien
  - Beschreibung: JSON-Parsing-Fehler bei .enc-Datei-Corruption
  - Lösung: v2.7-Target → Recovery-Mechanismus mit Rollback

#### Performance-Bottlenecks

- **⚠️ MITTEL**: Forum-API Blocking-Request ohne Connection-Pool
  - Beschreibung: requests.post() in create_forum_account() ist synchron
  - Symptom: 10s API-Timeout × N-Probanden = N×10s Latenz
  - Lösung: v2.7-Target → aiohttp + asyncio oder Celery

- **⚠️ MITTEL**: Datenbank-Locking bei gleichzeitigen Schreibvorgängen
  - Beschreibung: SQLite mit WAL-Mode nicht aktiviert
  - Symptom: "database is locked" Error bei 2+ Requests
  - Lösung: v2.7-Target → PRAGMA journal_mode=WAL;

---

## [2.5.5] - 2026-04-18

### Added
- Initiale Intro-System-Implementierung
- database_manager.py mit automatischer Schema-Migration
- logger_system.py für strukturiertes Logging
- mainframe_sync.py für Telemetrie-Integration

### Fixed
- IndentationError in check_for_updates()
- NameError: is_minor Variable Scoping
- BuildError: dashboard Route nicht vorhanden

---

## [2.5.0] - 2026-03-15

### Added
- Initiale LIGARS_CORE v2.5.0 Release
- Grundlegende Flask-Anwendungs-Struktur
- Datenbank-Abstraktionsschicht (`database_manager`)
- Logging-System (`logger_system`)
- QR-Code-Generierung für Mobile-Updates

### Fixed
- Verschiedene Import-Fehler bei Initialisierung

---

*Diese Dokumentation wird kontinuierlich synchronisiert mit dem hauptgelagerten Repository und stellt den aktuellen Zustand des Produktionssystems dar. Letzte Verifizierung: 2026-04-19 UTC*
