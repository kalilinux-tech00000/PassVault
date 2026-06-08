
"""
gui.py — Tkinter GUI for Password Manager
Run: python gui.py
Dark cybersecurity aesthetic — wires into existing modules.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
# clipboard handled below

# ── Try clipboard support ─────────────────────────────────────────────────────
try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False

from database import initialize_db, get_connection
from auth import register_master_user, login
from vault import (
    add_credential, list_credentials, get_credential,
    search_credentials, update_credential, delete_credential
)
from logger import get_all_logs, get_failed_logs, export_logs_csv

# ── Theme ─────────────────────────────────────────────────────────────────────
BG        = "#0d1117"
BG2       = "#161b22"
BG3       = "#21262d"
ACCENT    = "#00ff88"
ACCENT2   = "#00bfff"
DANGER    = "#ff4d4d"
TEXT      = "#e6edf3"
TEXT_DIM  = "#8b949e"
BORDER    = "#30363d"
FONT_MAIN = ("Courier New", 11)
FONT_LG   = ("Courier New", 14, "bold")
FONT_SM   = ("Courier New", 9)
FONT_HEAD = ("Courier New", 18, "bold")


def style_button(btn, kind="primary"):
    if kind == "primary":
        btn.configure(bg=ACCENT, fg="#0d1117", activebackground="#00cc70",
                      activeforeground="#0d1117", relief="flat", cursor="hand2",
                      font=("Courier New", 10, "bold"), bd=0)
    elif kind == "danger":
        btn.configure(bg=DANGER, fg="white", activebackground="#cc0000",
                      activeforeground="white", relief="flat", cursor="hand2",
                      font=("Courier New", 10, "bold"), bd=0)
    elif kind == "ghost":
        btn.configure(bg=BG3, fg=TEXT_DIM, activebackground=BORDER,
                      activeforeground=TEXT, relief="flat", cursor="hand2",
                      font=FONT_MAIN, bd=0)


def style_entry(entry):
    entry.configure(bg=BG3, fg=TEXT, insertbackground=ACCENT,
                    relief="flat", font=FONT_MAIN, bd=0,
                    highlightthickness=1, highlightcolor=ACCENT,
                    highlightbackground=BORDER)


# ═════════════════════════════════════════════════════════════════════════════
#  LOGIN / REGISTER WINDOW
# ═════════════════════════════════════════════════════════════════════════════

class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🔐 Password Manager")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.fernet_key = None

        self._center(420, 520)
        initialize_db()
        self._check_first_run()
        self._build_ui()

    def _center(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _check_first_run(self):
        conn = get_connection()
        self._is_first_run = not conn.execute(
            "SELECT id FROM master_user LIMIT 1"
        ).fetchone()
        conn.close()

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=BG, pady=30)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔐", font=("Courier New", 36), bg=BG, fg=ACCENT).pack()
        tk.Label(hdr, text="PASSWORD VAULT", font=FONT_HEAD, bg=BG, fg=ACCENT).pack()
        tk.Label(hdr, text="SECURE CREDENTIAL MANAGER", font=FONT_SM,
                 bg=BG, fg=TEXT_DIM).pack(pady=(2, 0))

        # Card
        card = tk.Frame(self, bg=BG2, padx=30, pady=30,
                        highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="both", expand=True, padx=30, pady=(0, 30))

        mode_text = "CREATE MASTER ACCOUNT" if self._is_first_run else "SIGN IN"
        tk.Label(card, text=mode_text, font=("Courier New", 11, "bold"),
                 bg=BG2, fg=TEXT_DIM).pack(anchor="w", pady=(0, 15))

        # Username
        tk.Label(card, text="USERNAME", font=FONT_SM, bg=BG2, fg=TEXT_DIM).pack(anchor="w")
        self.ent_user = tk.Entry(card, width=30)
        style_entry(self.ent_user)
        self.ent_user.pack(fill="x", ipady=8, pady=(2, 12))

        # Password
        tk.Label(card, text="MASTER PASSWORD", font=FONT_SM, bg=BG2, fg=TEXT_DIM).pack(anchor="w")
        self.ent_pw = tk.Entry(card, show="●", width=30)
        style_entry(self.ent_pw)
        self.ent_pw.pack(fill="x", ipady=8, pady=(2, 0))

        # Confirm (first run only)
        self.frm_confirm = tk.Frame(card, bg=BG2)
        tk.Label(self.frm_confirm, text="CONFIRM PASSWORD", font=FONT_SM,
                 bg=BG2, fg=TEXT_DIM).pack(anchor="w", pady=(12, 0))
        self.ent_confirm = tk.Entry(self.frm_confirm, show="●", width=30)
        style_entry(self.ent_confirm)
        self.ent_confirm.pack(fill="x", ipady=8, pady=(2, 0))
        if self._is_first_run:
            self.frm_confirm.pack(fill="x")

        # Error label
        self.lbl_err = tk.Label(card, text="", font=FONT_SM, bg=BG2, fg=DANGER)
        self.lbl_err.pack(pady=(10, 0))

        # Submit button
        btn_text = "CREATE ACCOUNT" if self._is_first_run else "UNLOCK VAULT"
        btn = tk.Button(card, text=btn_text, command=self._submit,
                        width=28, pady=10)
        style_button(btn)
        btn.pack(pady=(12, 0))

        self.ent_user.focus()
        self.bind("<Return>", lambda e: self._submit())

    def _submit(self):
        username = self.ent_user.get().strip()
        password = self.ent_pw.get()

        if not username or not password:
            self.lbl_err.config(text="All fields are required.")
            return

        if self._is_first_run:
            confirm = self.ent_confirm.get()
            if password != confirm:
                self.lbl_err.config(text="Passwords do not match.")
                return
            ok = register_master_user(username, password)
            if not ok:
                self.lbl_err.config(text="Registration failed.")
                return

        key = login(username, password)
        if key:
            self.fernet_key = key
            self.destroy()
        else:
            self.lbl_err.config(text="❌  Invalid credentials.")
            self.ent_pw.delete(0, tk.END)


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN VAULT WINDOW
# ═════════════════════════════════════════════════════════════════════════════

class VaultWindow(tk.Tk):
    def __init__(self, fernet_key: bytes):
        super().__init__()
        self.fernet_key = fernet_key
        self.title("🔐 Password Vault")
        self.configure(bg=BG)
        self.minsize(1000, 650)
        self._center(1100, 700)
        self._build_ui()
        self._load_credentials()

    def _center(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────────────────
        topbar = tk.Frame(self, bg=BG2, height=56,
                          highlightthickness=1, highlightbackground=BORDER)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="🔐 PASSWORD VAULT", font=FONT_LG,
                 bg=BG2, fg=ACCENT).pack(side="left", padx=20)

        btn_lock = tk.Button(topbar, text="🔒 LOCK", command=self._lock,
                             padx=15, pady=6)
        style_button(btn_lock, "danger")
        btn_lock.pack(side="right", padx=15, pady=10)

        # ── Tab bar ──────────────────────────────────────────────────────────
        tabbar = tk.Frame(self, bg=BG, pady=0)
        tabbar.pack(fill="x")

        self._tab_btns = {}
        self._active_tab = tk.StringVar(value="vault")
        for label, key in [("VAULT", "vault"), ("ADD NEW", "add"), ("LOGS", "logs")]:
            btn = tk.Button(tabbar, text=label, command=lambda k=key: self._switch_tab(k),
                            padx=20, pady=10, relief="flat", font=("Courier New", 10, "bold"),
                            cursor="hand2")
            btn.pack(side="left")
            self._tab_btns[key] = btn

        self._tab_indicator = tk.Frame(self, bg=ACCENT, height=2)
        self._tab_indicator.pack(fill="x")

        # ── Content area ─────────────────────────────────────────────────────
        self.content = tk.Frame(self, bg=BG)
        self.content.pack(fill="both", expand=True)

        self._frames = {}
        self._frames["vault"] = self._build_vault_tab()
        self._frames["add"]   = self._build_add_tab()
        self._frames["logs"]  = self._build_logs_tab()

        self._switch_tab("vault")

    def _switch_tab(self, key):
        for k, f in self._frames.items():
            f.pack_forget()
        self._frames[key].pack(fill="both", expand=True)
        self._active_tab.set(key)

        for k, btn in self._tab_btns.items():
            if k == key:
                btn.configure(bg=BG, fg=ACCENT)
            else:
                btn.configure(bg=BG, fg=TEXT_DIM)

        if key == "logs":
            self._load_logs()

    # ── VAULT TAB ─────────────────────────────────────────────────────────────
    def _build_vault_tab(self):
        frame = tk.Frame(self.content, bg=BG)

        # Search bar
        search_row = tk.Frame(frame, bg=BG, pady=12, padx=20)
        search_row.pack(fill="x")

        tk.Label(search_row, text="🔍", font=FONT_MAIN, bg=BG, fg=TEXT_DIM).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_search())
        search_ent = tk.Entry(search_row, textvariable=self.search_var, width=40)
        style_entry(search_ent)
        search_ent.pack(side="left", ipady=7, padx=(8, 0), fill="x", expand=True)

        btn_refresh = tk.Button(search_row, text="↻ REFRESH",
                                command=self._load_credentials, padx=12, pady=6)
        style_button(btn_refresh, "ghost")
        btn_refresh.pack(side="right", padx=(10, 0))

        # Table
        tbl_frame = tk.Frame(frame, bg=BG, padx=20)
        tbl_frame.pack(fill="both", expand=True)

        cols = ("ID", "Site", "URL", "Username", "Updated")
        self.tree = ttk.Treeview(tbl_frame, columns=cols, show="headings",
                                 selectmode="browse")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=BG2, foreground=TEXT,
                        fieldbackground=BG2, borderwidth=0,
                        font=FONT_MAIN, rowheight=32)
        style.configure("Treeview.Heading",
                        background=BG3, foreground=ACCENT,
                        font=("Courier New", 10, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", BG3)],
                  foreground=[("selected", ACCENT)])

        widths = {"ID": 45, "Site": 160, "URL": 240, "Username": 200, "Updated": 160}
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths[col], anchor="w")

        scrollbar = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._on_row_double_click)

        # Action buttons
        btn_row = tk.Frame(frame, bg=BG, pady=12, padx=20)
        btn_row.pack(fill="x")

        for text, cmd, kind in [
            ("👁  REVEAL", self._reveal_selected, "primary"),
            ("📋 COPY PW", self._copy_password, "ghost"),
            ("✏️  EDIT",    self._edit_selected,  "ghost"),
            ("🗑  DELETE",  self._delete_selected, "danger"),
        ]:
            tk.Button(btn_row, text=text, command=cmd, padx=18, pady=8
                      ).configure(bg=ACCENT if kind=="primary" else (DANGER if kind=="danger" else BG3),
                                  fg="#0d1117" if kind=="primary" else ("white" if kind=="danger" else TEXT_DIM),
                                  activebackground=BG3, relief="flat", cursor="hand2",
                                  font=("Courier New", 10, "bold"), bd=0)
            btn = btn_row.winfo_children()[-1]
            btn.pack(side="left", padx=(0, 10))

        self.status_var = tk.StringVar(value="")
        tk.Label(frame, textvariable=self.status_var, font=FONT_SM,
                 bg=BG, fg=ACCENT).pack(pady=(0, 8))

        return frame

    def _load_credentials(self, keyword=""):
        for row in self.tree.get_children():
            self.tree.delete(row)
        creds = search_credentials(keyword) if keyword else list_credentials()
        for c in creds:
            self.tree.insert("", "end", iid=str(c["id"]),
                             values=(c["id"], c["site_name"],
                                     c["site_url"] or "", c["username"],
                                     c["updated_at"][:16] if c.get("updated_at") else ""))
        self.status_var.set(f"{len(creds)} credential(s) stored")

    def _on_search(self):
        kw = self.search_var.get().strip()
        self._load_credentials(kw)

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a credential first.", parent=self)
            return None
        return int(sel[0])

    def _on_row_double_click(self, event):
        self._reveal_selected()

    def _reveal_selected(self):
        rid = self._selected_id()
        if rid is None:
            return
        cred = get_credential(rid, self.fernet_key)
        if not cred:
            return
        RevealDialog(self, cred)

    def _copy_password(self):
        rid = self._selected_id()
        if rid is None:
            return
        cred = get_credential(rid, self.fernet_key)
        if not cred:
            return
        if HAS_CLIPBOARD:
            pyperclip.copy(cred["decrypted_password"])
            self.status_var.set("✅ Password copied to clipboard!")
        else:
            messagebox.showinfo("Password", cred["decrypted_password"], parent=self)

    def _edit_selected(self):
        rid = self._selected_id()
        if rid is None:
            return
        EditDialog(self, rid, self.fernet_key, on_save=self._load_credentials)

    def _delete_selected(self):
        rid = self._selected_id()
        if rid is None:
            return
        sel = self.tree.item(str(rid))["values"]
        if messagebox.askyesno("Confirm Delete",
                               f"Delete credentials for '{sel[1]}'?\nThis cannot be undone.",
                               parent=self):
            delete_credential(rid)
            self._load_credentials()
            self.status_var.set(f"🗑 Deleted credential ID={rid}")

    # ── ADD TAB ───────────────────────────────────────────────────────────────
    def _build_add_tab(self):
        frame = tk.Frame(self.content, bg=BG)
        inner = tk.Frame(frame, bg=BG2, padx=40, pady=35,
                         highlightthickness=1, highlightbackground=BORDER)
        inner.place(relx=0.5, rely=0.5, anchor="center", width=540)

        tk.Label(inner, text="ADD NEW CREDENTIAL", font=("Courier New", 13, "bold"),
                 bg=BG2, fg=ACCENT).pack(anchor="w", pady=(0, 20))

        self._add_vars = {}
        fields = [
            ("site_name", "SITE NAME *", False),
            ("site_url",  "SITE URL",    False),
            ("username",  "USERNAME / EMAIL *", False),
            ("password",  "PASSWORD *", True),
            ("notes",     "NOTES",      False),
        ]
        for key, label, is_pw in fields:
            tk.Label(inner, text=label, font=FONT_SM, bg=BG2, fg=TEXT_DIM).pack(anchor="w")
            var = tk.StringVar()
            ent = tk.Entry(inner, textvariable=var, show="●" if is_pw else "")
            style_entry(ent)
            ent.pack(fill="x", ipady=8, pady=(2, 12))
            self._add_vars[key] = var

        self._add_status = tk.Label(inner, text="", font=FONT_SM, bg=BG2, fg=ACCENT)
        self._add_status.pack()

        btn_row = tk.Frame(inner, bg=BG2)
        btn_row.pack(fill="x", pady=(8, 0))

        save_btn = tk.Button(btn_row, text="💾  SAVE CREDENTIAL",
                             command=self._save_new, padx=20, pady=10)
        style_button(save_btn)
        save_btn.pack(side="left")

        clear_btn = tk.Button(btn_row, text="CLEAR", command=self._clear_add,
                              padx=15, pady=10)
        style_button(clear_btn, "ghost")
        clear_btn.pack(side="left", padx=(10, 0))

        return frame

    def _save_new(self):
        v = {k: var.get().strip() for k, var in self._add_vars.items()}
        if not v["site_name"] or not v["username"] or not v["password"]:
            self._add_status.config(text="❌  Site name, username and password are required.", fg=DANGER)
            return
        add_credential(v["site_name"], v["site_url"], v["username"],
                       v["password"], self.fernet_key, v["notes"])
        self._add_status.config(text=f"✅  Saved credentials for {v['site_name']}!", fg=ACCENT)
        self._clear_add()
        self._load_credentials()

    def _clear_add(self):
        for var in self._add_vars.values():
            var.set("")

    # ── LOGS TAB ──────────────────────────────────────────────────────────────
    def _build_logs_tab(self):
        frame = tk.Frame(self.content, bg=BG)

        ctrl = tk.Frame(frame, bg=BG, pady=12, padx=20)
        ctrl.pack(fill="x")

        tk.Label(ctrl, text="LOGIN AUDIT LOG", font=("Courier New", 12, "bold"),
                 bg=BG, fg=ACCENT).pack(side="left")

        self._log_filter = tk.StringVar(value="all")
        for text, val in [("ALL", "all"), ("FAILED ONLY", "failed")]:
            rb = tk.Radiobutton(ctrl, text=text, variable=self._log_filter,
                                value=val, command=self._load_logs,
                                bg=BG, fg=TEXT_DIM, selectcolor=BG,
                                activebackground=BG, activeforeground=ACCENT,
                                font=FONT_SM, cursor="hand2")
            rb.pack(side="left", padx=(20, 0))

        export_btn = tk.Button(ctrl, text="📥 EXPORT CSV",
                               command=self._export_logs, padx=12, pady=6)
        style_button(export_btn, "ghost")
        export_btn.pack(side="right")

        # Log table
        tbl = tk.Frame(frame, bg=BG, padx=20)
        tbl.pack(fill="both", expand=True)

        cols = ("ID", "Username", "Status", "IP", "Timestamp", "Reason")
        self.log_tree = ttk.Treeview(tbl, columns=cols, show="headings",
                                     selectmode="browse")
        for col, w in zip(cols, [45, 140, 90, 130, 170, 240]):
            self.log_tree.heading(col, text=col)
            self.log_tree.column(col, width=w, anchor="w")

        # Tag colors
        self.log_tree.tag_configure("success", foreground="#00ff88")
        self.log_tree.tag_configure("failed",  foreground=DANGER)

        sb = ttk.Scrollbar(tbl, orient="vertical", command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=sb.set)
        self.log_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        return frame

    def _load_logs(self):
        for row in self.log_tree.get_children():
            self.log_tree.delete(row)
        logs = get_failed_logs() if self._log_filter.get() == "failed" else get_all_logs(200)
        for log in logs:
            tag = "success" if log["status"] == "SUCCESS" else "failed"
            self.log_tree.insert("", "end", values=(
                log["id"], log["username"], log["status"],
                log["ip_address"], log["timestamp"], log.get("reason") or ""
            ), tags=(tag,))

    def _export_logs(self):
        export_logs_csv("login_logs_export.csv")
        messagebox.showinfo("Export", "Logs exported to login_logs_export.csv", parent=self)

    # ── Lock ─────────────────────────────────────────────────────────────────
    def _lock(self):
        if messagebox.askyesno("Lock Vault", "Lock vault and return to login screen?", parent=self):
            self.destroy()
            _start_app()


# ═════════════════════════════════════════════════════════════════════════════
#  DIALOGS
# ═════════════════════════════════════════════════════════════════════════════

class RevealDialog(tk.Toplevel):
    def __init__(self, parent, cred: dict):
        super().__init__(parent)
        self.title("Credential Details")
        self.configure(bg=BG2)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        w, h = 480, 380
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(self, text=f"🌐  {cred['site_name']}", font=FONT_LG,
                 bg=BG2, fg=ACCENT).pack(pady=(20, 5))
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=20)

        info_frame = tk.Frame(self, bg=BG2, padx=30, pady=20)
        info_frame.pack(fill="both", expand=True)

        rows = [
            ("URL",      cred.get("site_url") or "—"),
            ("Username", cred["username"]),
            ("Password", cred["decrypted_password"]),
            ("Notes",    cred.get("notes") or "—"),
            ("Saved",    cred.get("created_at", "")[:16]),
        ]
        for label, val in rows:
            row = tk.Frame(info_frame, bg=BG2, pady=6)
            row.pack(fill="x")
            tk.Label(row, text=f"{label}:", font=FONT_SM, bg=BG2,
                     fg=TEXT_DIM, width=10, anchor="w").pack(side="left")
            color = ACCENT if label == "Password" else TEXT
            tk.Label(row, text=val, font=FONT_MAIN, bg=BG2,
                     fg=color, wraplength=300, anchor="w").pack(side="left")

        btn_row = tk.Frame(self, bg=BG2, pady=15)
        btn_row.pack()

        if HAS_CLIPBOARD:
            def copy():
                pyperclip.copy(cred["decrypted_password"])
                close_btn.configure(text="✅ Copied!")
                self.after(1500, self.destroy)
            cp_btn = tk.Button(btn_row, text="📋 COPY PASSWORD", command=copy,
                               padx=16, pady=8)
            style_button(cp_btn)
            cp_btn.pack(side="left", padx=(0, 10))

        close_btn = tk.Button(btn_row, text="CLOSE", command=self.destroy,
                              padx=16, pady=8)
        style_button(close_btn, "ghost")
        close_btn.pack(side="left")


class EditDialog(tk.Toplevel):
    def __init__(self, parent, record_id: int, fernet_key: bytes, on_save=None):
        super().__init__(parent)
        self.title("Edit Credential")
        self.configure(bg=BG2)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.record_id  = record_id
        self.fernet_key = fernet_key
        self.on_save    = on_save
        w, h = 460, 320
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self._build()

    def _build(self):
        inner = tk.Frame(self, bg=BG2, padx=30, pady=25)
        inner.pack(fill="both", expand=True)

        tk.Label(inner, text=f"EDIT CREDENTIAL  #{self.record_id}",
                 font=("Courier New", 11, "bold"), bg=BG2, fg=ACCENT).pack(anchor="w", pady=(0, 15))

        tk.Label(inner, text="NEW PASSWORD  (leave blank to keep current)",
                 font=FONT_SM, bg=BG2, fg=TEXT_DIM).pack(anchor="w")
        self.pw_var = tk.StringVar()
        pw_ent = tk.Entry(inner, textvariable=self.pw_var, show="●")
        style_entry(pw_ent)
        pw_ent.pack(fill="x", ipady=8, pady=(2, 12))

        tk.Label(inner, text="NOTES  (leave blank to keep current)",
                 font=FONT_SM, bg=BG2, fg=TEXT_DIM).pack(anchor="w")
        self.notes_var = tk.StringVar()
        notes_ent = tk.Entry(inner, textvariable=self.notes_var)
        style_entry(notes_ent)
        notes_ent.pack(fill="x", ipady=8, pady=(2, 20))

        self.status_lbl = tk.Label(inner, text="", font=FONT_SM, bg=BG2, fg=ACCENT)
        self.status_lbl.pack()

        btn_row = tk.Frame(inner, bg=BG2)
        btn_row.pack(fill="x")

        save_btn = tk.Button(btn_row, text="💾 SAVE", command=self._save, padx=15, pady=8)
        style_button(save_btn)
        save_btn.pack(side="left")

        cancel_btn = tk.Button(btn_row, text="CANCEL", command=self.destroy, padx=15, pady=8)
        style_button(cancel_btn, "ghost")
        cancel_btn.pack(side="left", padx=(10, 0))

    def _save(self):
        pw    = self.pw_var.get() or None
        notes = self.notes_var.get() or None
        if not pw and not notes:
            self.status_lbl.config(text="Nothing to update.", fg=DANGER)
            return
        update_credential(self.record_id, self.fernet_key, pw, notes)
        self.status_lbl.config(text="✅ Saved!", fg=ACCENT)
        if self.on_save:
            self.on_save()
        self.after(800, self.destroy)


# ═════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

def _start_app():
    login_win = LoginWindow()
    login_win.mainloop()
    key = login_win.fernet_key
    if key:
        vault_win = VaultWindow(key)
        vault_win.mainloop()


if __name__ == "__main__":
    _start_app()
