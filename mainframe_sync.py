import requests
import platform
import sys
import hashlib
import uuid

# Die ID-Logik muss auch hier rein, damit die Datei eigenständig funktioniert
def get_unique_device_id():
    node = str(uuid.getnode())
    name = platform.node()
    combined = f"{node}-{name}-LIGARS-SECRET-2024"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]

def sync_stats_to_mainframe(plan_name, version): # version als Parameter hinzufügen
    url = "https://ligars.any64.de/api/stats_collector.php"
    device_hash = get_unique_device_id()

    payload = {
        "version": version,
        "os": platform.system() + " " + platform.release(),
        "plan": plan_name,
        "python_version": sys.version.split()[0],
        "device_id": device_hash
    }

    try:
        # Timeout auf 10 Sekunden hoch, falls der Server langsam ist
        response = requests.post(url, json=payload, timeout=10)

        # Prüfung der Server-Antwort
        if response.status_code == 200:
            server_feedback = response.text.strip()

            if "STAT_SYNC_SUCCESS" in server_feedback:
                print(f"\033[92m>>> [MAINFRAME]: Daten für ID {device_hash[:8]} erfolgreich gespeichert.\033[0m")
            else:
                print(f"\033[93m>>> [MAINFRAME]: Verbunden, aber Server meldet: {server_feedback}\033[0m")
        else:
            print(f"\033[91m>>> [MAINFRAME_ERR]: HTTP-Fehler {response.status_code}\033[0m")

    except Exception as e:
        print(f"\033[91m>>> [MAINFRAME_ERR]: Verbindung zum Mainframe fehlgeschlagen: {e}\033[0m")
