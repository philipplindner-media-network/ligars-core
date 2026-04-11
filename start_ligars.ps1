# LIGARS Windows Startup Script v2.0
Clear-Host
$SIGN = @"
  _      _____ _____          _____   _____ 
 | |    |_   _/ ____|   /\   |  __ \ / ____|
 | |      | || |  __   /  \  | |__) | (___  
 | |      | || | |_ | / /\ \ |  _  / \___ \ 
 | |____ _| || |__| |/ ____ \| | \ \ ____) |
 |______|_____\_____/_/    \_\_|  \_\_____/ 
"@
Write-Host $SIGN -ForegroundColor Cyan
Write-Host "`n [SYSTEM] Initialisiere Boot-Sequenz..." -ForegroundColor Gray

# 1. API-KEY CHECK
$appContent = Get-Content "app.py" -Raw
$placeholder = "HIRE_DIE_API_KEY"

if ($appContent -match $placeholder -or $appContent -match 'api_key=""') {
    Write-Host "`n [!!!] KRITISCHER FEHLER: KEIN API-KEY GEFUNDEN!" -ForegroundColor Red
    Write-Host " [INFO] Du musst deinen Google Gemini API-Key in der app.py eintragen.`n" -ForegroundColor Yellow
    
    if (Test-Path "ANLEITUNG.txt") {
        Write-Host " --- AUSZUG AUS ANLEITUNG.TXT ---" -ForegroundColor Gray
        Get-Content "ANLEITUNG.txt" | Select-Object -First 10
    }
    Write-Host "`n [Drücke eine Taste zum Beenden]"
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit
}

# 2. Python & Module Check
Write-Host " [SYSTEM] Prüfe Abhängigkeiten..." -ForegroundColor Gray
python -m pip install flask requests google-generativeai pillow cryptography -q

# 3. Server starten
Write-Host " [SYSTEM] Starte Core-Engine..." -ForegroundColor Magenta
Start-Process python -ArgumentList "app.py" -WindowStyle Hidden

# 4. Warten auf Port 8000
while (!(Test-NetConnection -ComputerName 127.0.0.1 -Port 8000 -WarningAction SilentlyContinue).TcpTestSucceeded) {
    Start-Sleep -Seconds 1
}

Write-Host " [SYSTEM] Zugriff gewährt. Interface wird geladen." -ForegroundColor Green
Start-Process "http://127.0.0.1:8000"
