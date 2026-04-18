import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import json
import os
import sqlite3
import requests
from datetime import datetime, timedelta
from database_manager import get_db
from ai_handler import generate_ai_content

# --- DESIGN EINSTELLUNGEN ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

class LigarsGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LIGARS // CORE_CONTROL_UNIT v2.9.7")
        self.geometry("1200x850")

        # Konfiguration laden
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
        except Exception:
            self.config = {"GEMINI_API_KEY": "", "WEB_API_KEY": "LIGARS_SECURE_SYNC_2026"}

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(self.sidebar, text="LIGARS_OS", font=ctk.CTkFont(family="Orbitron", size=22, weight="bold")).pack(pady=20)

        self.timer_label = ctk.CTkLabel(self.sidebar, text="00:00:00", font=("Share Tech Mono", 28, "bold"), text_color="#00ffcc")
        self.timer_label.pack(pady=(10, 20))

        ctk.CTkButton(self.sidebar, text="REFRESH ALL", command=self.refresh_all, fg_color="#1f1f1f").pack(pady=20, padx=20)

        # --- TABS ---
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.tab_status = self.tabview.add("STATUS / AI")
        self.tab_master = self.tabview.add("EQUIPMENT_MASTER")
        self.tab_data = self.tabview.add("BIOMETRIE & EINKAUF")
        self.tab_web = self.tabview.add("WEB_STRAFBUCH")

        self.setup_status_tab()
        self.setup_master_tab()
        self.setup_data_tab()
        self.setup_web_tab()

        self.update_timer()
        self.refresh_all()

    def update_timer(self):
        now = datetime.now()
        target = now.replace(hour=23, minute=59, second=59)
        diff = target - now
        h, m, s = str(diff).split(".")[0].split(":")
        self.timer_label.configure(text=f"{h.zfill(2)}:{m.zfill(2)}:{s.zfill(2)}")
        self.after(1000, self.update_timer)

    # --- UI HILFSFUNKTIONEN ---
    def create_tree(self, parent, columns):
        frame = tk.Frame(parent, bg="#0a0a0a")
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#0a0a0a", foreground="white", fieldbackground="#0a0a0a", borderwidth=0, rowheight=30)
        style.configure("Treeview.Heading", background="#1f1f1f", foreground="#00ffcc", relief="flat")

        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=150)
        tree.pack(side="left", fill="both", expand=True)
        frame.pack(fill="both", expand=True)
        return tree

    def show_details_popup(self, title, subtitle, content):
        if not content: content = "KEIN_INHALT_VERFÜGBAR"
        popup = ctk.CTkToplevel(self)
        popup.title(title)
        popup.geometry("500x400")
        popup.attributes("-topmost", True)
        ctk.CTkLabel(popup, text=subtitle, font=("Orbitron", 14), text_color="#00ffcc").pack(pady=10)
        textbox = ctk.CTkTextbox(popup, width=460, height=250)
        textbox.pack(pady=10)
        textbox.insert("0.0", content)
        textbox.configure(state="disabled")
        ctk.CTkButton(popup, text="CLOSE", command=popup.destroy).pack(pady=10)

    # --- TAB SETUPS ---
    def setup_status_tab(self):
        self.feedback_display = ctk.CTkTextbox(self.tab_status, width=750, height=250)
        self.feedback_display.pack(pady=20, padx=20)
        self.command_entry = ctk.CTkEntry(self.tab_status, width=600, placeholder_text="Befehl...")
        self.command_entry.pack(pady=10)
        ctk.CTkButton(self.tab_status, text="INJECT", command=self.inject_command).pack(pady=20)

    def setup_master_tab(self):
        self.tree_master = self.create_tree(self.tab_master, ("Kategorie", "Inhalt"))
        self.tree_master.bind("<Double-1>", lambda e: self.on_double_click_master(e))

    def on_double_click_master(self, event):
        item_id = self.tree_master.identify_row(event.y)
        if item_id:
            vals = self.tree_master.item(item_id, "values")
            self.show_details_popup("MASTER_DETAILS", vals[0], vals[1])

    def setup_data_tab(self):
        self.tree_bio = self.create_tree(self.tab_data, ("Datum", "Taille", "Brust", "Hals"))
        self.tree_equip = self.create_tree(self.tab_data, ("Item", "Status", "Preis"))

    def setup_web_tab(self):
        self.tree_web = self.create_tree(self.tab_web, ("Zeit", "Name", "Status", "Kommentar"))
        self.tree_web.bind("<Double-1>", lambda e: self.on_double_click_web(e))

    def on_double_click_web(self, event):
        item_id = self.tree_web.identify_row(event.y)
        if item_id:
            vals = self.tree_web.item(item_id, "values")
            self.show_details_popup("WEB_DETAILS", f"Feedback von {vals[1]}", vals[3])

    # --- LOADERS ---
    def refresh_all(self):
        # Master DB - Robustere Spaltenabfrage
        for i in self.tree_master.get_children(): self.tree_master.delete(i)
        if os.path.exists("equipment_master.db"):
            try:
                with sqlite3.connect("equipment_master.db") as conn:
                    # Wir fragen einfach alles ab (*), um Fehler bei Spaltennamen zu vermeiden
                    cursor = conn.execute("SELECT * FROM master_assets")
                    for r in cursor.fetchall():
                        # Wir nehmen an, dass Spalte 1 die Kategorie und Spalte 2 der Inhalt ist
                        if len(r) >= 3:
                            self.tree_master.insert("", "end", values=(r[1], r[2]))
                        elif len(r) == 2:
                            self.tree_master.insert("", "end", values=(r[0], r[1]))
            except Exception as e:
                print(f"Fehler beim Laden der Master-DB: {e}")

        # Web Sync
        for i in self.tree_web.get_children(): self.tree_web.delete(i)
        try:
            resp = requests.post("https://ligars.any64.de/api/strafbuch_fetch.php",
                               json={"api_key": self.config.get("WEB_API_KEY", "LIGARS_SECURE_SYNC_2026")},
                               timeout=3)
            if resp.status_code == 200:
                for entry in resp.json().get("data", []):
                    kommentar = entry['proband_kommentar'] if entry['proband_kommentar'] else "---"
                    self.tree_web.insert("", "end", values=(entry['zeitstempel'], entry['proband_name'], entry['status'], kommentar))
        except: pass

        # AI Status / Biometrie / Einkäufe
        try:
            with get_db() as conn:
                # Feedback
                row = conn.execute("SELECT wert FROM settings WHERE name = 'feedback'").fetchone()
                if row:
                    self.feedback_display.delete("0.0", "end")
                    self.feedback_display.insert("0.0", row['wert'])

                # Biometrie
                for i in self.tree_bio.get_children(): self.tree_bio.delete(i)
                for r in conn.execute("SELECT datum, taille, brust, hals FROM eintraege ORDER BY id DESC LIMIT 5").fetchall():
                    self.tree_bio.insert("", "end", values=(r[0], r[1], r[2], r[3]))

                # Einkäufe
                for i in self.tree_equip.get_children(): self.tree_equip.delete(i)
                for r in conn.execute("SELECT item, status, preis FROM einkaeufe").fetchall():
                    self.tree_equip.insert("", "end", values=(r[0], "OK" if r[1]==1 else "OPEN", r[2]))
        except Exception as e:
            print(f"Fehler beim Laden lokaler Daten: {e}")

    def inject_command(self):
        cmd = self.command_entry.get()
        if not cmd: return
        res = generate_ai_content(self.config['GEMINI_API_KEY'], "Du bist LIGARS_CORE.", cmd)
        if res:
            with get_db() as conn:
                conn.execute("UPDATE settings SET wert = ? WHERE name = 'feedback'", (res,))
            self.refresh_all()

if __name__ == "__main__":
    LigarsGUI().mainloop()
