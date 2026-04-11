import google.generativeai as genai
from logger_system import LigarsLogger

def generate_ai_content(api_key, system_prompt, task_prompt, prompt_name="UNNAMED_TASK"):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3-flash-preview')

        full_prompt = f"{system_prompt}\n\nAUFTRAG:\n{task_prompt}"

        # Logge den Prompt bevor er gesendet wird
        LigarsLogger.log_prompt(prompt_name, full_prompt)

        response = model.generate_content(full_prompt)

        # Logge die Antwort (gekürzt fürs Terminal)
        LigarsLogger.log("AI", f"Antwort erhalten für {prompt_name}", response.text[:50] + "...")
        return response.text

    except Exception as e:
        LigarsLogger.log("ERR", f"KI-Fehler bei {prompt_name}", str(e))
        return None
