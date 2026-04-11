#!/bin/bash

# LIGARS_CORE v2.5 - START-SEQUENZ
# Modus: Kiosk / Fullscreen-Interface

# 1. VIRTUELLE UMGEBUNG AKTIVIEREN
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo -e "\033[0;31m[FEHLER] VENV nicht gefunden. Bitte install_ligars.sh zuerst ausführen.\033[0m"
    exit 1
fi

# 2. FLASK-SERVER IM HINTERGRUND STARTEN
echo -e "\033[0;32m> Starte LIGARS_CORE Kern-Prozess...\033[0m"
python3 app.py &

# Kurze Pause, damit der Server Zeit zum Hochfahren hat
sleep 3

# 3. BROWSER IM VOLLBILDMODUS STARTEN
URL="http://127.0.0.1:8000"

echo -e "\033[0;32m> Initialisiere Visual-Interface (Kiosk-Modus)...\033[0m"

if command -v google-chrome &> /dev/null; then
    google-chrome --app=$URL --start-fullscreen --no-first-run
elif command -v chromium-browser &> /dev/null; then
    chromium-browser --app=$URL --start-fullscreen --no-first-run
elif command -v firefox &> /dev/null; then
    firefox --new-window $URL --fullscreen
else
    echo -e "\033[0;33m[WARNUNG] Kein Standard-Browser gefunden. Öffne URL manuell: $URL\033[0m"
fi

# Wenn der Browser geschlossen wird, beende auch den Flask-Server
trap "kill $!" EXIT
