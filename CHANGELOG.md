# CHANGELOG

Alle bemerkenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.  
Format nach [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

---

## [2.5.5] - 2026-04-18

### Added

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

---

### Changed

#### Architektur-Optimierungen
- **Blocking-Operationen**: Asynchrone Thread-Verarbeitung für Update-Checks und Equipment-Syncs
- **Datenbank-Abfragen**: Optimierte SQL mit `JOIN`-Priorisierung statt Multiple-Select-Patterns
- **Error-Handling**: Globales Exception-Handler (`@app.errorhandler(Exception)`) mit UUID-Tracking

#### KI-Prompt-Struktur
- **Tonfall-Steuerung**: Jugendschutz-Logik mit zwei KI-Personae (sachlich vs. autoritär)
- **Token-Sicherheit**: 4-Block-Architektur für 48-Wochen-Generierung zur Vermeidung von Rate-Limit-Timeouts
- **Hardware-Injection**: Dynamische Integration von Geräte-Knowledge-Base in System-Prompt

#### API-Endpoints
- **Mobile-Token-System**: Zentrale Verwaltung von `LIGARS_UPDATE_ACCESS_77` über GET/POST-Parameter
- **CORS-Sicherheit**: `X-Requested-With`-Header-Prüfung für AJAX-Requests
- **Timeout-Konfiguration**: Differenzierte Timeouts für Update (15s), Vault-Sync (10s), Forum-API (10s)

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

- **Vulnerability-Fix**: Path-Traversal-Schutz in `@app.route('/uploads/<path:filename>')` durch `send_from_directory()`
- **Passwort-Hashing**: Verschlüsselte SMTP-Credentials zur Vermeidung von Hardcoded-Secrets
- **Session-Timeout**: Implizite Sessionablauf-Verwerfung bei Inaktivität (Browser-Default)
- **CSRF-Token**: Flask Session-basierter CSRF-Schutz auf allen POST-Operationen

---

### Known Issues

- **Fernet-Schlüssel Hardcoding**: `SECRET_KEY` und `encryption_key` sind aktuell im Quelltext sichtbar → Umbau auf Umgebungsvariablen erforderlich (v2.6)
- **Rate-Limit-Handling**: Gemini API-Kontingent nicht implementiert → Fallback auf vorherigen Befehlstext notwendig
- **Vault-Deserialisierung**: JSON-Parsing bei beschädigten `.enc`-Dateien führt zu kritischem Fehler (Recovery-Mechanismus ausstehend)
- **Forum-API-Abhängigkeit**: Blockierender POST-Request ohne Connection-Pool → Performance-Bottleneck bei vielen Setup-Operationen

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

*Diese Dokumentation wird kontinuierlich synchronisiert mit dem hauptgelagerten Repository und stellt den aktuellen Zustand des Produktionssystems dar.*