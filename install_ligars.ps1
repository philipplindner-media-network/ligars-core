# LIGARS_CORE v2.5 - WINDOWS_INSTALLER
Clear-Host
Write-Host "#########################################################" -ForegroundColor Cyan
Write-Host "#   LIGARS_CORE // WINDOWS-SYSTEM-INITIALISIERUNG       #" -ForegroundColor Cyan
Write-Host "#########################################################" -ForegroundColor Cyan

# 1. PRÜFE AUF PYTHON
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "> Python nicht gefunden. Bitte installiere Python 3.10+ von python.org" -ForegroundColor Red
    exit
}

# 2. VENV ERSTELLEN
Write-Host "> Erstelle isolierte Umgebung (VENV)..." -ForegroundColor Green
if (Test-Path "venv") { Remove-Item -Recurse -Force "venv" }
python -m venv venv

# 3. AKTIVIERUNG & INSTALLATION
Write-Host "> Installiere Module in VENV..." -ForegroundColor Green
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\pip.exe install flask google-generativeai cryptography requests qrcode[pil] pillow

# 4. CONFIGURATION
$CONFIG_FILE = "config.json"
if (!(Test-Path $CONFIG_FILE)) {
    '{ "SMTP_SERVER": "mail.lindner-leipzig.de", "WEB_PASSWORD": "Sissy2026" }' | Out-File -FilePath $CONFIG_FILE -Encoding utf8
}

$apikey = Read-Host "GEMINI_API_KEY EINGEBEN"
$config = Get-Content $CONFIG_FILE | ConvertFrom-Json
$config.GEMINI_API_KEY = $apikey
$config | ConvertTo-Json | Out-File -FilePath $CONFIG_FILE -Encoding utf8

Write-Host "> Installation abgeschlossen." -ForegroundColor Green
Write-Host "> Starte Anwendung mit: .\venv\Scripts\python.exe app.py" -ForegroundColor Yellow

# 5. START-SKRIPT GENERIEREN (Kiosk-Modus für Windows)
Write-Host "> Generiere start_ligars.ps1..." -ForegroundColor Green

$START_SCRIPT = @"
# LIGARS_CORE // START-SEQUENZ
# Modus: Server + Browser-Kiosk

# 1. Server im Hintergrund starten
Write-Host "Starte Flask-Server..." -ForegroundColor Cyan
Start-Process .\venv\Scripts\python.exe -ArgumentList "app.py" -WindowStyle Hidden

# 2. Kurze Pause für Server-Initialisierung
Start-Sleep -Seconds 5

# 3. Browser im Kiosk-Modus
`$url = "http://127.0.0.1:8000"
Write-Host "Starte Browser..." -ForegroundColor Cyan
if (Get-Command "chrome.exe" -ErrorAction SilentlyContinue) {
    & "chrome.exe" --app=`$url --start-fullscreen --no-first-run
} else {
    Start-Process msedge -ArgumentList "--app=`$url --start-fullscreen"
}
"@

$START_SCRIPT | Out-File -FilePath "start_ligars.ps1" -Encoding utf8

Write-Host "#########################################################" -ForegroundColor Cyan
Write-Host "#  INSTALLATION ABGESCHLOSSEN                           #" -ForegroundColor Cyan
Write-Host "#  STARTE DAS SYSTEM MIT: .\start_ligars.ps1            #" -ForegroundColor Cyan
Write-Host "#########################################################" -ForegroundColor Cyan
