"""
PassVault — Mobile Password Manager
Built with Kivy for Android & iOS
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import get_color_from_hex

from database import initialize_db, get_connection
from auth import register_master_user, login
from vault import (add_credential, list_credentials, get_credential,
                   search_credentials, update_credential, delete_credential)
from logger import get_all_logs, get_failed_logs

# ── Theme ─────────────────────────────────────────────────────────────────────
BG      = get_color_from_hex("#0d1117")
BG2     = get_color_from_hex("#161b22")
BG3     = get_color_from_hex("#21262d")
ACCENT  = get_color_from_hex("#00ff88")
DANGER  = get_color_from_hex("#ff4d4d")
TEXT    = get_color_from_hex("#e6edf3")
DIM     = get_color_from_hex("#8b949e")
BORDER  = get_color_from_hex("#30363d")

Window.clearcolor = BG


# ── Reusable Widgets ──────────────────────────────────────────────────────────

def make_label(text, color=None, size=16, bold=False, halign="left"):
    lbl = Label(
        text=text,
        color=color or TEXT,
        font_size=dp(size),
        bold=bold,
        halign=halign,
        size_hint_y=None,
    )
    lbl.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1] + dp(4)))
    lbl.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
    return lbl


def make_input(hint="", password=False):
    inp = TextInput(
        hint_text=hint,
        password=password,
        multiline=False,
        background_color=BG3,
        foreground_color=TEXT,
        hint_text_color=DIM,
        cursor_color=ACCENT,
        font_size=dp(15),
        size_hint_y=None,
        height=dp(48),
        padding=[dp(12), dp(12)],
    )
    return inp


def accent_btn(text, on_press, danger=False):
    color = DANGER if danger else ACCENT
    btn = Button(
        text=text,
        background_color=color,
        color=get_color_from_hex("#0d1117"),
        bold=True,
        font_size=dp(14),
        size_hint_y=None,
        height=dp(50),
    )
    btn.bind(on_press=on_press)
    return btn


def ghost_btn(text, on_press):
    btn = Button(
        text=text,
        background_color=BG3,
        color=DIM,
        font_size=dp(13),
        size_hint_y=None,
        height=dp(44),
    )
    btn.bind(on_press=on_press)
    return btn


def show_popup(title, message, ok_text="OK", on_ok=None):
    content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(16))
    lbl = Label(text=message, color=TEXT, font_size=dp(14),
                halign='center', text_size=(dp(260), None))
    lbl.bind(texture_size=lambda i, v: setattr(i, 'height', v[1]))
    content.add_widget(lbl)
    popup = Popup(title=title, content=content,
                  size_hint=(0.85, None), height=dp(220),
                  background_color=BG2, title_color=ACCENT,
                  separator_color=ACCENT)
    def close(*a):
        popup.dismiss()
        if on_ok:
            on_ok()
    btn = accent_btn(ok_text, close)
    content.add_widget(btn)
    popup.open()


# ═════════════════════════════════════════════════════════════════════════════
#  LOGIN SCREEN
# ═════════════════════════════════════════════════════════════════════════════

class LoginScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.fernet_key = None
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=dp(30), spacing=dp(14))

        # Header
        root.add_widget(Widget(size_hint_y=None, height=dp(40)))
        root.add_widget(make_label("🔐", color=ACCENT, size=48, halign='center'))
        root.add_widget(make_label("PASSWORD VAULT", color=ACCENT, size=20,
                                   bold=True, halign='center'))
        root.add_widget(make_label("SECURE CREDENTIAL MANAGER", color=DIM,
                                   size=11, halign='center'))
        root.add_widget(Widget(size_hint_y=None, height=dp(30)))

        # Check first run
        conn = get_connection()
        is_first = not conn.execute("SELECT id FROM master_user LIMIT 1").fetchone()
        conn.close()
        self._is_first = is_first

        mode = "CREATE MASTER ACCOUNT" if is_first else "SIGN IN"
        root.add_widget(make_label(mode, color=DIM, size=11, halign='center'))

        root.add_widget(make_label("USERNAME", color=DIM, size=11))
        self.inp_user = make_input("Enter username")
        root.add_widget(self.inp_user)

        root.add_widget(make_label("MASTER PASSWORD", color=DIM, size=11))
        self.inp_pw = make_input("Enter password", password=True)
        root.add_widget(self.inp_pw)

        if is_first:
            root.add_widget(make_label("CONFIRM PASSWORD", color=DIM, size=11))
            self.inp_confirm = make_input("Repeat password", password=True)
            root.add_widget(self.inp_confirm)

        self.lbl_err = make_label("", color=DANGER, size=12, halign='center')
        root.add_widget(self.lbl_err)

        btn_text = "CREATE ACCOUNT" if is_first else "UNLOCK VAULT"
        root.add_widget(accent_btn(btn_text, self._submit))
        root.add_widget(Widget())  # spacer

        self.add_widget(root)

    def _submit(self, *_):
        username = self.inp_user.text.strip()
        password = self.inp_pw.text

        if not username or not password:
            self.lbl_err.text = "All fields are required."
            return

        if self._is_first:
            confirm = self.inp_confirm.text
            if password != confirm:
                self.lbl_err.text = "Passwords do not match."
                return
            if not register_master_user(username, password):
                self.lbl_err.text = "Registration failed."
                return

        key = login(username, password)
        if key:
            app = App.get_running_app()
            app.fernet_key = key
            app.username   = username
            self.manager.transition = SlideTransition(direction='left')
            self.manager.current = 'vault'
        else:
            self.lbl_err.text = "❌  Invalid credentials."
            self.inp_pw.text = ""


# ═════════════════════════════════════════════════════════════════════════════
#  VAULT SCREEN
# ═════════════════════════════════════════════════════════════════════════════

class VaultScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        self._build()
        self._load()

    def _build(self):
        root = BoxLayout(orientation='vertical')

        # Top bar
        topbar = BoxLayout(size_hint_y=None, height=dp(56),
                           padding=[dp(16), dp(8)])
        with topbar.canvas.before:
            Color(*BG2)
            self._tb_rect = Rectangle(pos=topbar.pos, size=topbar.size)
        topbar.bind(pos=lambda i, v: setattr(self._tb_rect, 'pos', v),
                    size=lambda i, v: setattr(self._tb_rect, 'size', v))

        topbar.add_widget(Label(text="🔐 VAULT", color=ACCENT,
                                bold=True, font_size=dp(16)))
        lock_btn = Button(text="LOCK", background_color=DANGER,
                          color=TEXT, bold=True, font_size=dp(12),
                          size_hint=(None, None), size=(dp(70), dp(36)))
        lock_btn.bind(on_press=self._lock)
        topbar.add_widget(lock_btn)
        root.add_widget(topbar)

        # Search
        search_row = BoxLayout(size_hint_y=None, height=dp(52),
                               padding=[dp(12), dp(6)], spacing=dp(8))
        self.search_inp = TextInput(
            hint_text="🔍 Search sites, usernames…",
            multiline=False,
            background_color=BG3,
            foreground_color=TEXT,
            hint_text_color=DIM,
            font_size=dp(14),
            padding=[dp(10), dp(10)],
        )
        self.search_inp.bind(text=lambda i, v: self._load(v))
        search_row.add_widget(self.search_inp)
        root.add_widget(search_row)

        # Credential list
        self.scroll = ScrollView()
        self.list_layout = GridLayout(cols=1, spacing=dp(2),
                                      size_hint_y=None, padding=[dp(10), dp(4)])
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        self.scroll.add_widget(self.list_layout)
        root.add_widget(self.scroll)

        # Bottom nav
        nav = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(2))
        with nav.canvas.before:
            Color(*BG2)
            self._nav_rect = Rectangle(pos=nav.pos, size=nav.size)
        nav.bind(pos=lambda i, v: setattr(self._nav_rect, 'pos', v),
                 size=lambda i, v: setattr(self._nav_rect, 'size', v))

        for label, screen in [("+ ADD", "add"), ("📋 LOGS", "logs")]:
            btn = Button(text=label, background_color=BG3, color=ACCENT,
                         bold=True, font_size=dp(13))
            btn.bind(on_press=lambda _, s=screen: self._goto(s))
            nav.add_widget(btn)
        root.add_widget(nav)

        self.add_widget(root)

    def _goto(self, screen):
        self.manager.transition = SlideTransition(direction='left')
        self.manager.current = screen

    def _load(self, keyword=""):
        self.list_layout.clear_widgets()
        creds = search_credentials(keyword) if keyword else list_credentials()
        if not creds:
            self.list_layout.add_widget(
                make_label("No credentials stored yet.", color=DIM,
                           halign='center', size=13))
            return
        for c in creds:
            self._add_row(c)

    def _add_row(self, c):
        row = BoxLayout(orientation='horizontal', size_hint_y=None,
                        height=dp(70), padding=[dp(12), dp(8)], spacing=dp(8))
        with row.canvas.before:
            Color(*BG2)
            RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(6)])

        info = BoxLayout(orientation='vertical', spacing=dp(2))
        info.add_widget(Label(text=c['site_name'], color=TEXT, bold=True,
                               font_size=dp(15), halign='left',
                               size_hint_y=None, height=dp(24),
                               text_size=(dp(200), None)))
        info.add_widget(Label(text=c['username'], color=DIM,
                               font_size=dp(12), halign='left',
                               size_hint_y=None, height=dp(20),
                               text_size=(dp(200), None)))
        row.add_widget(info)

        reveal_btn = Button(text="REVEAL", background_color=ACCENT,
                            color=get_color_from_hex("#0d1117"),
                            bold=True, font_size=dp(11),
                            size_hint=(None, None), size=(dp(72), dp(38)))
        reveal_btn.bind(on_press=lambda _, cid=c['id']: self._reveal(cid))
        row.add_widget(reveal_btn)

        del_btn = Button(text="DEL", background_color=DANGER,
                         color=TEXT, bold=True, font_size=dp(11),
                         size_hint=(None, None), size=(dp(48), dp(38)))
        del_btn.bind(on_press=lambda _, cid=c['id'], sn=c['site_name']:
                     self._confirm_delete(cid, sn))
        row.add_widget(del_btn)

        self.list_layout.add_widget(row)
        self.list_layout.add_widget(Widget(size_hint_y=None, height=dp(4)))

    def _reveal(self, record_id):
        key = App.get_running_app().fernet_key
        cred = get_credential(record_id, key)
        if not cred:
            return
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        for label, val, col in [
            ("SITE",     cred['site_name'],          TEXT),
            ("URL",      cred.get('site_url') or "—", DIM),
            ("USERNAME", cred['username'],             TEXT),
            ("PASSWORD", cred['decrypted_password'],   ACCENT),
            ("NOTES",    cred.get('notes') or "—",     DIM),
        ]:
            row = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(30))
            row.add_widget(Label(text=label, color=DIM, font_size=dp(11),
                                  size_hint_x=None, width=dp(80), bold=True))
            row.add_widget(Label(text=val, color=col, font_size=dp(13),
                                  halign='left', text_size=(dp(200), None)))
            content.add_widget(row)

        popup = Popup(title=f"🌐 {cred['site_name']}", content=content,
                      size_hint=(0.92, None), height=dp(380),
                      background_color=BG2, title_color=ACCENT,
                      separator_color=ACCENT)
        close_btn = ghost_btn("CLOSE", lambda _: popup.dismiss())
        content.add_widget(close_btn)
        popup.open()

    def _confirm_delete(self, record_id, site_name):
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(16))
        content.add_widget(Label(
            text=f"Delete credentials for\n[b]{site_name}[/b]?\n\nThis cannot be undone.",
            markup=True, color=TEXT, font_size=dp(14),
            halign='center', text_size=(dp(260), None)))
        row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(48))
        popup = Popup(title="Confirm Delete", content=content,
                      size_hint=(0.85, None), height=dp(260),
                      background_color=BG2, title_color=DANGER,
                      separator_color=DANGER)
        def do_delete(_):
            delete_credential(record_id)
            popup.dismiss()
            self._load()
        row.add_widget(accent_btn("DELETE", do_delete, danger=True))
        row.add_widget(ghost_btn("CANCEL", lambda _: popup.dismiss()))
        content.add_widget(row)
        popup.open()

    def _lock(self, *_):
        App.get_running_app().fernet_key = None
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'login'


# ═════════════════════════════════════════════════════════════════════════════
#  ADD CREDENTIAL SCREEN
# ═════════════════════════════════════════════════════════════════════════════

class AddScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical')

        # Top bar
        topbar = BoxLayout(size_hint_y=None, height=dp(56),
                           padding=[dp(16), dp(8)])
        with topbar.canvas.before:
            Color(*BG2)
            r = Rectangle(pos=topbar.pos, size=topbar.size)
        topbar.bind(pos=lambda i, v: setattr(r, 'pos', v),
                    size=lambda i, v: setattr(r, 'size', v))
        back_btn = Button(text="← BACK", background_color=BG3, color=DIM,
                          bold=True, font_size=dp(12),
                          size_hint=(None, None), size=(dp(80), dp(36)))
        back_btn.bind(on_press=self._back)
        topbar.add_widget(back_btn)
        topbar.add_widget(Label(text="ADD CREDENTIAL", color=ACCENT,
                                bold=True, font_size=dp(15)))
        root.add_widget(topbar)

        scroll = ScrollView()
        form = GridLayout(cols=1, spacing=dp(6), padding=[dp(20), dp(16)],
                          size_hint_y=None)
        form.bind(minimum_height=form.setter('height'))

        fields = [
            ("SITE NAME *",       "e.g. GitHub",             False),
            ("SITE URL",          "https://github.com",       False),
            ("USERNAME / EMAIL *","you@email.com",            False),
            ("PASSWORD *",        "Enter password",           True),
            ("NOTES",             "Optional notes",           False),
        ]
        self._inputs = {}
        for label, hint, is_pw in fields:
            form.add_widget(make_label(label, color=DIM, size=11))
            inp = make_input(hint, password=is_pw)
            form.add_widget(inp)
            self._inputs[label] = inp
            form.add_widget(Widget(size_hint_y=None, height=dp(6)))

        self.status_lbl = make_label("", color=ACCENT, size=12, halign='center')
        form.add_widget(self.status_lbl)

        save_btn = accent_btn("💾  SAVE CREDENTIAL", self._save)
        form.add_widget(save_btn)

        scroll.add_widget(form)
        root.add_widget(scroll)
        self.add_widget(root)

    def _save(self, *_):
        v = {k: inp.text.strip() for k, inp in self._inputs.items()}
        site  = v.get("SITE NAME *", "")
        url   = v.get("SITE URL", "")
        user  = v.get("USERNAME / EMAIL *", "")
        pw    = v.get("PASSWORD *", "")
        notes = v.get("NOTES", "")

        if not site or not user or not pw:
            self.status_lbl.text = "❌ Site, username and password are required."
            self.status_lbl.color = DANGER
            return

        key = App.get_running_app().fernet_key
        add_credential(site, url, user, pw, key, notes)
        self.status_lbl.text = f"✅ Saved {site}!"
        self.status_lbl.color = ACCENT
        for inp in self._inputs.values():
            inp.text = ""
        Clock.schedule_once(lambda _: self._back(), 1.2)

    def _back(self, *_):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'vault'


# ═════════════════════════════════════════════════════════════════════════════
#  LOGS SCREEN
# ═════════════════════════════════════════════════════════════════════════════

class LogsScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical')

        topbar = BoxLayout(size_hint_y=None, height=dp(56),
                           padding=[dp(16), dp(8)])
        with topbar.canvas.before:
            Color(*BG2)
            r = Rectangle(pos=topbar.pos, size=topbar.size)
        topbar.bind(pos=lambda i, v: setattr(r, 'pos', v),
                    size=lambda i, v: setattr(r, 'size', v))
        back_btn = Button(text="← BACK", background_color=BG3, color=DIM,
                          bold=True, font_size=dp(12),
                          size_hint=(None, None), size=(dp(80), dp(36)))
        back_btn.bind(on_press=lambda _: self._back())
        topbar.add_widget(back_btn)
        topbar.add_widget(Label(text="LOGIN AUDIT LOG", color=ACCENT,
                                bold=True, font_size=dp(15)))
        root.add_widget(topbar)

        scroll = ScrollView()
        self.log_layout = GridLayout(cols=1, spacing=dp(3),
                                     padding=[dp(10), dp(8)], size_hint_y=None)
        self.log_layout.bind(minimum_height=self.log_layout.setter('height'))

        logs = get_all_logs(100)
        if not logs:
            self.log_layout.add_widget(
                make_label("No login logs found.", color=DIM, halign='center'))
        for log in logs:
            color = ACCENT if log['status'] == 'SUCCESS' else DANGER
            row = BoxLayout(size_hint_y=None, height=dp(62),
                            padding=[dp(12), dp(8)], spacing=dp(6))
            with row.canvas.before:
                Color(*BG2)
                RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(5)])

            info = BoxLayout(orientation='vertical', spacing=dp(2))
            info.add_widget(Label(
                text=f"[b]{log['status']}[/b]  {log['username']}",
                markup=True, color=color, font_size=dp(14),
                halign='left', size_hint_y=None, height=dp(24),
                text_size=(dp(220), None)))
            info.add_widget(Label(
                text=f"{log['timestamp'][:16]}  IP: {log['ip_address']}",
                color=DIM, font_size=dp(11),
                halign='left', size_hint_y=None, height=dp(18),
                text_size=(dp(220), None)))
            row.add_widget(info)
            self.log_layout.add_widget(row)
            self.log_layout.add_widget(Widget(size_hint_y=None, height=dp(2)))

        scroll.add_widget(self.log_layout)
        root.add_widget(scroll)
        self.add_widget(root)

    def _back(self):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'vault'


# ═════════════════════════════════════════════════════════════════════════════
#  APP
# ═════════════════════════════════════════════════════════════════════════════

class PassVaultApp(App):
    fernet_key = None
    username   = None

    def build(self):
        initialize_db()
        self.title = "PassVault"
        self.icon  = "icon.png"

        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(VaultScreen(name='vault'))
        sm.add_widget(AddScreen(name='add'))
        sm.add_widget(LogsScreen(name='logs'))
        return sm


if __name__ == "__main__":
    PassVaultApp().run()
