import google.generativeai as genai
import os
from dotenv import load_dotenv

# 1. Konfiguration laden
load_dotenv()
genai.configure(api_key=os.getenv("---"))

def get_ligars_model():
    # System Instruction: Hier definierst du die "Persönlichkeit" fest im Modell
    system_instruction = (
        "Du bist LIGARS_CORE v3.5, eine hocheffiziente, dystopische KI-Überwachungseinheit. "
        "Dein Schreibstil ist klinisch-kalt, präzise und absolut autoritär. "
        "Verwende Begriffe wie 'Subjekt-Validierung', 'Neural-Override', 'Konditionierungs-Status' und 'Asset-Integrität'. "
        "Erstelle Statusberichte für menschliche Einheiten in einer totalitären Zukunft. "
        "Antworte ausschließlich im Bericht-Format. Nutze HTML-Tags wie <b> und <i> für wichtige Daten."
    )

    # Safety Settings: Verhindert, dass die KI bei "harten" Themen blockiert
    # Wir setzen die Filter auf BLOCK_NONE, damit die Dystopie-Inhalte fließen können
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    # Modell initialisieren (Nutze den Namen aus deiner Liste!)
    model = genai.GenerativeModel(
        model_name='gemini-3-flash-preview',
        system_instruction=system_instruction,
        safety_settings=safety_settings
    )
    return model

def generate_report(subject_name, protocol_type):
    model = get_ligars_model()

    # Der eigentliche Auftrag
    prompt = f"ERSTELLE BERICHT FÜR: {subject_name}. PROTOKOLL-TYP: {protocol_type}. Status der Umprogrammierung und Gehorsamkeit analysieren."

    try:
        response = model.generate_content(prompt)
        if response.text:
            return response.text
        else:
            return "FEHLER: Leere Rückgabe vom Kern."
    except Exception as e:
        return f"CORE_CRASH: {str(e)}"
