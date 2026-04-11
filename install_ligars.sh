#!/bin/bash
# LIGARS_CORE v2.5 - UNIVERSAL_INSTALLER (FIXED & KIOSK)

clear
echo -e "\033[0;36m#########################################################"
echo "#   LIGARS_CORE // SYSTEM-INITIALISIERUNG               #"
echo "#########################################################\033[0m"

# 1. PAKETMANAGER LOGIK
install_pkg() {
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -y && sudo apt-get install -y python3-pip python3-venv python3-full
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3-pip python3-virtualenv
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm python-pip
    fi
}

# 2. SYSTEM-VORAUSSETZUNGEN
echo -e "\033[0;32m> Prüfe System-Abhängigkeiten...\033[0m"
install_pkg

# 3. VENV ERSTELLEN & REPARIEREN
echo -e "\033[0;32m> Erstelle isolierte Umgebung (VENV)...\033[0m"
rm -rf venv
python3 -m venv venv

# 4. AKTIVIERUNG & INSTALLATION
# Wir nutzen '.' für maximale Shell-Kompatibilität
. venv/bin/activate || { echo "FEHLER: VENV konnte nicht aktiviert werden."; exit 1; }

echo -e "\033[0;32m> Installiere Module in VENV...\033[0m"
python3 -m pip install --upgrade pip
python3 -m pip install flask google-generativeai cryptography requests qrcode[pil] pillow

# 5. CONFIGURATION
CONFIG_FILE="config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo '{"SMTP_SERVER": "mail.lindner-leipzig.de", "WEB_PASSWORD": "Sissy2026"}' > $CONFIG_FILE
fi

echo -e "\033[0;36m"
read -p "GEMINI_API_KEY EINGEBEN: " apikey
echo -e "\033[0m"

python3 - <<EOF
import json
with open('$CONFIG_FILE', 'r') as f:
    data = json.load(f)
data['GEMINI_API_KEY'] = '$apikey'
with open('$CONFIG_FILE', 'w') as f:
    json.dump(data, f, indent=4)
EOF

# 6. KIOSK-STARTER ERSTELLEN
cat <<EOF > start_ligars.sh
#!/bin/bash
cd "\$(dirname "\$0")"
. venv/bin/activate
echo "> LIGARS_CORE startet im Kiosk-Modus..."
python3 app.py &
sleep 5
URL="http://127.0.0.1:8000"
if command -v google-chrome &> /dev/null; then
    google-chrome --app=\$URL --start-fullscreen
elif command -v chromium-browser &> /dev/null; then
    chromium-browser --app=\$URL --start-fullscreen
else
    xdg-open \$URL
fi
EOF
chmod +x start_ligars.sh

echo -e "\033[0;32m> INSTALLATION ABGESCHLOSSEN. Starten mit: ./start_ligars.sh\033[0m"
