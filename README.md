# LIGARS-CORE: AI Simulation Framework

**Eine Single-App-Lösung für KI-gestützte Simulationen und Rollenspiel-Protokollierung.**

---

## 🚀 Quick Start

Installation und Start in 3 einfachen Schritten:

```bash
# 1. Installation
./install_ligars.sh

# 2. Gemini Key einbauen
nano config.json -> "GEMINI_API_KEY": "-KEY Hier Rein-", Ändnern.

# 3. System starten
python3 app.py
```

Das Web-Interface ist danach verfügbar unter: **http://127.0.0.1:8090**

---

## 📋 Übersicht

**LIGARS-CORE** ist ein experimentelles KI-Simulations-Framework für Persönlichkeitsprofile und kreative Rollenspiel-Protokolle. Das System läuft vollständig lokal und benötigt keine externe Infrastruktur.

### Features

- ✅ **Web-Dashboard**: Lokales Interface unter `http://127.0.0.1:8090`
- ✅ **Lokale Speicherung**: Alle Daten werden lokal gespeichert
- ✅ **AES-256 Verschlüsselung**: Sichere Speicherung von SMTP-Passwörtern
- ✅ **Einfache Bedienung**: Konfigurieren → Starten → Nutzen
- ✅ **Google Generative AI Integration**: Powered by Gemini

---

## 🔒 Sicherheit


### Konfiguration

Die `config.json` enthält alle Einstellungen. **Speichern Sie niemals API-Keys oder Passwörter im Repository!** Nutzen Sie stattdessen Umgebungsvariablen.

---

## 📦 Installation

### Automatisierte Installation (Linux)

```bash
chmod +x install_ligars.sh
./install_ligars.sh
```

Das Skript installiert automatisch:
- Python 3.8+ (falls nicht vorhanden)
- Alle benötigten Abhängigkeiten (Flask, Requests, Google Generative AI, Cryptography)
- Config-Datei (basierend auf `config.json.example`)
- Virtual Environment

---

## ⚙️ Konfiguration

Nach der Installation bearbeiten Sie `config.json`:

```json
{
    "SMTP_SERVER": "mail.lindner-leipzig.de",
    "SMTP_PORT": 465,
    "SMTP_USER": "ligars-core@lindner-leipzig.eu",
    "SMTP_PASS": "gAAAAABp2inKi7IrUnKTp9q7v123cmQfslXGE2qo-cjGOxBqr9ctdn5_26qPwsUMrsZBGqv-UWjzr1YOaM0ES2XBQIIxjJRcJQ==",
    "MAIL_SENDER": "ligars-core@lindner-leipzig.eu",
    "GEMINI_API_KEY": "-KEY Hier Rein-",
    "WEB_PASSWORD": "Sissy2026"
}

```

Die Vorlage finden Sie in `config.json.example`.

---

## ⚠️ Disclaimer

**WICHTIG**: LIGARS-CORE ist ein experimentelles System. 

Die Nutzung erfolgt auf **EIGENE GEFAHR**. Der Entwickler übernimmt **KEINE HAFTUNG** für:
- Datenverlust oder Datenkorruption
- Fehlfunktionen des Systems
- Sicherheitslücken oder unbefugte Zugriffe
- Schäden durch Missbrauch oder unsachgemäße Nutzung

Nutzer sind selbst verantwortlich für die Einhaltung aller geltenden Gesetze und Richtlinien.

---

## 📞 Support

Für Fragen, Probleme oder Vorschläge:

- **Website**: [https://ligars.any64.de/](https://ligars.any64.de/)
- **E-Mail**: [ligars-core@lindner-leipzig.de](mailto:ligars-core@lindner-leipzig.de)

---

## 📝 Lizenz

MIT License - Siehe LICENSE Datei für Details.

---

**LIGARS-CORE v2.5.0** | Experimentelles System | Klinisch-technologische Architektur
