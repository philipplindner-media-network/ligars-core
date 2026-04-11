import datetime
import os

class LigarsLogger:
    @staticmethod
    def log(category, message, data=None):
        # Farben für das Terminal
        colors = {
            "SYS": "\033[94m",  # Blau
            "DB": "\033[92m",   # Grün
            "AI": "\033[95m",   # Magenta
            "MAIL": "\033[93m", # Gelb
            "ERR": "\033[91m",  # Rot
            "PROMPT": "\033[96m", # Cyan (für KI Prompts)
            "END": "\033[0m"
        }

        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        col = colors.get(category, colors["END"])
        reset = colors["END"]

        # 1. Terminal Ausgabe
        output = f"{col}[{ts}] [{category}] {message}{reset}"
        if data:
            output += f"\n   -> DATA: {data}"
        print(output)

        # 2. In Datei schreiben (Allgemeiner Log)
        with open("core/system.log", "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [{category}] {message} {f'| Data: {data}' if data else ''}\n")

    @staticmethod
    def log_prompt(prompt_name, content):
        """ Spezielle Funktion nur für KI-Prompts in separate Datei """
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = "core/ai_prompts.log"

        # Terminal-Info, dass ein Prompt gesendet wurde (kurz)
        LigarsLogger.log("PROMPT", f"KI-Anfrage gesendet: {prompt_name}")

        # Ausführlicher Inhalt in die KI-Logdatei
        with open(filename, "a", encoding="utf-8") as f:
            f.write(f"{'='*50}\n[{ts}] PROMPT_NAME: {prompt_name}\nCONTENT:\n{content}\n{'='*50}\n\n")
