import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import json
import os
import sqlite3
from datetime import datetime, timedelta
from database_manager import get_db
from ai_handler import generate_ai_content

# --- DESIGN EINSTELLUNGEN ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

class LigarsGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LIGARS // CORE_CONTROL_UNIT v2.8")
        self.geometry("1200x850")

        # Konfiguration laden
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            self.config = {"GEMINI_API_KEY": ""}

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(self.sidebar, text="LIGARS_OS", font=ctk.CTkFont(family="Orbitron", size=22, weight="bold")).pack(pady=20)

        # COUNTDOWN TIMER (Sidebar)
        ctk.CTkLabel(self.sidebar, text="NÄCHSTER KONTAKT:", font=("Share Tech Mono", 12), text_color="#888").pack(pady=(10, 0))
        self.timer_label = ctk.CTkLabel(self.sidebar, text="00:00:00", font=("Share Tech Mono", 28, "bold"), text_color="#00ffcc")
        self.timer_label.pack(pady=(0, 20))

        self.btn_refresh = ctk.CTkButton(self.sidebar, text="REFRESH ALL", command=self.refresh_all, fg_color="#1f1f1f")
        self.btn_refresh.pack(pady=20, padx=20)

        # --- TABS ---
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.tab_status = self.tabview.add("STATUS / AI")
        self.tab_master = self.tabview.add("EQUIPMENT_MASTER")
        self.tab_data = self.tabview.add("BIOMETRIE & EINKAUF")

        self.setup_status_tab()
        self.setup_master_tab()
        self.setup_data_tab()

        # Start Countdown & Initial Load
        self.update_timer()
        self.refresh_all()

    def update_timer(self):
        now = datetime.now()
        target = now.replace(hour=23, minute=59, second=59, microsecond=0)
        if now > target: target += timedelta(days=1)
        diff = target - now
        h, m, s = str(diff).split(".")[0].split(":")
        self.timer_label.configure(text=f"{h.zfill(2)}:{m.zfill(2)}:{s.zfill(2)}")
        self.after(1000, self.update_timer)

    def setup_status_tab(self):
        self.feedback_display = ctk.CTkTextbox(self.tab_status, width=750, height=250, font=("Share Tech Mono", 14))
        self.feedback_display.pack(pady=20, padx=20)
        self.command_entry = ctk.CTkEntry(self.tab_status, width=600, placeholder_text="Befehl eingeben...")
        self.command_entry.pack(pady=10)
        ctk.CTkButton(self.tab_status, text="INJECT", command=self.inject_command, fg_color="#00ffcc", text_color="#000").pack(pady=20)

    def setup_master_tab(self):
        # Hier nutzen wir master_assets
        container = ctk.CTkFrame(self.tab_master, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree_master = self.create_tree(container, ("Kategorie", "Inhalt"))
        self.tree_master.pack(fill="both", expand=True)

    def setup_data_tab(self):
        container = ctk.CTkFrame(self.tab_data, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree_bio = self.create_tree(container, ("Datum", "Taille", "Brust", "Hals"))
        self.tree_bio.pack(fill="both", expand=True, pady=(0, 10))
        self.tree_equip = self.create_tree(container, ("Item", "Status", "Preis"))
        self.tree_equip.pack(fill="both", expand=True)

    def create_tree(self, parent, columns):
        frame = tk.Frame(parent, bg="#0a0a0a")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        style = ttk.Style()
        style.configure("Treeview", background="#0a0a0a", foreground="white", fieldbackground="#0a0a0a", borderwidth=0)
        style.map("Treeview", background=[('selected', '#00ffcc')], foreground=[('selected', 'black')])
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=150)
        tree.pack(side="left", fill="both", expand=True)
        frame.pack(fill="both", expand=True)
        return tree

    def load_master_data(self):
        for i in self.tree_master.get_children(): self.tree_master.delete(i)
        if os.path.exists("equipment_master.db"):
            try:
                conn = sqlite3.connect("equipment_master.db")
                curr = conn.cursor()
                # Da master_assets existiert, nehmen wir diese Tabelle
                curr.execute("SELECT * FROM master_assets")
                for r in curr.fetchall():
                    # Wir nehmen die ersten zwei Spalten (Kategorie & Text)
                    self.tree_master.insert("", "end", values=(r[1], r[2]) if len(r) > 2 else (r[0], r[1]))
                conn.close()
            except Exception as e:
                print(f"Fehler Master-DB: {e}")

    def load_local_data(self):
        for i in self.tree_bio.get_children(): self.tree_bio.delete(i)
        for i in self.tree_equip.get_children(): self.tree_equip.delete(i)
        try:
            with get_db() as conn:
                for r in conn.execute("SELECT datum, taille, brust, hals FROM eintraege ORDER BY id DESC LIMIT 5").fetchall():
                    self.tree_bio.insert("", "end", values=(r[0], r[1], r[2], r[3]))
                for r in conn.execute("SELECT item, status, preis FROM einkaeufe").fetchall():
                    self.tree_equip.insert("", "end", values=(r[0], "OK" if r[1]==1 else "OPEN", r[2]))
        except: pass

    def inject_command(self):
        text = self.command_entry.get()
        if not text: return
        res = generate_ai_content(self.config['GEMINI_API_KEY'], "Du bist LIGARS_CORE.", text)
        if res:
            with get_db() as conn:
                conn.execute("UPDATE settings SET wert = ? WHERE name = 'feedback'", (res,))
                conn.commit()
            self.refresh_all()

    def refresh_all(self):
        self.load_master_data()
        self.load_local_data()
        with get_db() as conn:
            row = conn.execute("SELECT wert FROM settings WHERE name = 'feedback'").fetchone()
            if row:
                self.feedback_display.delete("0.0", "end")
                self.feedback_display.insert("0.0", row['wert'])

if __name__ == "__main__":
    app = LigarsGUI()
    app.mainloop()
