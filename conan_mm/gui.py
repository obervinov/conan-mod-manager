"""Tkinter window. Network/steamcmd work runs in a worker thread, the UI polls a queue."""
import json
import queue
import re
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import __version__, analyze, steam
from .core import Game

try:
    import sv_ttk  # Windows 11 "Sun Valley" ttk theme, light + dark
except ImportError:  # running from source without it: plain ttk, still works
    sv_ttk = None

PALETTE = {
    "dark": {"dim": "#9a9a9a", "off": "#6f6f6f", "warn": "#f0a54a", "bad": "#ff6b6b", "good": "#5fd38d",
             "text_bg": "#1c1c1c", "text_fg": "#e6e6e6"},
    "light": {"dim": "#555555", "off": "#999999", "warn": "#b35c00", "bad": "#cc0000", "good": "#008855",
              "text_bg": "#ffffff", "text_fg": "#1c1c1c"},
}

SOURCE_LABEL = {"managed": "менеджер", "steam": "Steam", "local": "вручную", "missing": "—"}


def detect_game_dir():
    """Steam install of Conan Exiles via registry + libraryfolders.vdf (Windows only)."""
    if sys.platform != "win32":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            steam_path = Path(winreg.QueryValueEx(k, "SteamPath")[0])
    except OSError:
        return None
    libs = [steam_path]
    vdf = steam_path / "steamapps" / "libraryfolders.vdf"
    if vdf.exists():
        libs += [Path(p.replace("\\\\", "\\")) for p in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text(errors="replace"))]
    for lib in libs:
        cand = lib / "steamapps" / "common" / "Conan Exiles"
        if (cand / "ConanSandbox").is_dir():
            return cand
    return None


def dark_titlebar(win, dark):
    """Windows 10 1809+/11: paint the native title bar to match the theme."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        value = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE, pre-20H1 value
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                break
    except (OSError, AttributeError):
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Conan Exiles Mod Manager {__version__}")
        self.geometry("1000x620")
        self.minsize(760, 420)
        self.data_dir = steam.default_data_dir()
        self.cfg_path = self.data_dir / "config.json"
        self.events = queue.Queue()
        self.busy = False
        self.game = None
        self.details = {}
        self.scanner = analyze.Scanner()
        self.infos, self.conflicts, self.engine = {}, [], None
        self.steamcmd = steam.SteamCmd(self.data_dir / "steamcmd", log=self.log_threadsafe)
        self._build()
        self.after(100, self._pump)
        self.cfg = self._load_cfg()
        self.apply_theme(self.cfg.get("theme", "dark"))
        start = self.cfg.get("game_dir") or detect_game_dir()
        if start:
            self.open_game(start)

    # ---------- layout ----------

    def _build(self):
        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")
        ttk.Label(top, text="Папка игры:").pack(side="left")
        self.path_var = tk.StringVar(value="не выбрана")
        ttk.Label(top, textvariable=self.path_var, style="Dim.TLabel").pack(side="left", padx=6, fill="x", expand=True)
        self.theme_btn = ttk.Button(top, text="☀ Светлая", command=self.toggle_theme)
        self.theme_btn.pack(side="right", padx=(6, 0))
        ttk.Button(top, text="Выбрать…", command=self.pick_game).pack(side="right")

        mid = ttk.Frame(self, padding=(6, 0))
        mid.pack(fill="both", expand=True)
        cols = ("n", "on", "title", "wid", "src", "eng", "cnf", "status")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="extended")
        for c, text, w, anchor in (
            ("n", "#", 40, "e"), ("on", "Вкл", 45, "center"), ("title", "Мод", 420, "w"),
            ("wid", "Workshop ID", 110, "w"), ("src", "Источник", 80, "w"),
            ("eng", "Движок", 60, "center"), ("cnf", "Конфл.", 55, "center"), ("status", "Статус", 230, "w"),
        ):
            self.tree.heading(c, text=text)
            self.tree.column(c, width=w, anchor=anchor, stretch=(c == "title"))
        sb = ttk.Scrollbar(mid, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tree.bind("<Double-1>", lambda e: self.toggle())
        self.tree.bind("<space>", lambda e: self.toggle())
        for seq in ("<Control-c>", "<Command-c>"):
            self.tree.bind(seq, lambda e: self.copy("title"))
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Копировать название", command=lambda: self.copy("title"))
        self.menu.add_command(label="Копировать Workshop ID", command=lambda: self.copy("wid"))
        self.menu.add_command(label="Копировать ссылку", command=lambda: self.copy("url"))
        self.menu.add_command(label="Копировать путь к файлу", command=lambda: self.copy("path"))
        self.menu.add_separator()
        self.menu.add_command(label="Открыть в Workshop", command=lambda: self.open_page())
        for seq in ("<Button-3>", "<Button-2>"):
            self.tree.bind(seq, self._popup)

        side = ttk.Frame(mid, padding=(8, 0))
        side.pack(side="left", fill="y")
        self.buttons = []
        for text, cmd in (
            ("Добавить по ID/ссылке", self.add),
            ("Вкл / выкл", self.toggle),
            ("▲ Выше", lambda: self.move(-1)),
            ("▼ Ниже", lambda: self.move(1)),
            (None, None),
            ("Конфликты и порядок…", self.show_conflicts),
            (None, None),
            ("Проверить обновления", self.check),
            ("Обновить выбранные", self.update_selected),
            ("Обновить все", self.update_all),
            (None, None),
            ("Привязать к Workshop ID", self.link),
            ("Открыть в Workshop", self.open_page),
            ("Удалить", self.remove),
            (None, None),
            ("Бэкап в zip…", self.export),
            ("Перечитать с диска", self.refresh),
        ):
            if text is None:
                ttk.Separator(side).pack(fill="x", pady=6)
                continue
            b = ttk.Button(side, text=text, command=cmd)
            b.pack(fill="x", pady=2)
            self.buttons.append(b)

        self.logbox = tk.Text(self, height=8, state="disabled", wrap="word", font=("Consolas", 9))
        self.logbox.pack(fill="x", padx=6, pady=6)

    # ---------- plumbing ----------

    def _load_cfg(self):
        try:
            return json.loads(self.cfg_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save_cfg(self):
        if self.game:
            self.cfg["game_dir"] = str(self.game.root)
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.cfg_path.write_text(json.dumps(self.cfg), encoding="utf-8")
        except OSError as e:
            self.log(f"Не сохранил настройки: {e}")

    # ---------- theme ----------

    def apply_theme(self, name):
        self.theme = name if name in PALETTE else "dark"
        c = PALETTE[self.theme]
        global sv_ttk
        style = ttk.Style(self)
        if sv_ttk:
            try:
                sv_ttk.set_theme(self.theme, self)
            except tk.TclError:  # e.g. Tk 9, which sv-ttk does not support yet
                sv_ttk = None
        if not sv_ttk:
            self._fallback_theme(style, self.theme)
        style.configure("Dim.TLabel", foreground=c["dim"])
        style.configure("Treeview", rowheight=26 if sv_ttk else 20)
        for w in self._themed_windows():
            dark_titlebar(w, self.theme == "dark")
        for t in self._themed_texts():
            t.configure(background=c["text_bg"], foreground=c["text_fg"], insertbackground=c["text_fg"],
                        relief="flat", highlightthickness=0)
        for tree in self._themed_trees():
            tree.tag_configure("off", foreground=c["off"])
            tree.tag_configure("warn", foreground=c["warn"])
            tree.tag_configure("bad", foreground=c["bad"])
            tree.tag_configure("moved", foreground=c["good"])
        if hasattr(self, "theme_btn"):
            self.theme_btn.configure(text="☀ Светлая" if self.theme == "dark" else "☾ Тёмная")

    def _fallback_theme(self, style, name):
        """Hand-made dark/light palette on top of the stock 'clam' theme."""
        style.theme_use("clam")
        if name == "dark":
            bg, fg, field, sel, line = "#202020", "#e6e6e6", "#1a1a1a", "#2f5f8f", "#3a3a3a"
        else:
            bg, fg, field, sel, line = "#f3f3f3", "#1c1c1c", "#ffffff", "#cce4f7", "#d0d0d0"
        style.configure(".", background=bg, foreground=fg, fieldbackground=field, bordercolor=line,
                        lightcolor=bg, darkcolor=bg, troughcolor=field, focuscolor=sel)
        style.configure("TButton", background=line if name == "dark" else "#e5e5e5", padding=(8, 3))
        style.map("TButton", background=[("active", sel), ("disabled", bg)], foreground=[("disabled", "#777")])
        style.configure("Treeview", background=field, fieldbackground=field, foreground=fg)
        style.map("Treeview", background=[("selected", sel)], foreground=[("selected", fg)])
        style.configure("Treeview.Heading", background=line if name == "dark" else "#e5e5e5", foreground=fg)
        style.map("Treeview.Heading", background=[("active", sel)])
        style.configure("TLabelframe.Label", background=bg, foreground=fg)
        self.configure(background=bg)
        for w in self.winfo_children():
            if isinstance(w, tk.Toplevel):
                w.configure(background=bg)
        self.option_add("*Menu.background", field)
        self.option_add("*Menu.foreground", fg)
        self.menu.configure(background=field, foreground=fg, activebackground=sel, activeforeground=fg)

    def toggle_theme(self):
        self.apply_theme("light" if self.theme == "dark" else "dark")
        self.cfg["theme"] = self.theme
        self._save_cfg()

    def _themed_windows(self):
        return [self] + [w for w in self.winfo_children() if isinstance(w, tk.Toplevel)]

    def _themed_texts(self):
        out = [getattr(self, "logbox", None)]
        out += [w.assets for w in self.winfo_children() if isinstance(w, ConflictsDialog)]
        return [t for t in out if t is not None]

    def _themed_trees(self):
        out = [getattr(self, "tree", None)]
        for w in self.winfo_children():
            if isinstance(w, ConflictsDialog):
                out += [w.ctree, w.otree]
        return [t for t in out if t is not None]

    def log(self, msg):
        self.logbox.configure(state="normal")
        self.logbox.insert("end", msg + "\n")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def log_threadsafe(self, msg):
        self.events.put(("log", msg))

    def _pump(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    self.log(payload)
                elif kind == "done":
                    self._set_busy(False)
                    try:
                        payload()
                    except Exception as e:  # noqa: BLE001 — keep the pump alive
                        self.log(f"Ошибка: {e}")
                        self.redraw()
        except queue.Empty:
            pass
        self.after(100, self._pump)

    def _set_busy(self, busy):
        self.busy = busy
        for b in self.buttons:
            b.state(["disabled"] if busy else ["!disabled"])
        self.configure(cursor="watch" if busy else "")

    def background(self, work, then=None):
        """Runs work() off the UI thread; then(result) runs back on it."""
        if self.busy:
            return
        self._set_busy(True)

        def run():
            try:
                res = work()
                cb = (lambda: then(res)) if then else (lambda: None)
            except Exception as e:  # noqa: BLE001 — every failure goes to the log, not a crash
                err = e
                cb = lambda: self.log(f"Ошибка: {err}")
            self.events.put(("done", lambda: (cb(), self.redraw())))

        threading.Thread(target=run, daemon=True).start()

    def guarded(fn):
        def wrap(self, *a):
            if self.game is None:
                messagebox.showinfo("Нет игры", "Сначала выбери папку игры")
                return
            try:
                return fn(self, *a)
            except Exception as e:  # noqa: BLE001
                self.log(f"Ошибка: {e}")
                self.redraw()
        return wrap

    # ---------- view ----------

    def analyze(self):
        """Pak indexes are cached, so this is cheap enough to run on every redraw."""
        self.infos = {m.key: self.scanner.mod(m) for m in self.game.mods if m.files}
        enabled = [m for m in self.game.mods if m.enabled and m.key in self.infos]
        self.conflicts = analyze.find_conflicts(enabled, self.infos)

    def redraw(self):
        if not self.game:
            return
        self.analyze()
        per_mod = {}
        for c in self.conflicts:
            for k in (c.winner, c.loser):
                per_mod[k] = per_mod.get(k, 0) + 1
        sel = set(self.tree.selection())
        self.tree.delete(*self.tree.get_children())
        n = 0
        for m in self.game.mods:
            n += m.enabled
            info = self.infos.get(m.key)
            compat = analyze.compat_issue(info.engine, self.engine) if info else None
            status = compat or (f"не читается: {info.error}" if info and info.error else m.status)
            tags = ("off",) if not m.enabled else ()
            if (status and status != "актуален") or per_mod.get(m.key):
                tags += ("warn",)
            self.tree.insert("", "end", iid=m.key, tags=tags, values=(
                n if m.enabled else "", "✔" if m.enabled else "", m.title, m.wid or "",
                SOURCE_LABEL[m.source], info.engine if info else "", per_mod.get(m.key, ""), status))
        keep = [k for k in sel if self.tree.exists(k)]
        if keep:
            self.tree.selection_set(keep)

    def _popup(self, event):
        row = self.tree.identify_row(event.y)
        if row and row not in self.tree.selection():
            self.tree.selection_set(row)
        if self.tree.selection():
            self.menu.tk_popup(event.x_root, event.y_root)

    def copy(self, what):
        """Ctrl+C / context menu: one line per selected mod into the clipboard."""
        if not self.game:
            return
        out = []
        for k in self.selected():
            m = self.game.get(k)
            if what == "title":
                out.append(m.title)
            elif what == "wid" and m.wid:
                out.append(m.wid)
            elif what == "url" and m.wid:
                out.append(steam.workshop_url(m.wid))
            elif what == "path":
                out += [str(f) for f in m.files] or [m.raw_line or ""]
        if out:
            self.clipboard_clear()
            self.clipboard_append("\n".join(out))
            self.log(f"Скопировано: {out[0]}" + (f" (+{len(out) - 1})" if len(out) > 1 else ""))

    def selected(self):
        return list(self.tree.selection())

    # ---------- actions ----------

    def pick_game(self):
        d = filedialog.askdirectory(title="Папка Conan Exiles (где лежит ConanSandbox)")
        if d:
            self.open_game(d)

    def open_game(self, path):
        try:
            self.game = Game(path, log=self.log)
        except Exception as e:  # noqa: BLE001
            self.log(f"Ошибка: {e}")
            return
        self._save_cfg()
        ws = f" | Workshop: {self.game.workshop_dir}" if self.game.workshop_dir else " | без Steam Workshop"
        self.path_var.set(f"{self.game.root}{ws}")
        self.engine = analyze.game_engine(self.game)
        label = {"UE5": "Enhanced (UE5)", "UE4": "Legacy (UE4)"}.get(self.engine, "не определена")
        self.log(f"Модов найдено: {len(self.game.mods)}. Версия игры: {label}")
        self.redraw()

    @guarded
    def refresh(self):
        self.game.reload()
        self.game.apply_details(self.details) if self.details else None
        self.redraw()

    @guarded
    def toggle(self):
        keys = self.selected()
        for k in keys:
            m = self.game.get(k)
            m.enabled = not m.enabled
        if keys:
            self.game.save()
            self.redraw()

    @guarded
    def move(self, delta):
        keys = self.selected()
        order = sorted(keys, key=lambda k: self.game.mods.index(self.game.get(k)), reverse=delta > 0)
        for k in order:
            self.game.move(k, delta)
        self.redraw()
        self.tree.selection_set(keys)

    @guarded
    def remove(self):
        keys = self.selected()
        if not keys:
            return
        names = "\n".join(self.game.get(k).title for k in keys)
        if not messagebox.askyesno("Удалить", f"Удалить файлы модов?\n\n{names}"):
            return
        for k in keys:
            hint = self.game.remove(k)
            if hint:
                self.log(hint)
        self.redraw()

    @guarded
    def open_page(self):
        for k in self.selected():
            m = self.game.get(k)
            if m.wid:
                webbrowser.open(steam.workshop_url(m.wid))

    @guarded
    def link(self):
        keys = self.selected()
        if len(keys) != 1 or self.game.get(keys[0]).source != "local":
            messagebox.showinfo("Привязка", "Выбери один мод с источником «вручную»")
            return
        text = simpledialog.askstring("Привязка", "Workshop ID или ссылка на мод:", parent=self)
        if not text:
            return
        wid = steam.parse_workshop_id(text)
        self.game.link(keys[0], wid)
        self.log(f"Привязан к {wid}. «Проверить обновления» покажет, свежий ли файл.")
        self.redraw()

    @guarded
    def add(self):
        text = simpledialog.askstring(
            "Добавить мод", "Workshop ID или ссылки (можно несколько через пробел/перенос):", parent=self)
        if not text:
            return
        ids = list(dict.fromkeys(steam.parse_workshop_id(t) for t in re.split(r"[\s,;]+", text) if t))
        self.install(ids)

    def install(self, ids):
        game = self.game

        def work():
            details = steam.fetch_details(ids)
            bad = [i for i in ids if not details.get(i, {}).get("ok")]
            if bad:
                raise RuntimeError(f"Не моды Conan Exiles или недоступны: {', '.join(bad)}")
            for i in ids:
                self.log_threadsafe(f"Качаю {details[i]['title']} ({details[i]['file_size'] // 1024 // 1024} MB)")
            folders = self.steamcmd.download(ids)
            return details, folders

        def then(res):
            details, folders = res
            self.details.update(details)
            for wid, folder in folders.items():
                try:
                    m = game.install(wid, folder, details[wid])
                    self.log(f"Установлен: {m.title} → {', '.join(f.name for f in m.files)}")
                except Exception as e:  # noqa: BLE001 — one broken mod must not stop the rest
                    self.log(f"Ошибка: {e}")
                finally:
                    steam.SteamCmd.discard(folder)
            game.apply_details(self.details)

        self.background(work, then)

    @guarded
    def export(self):
        name = time.strftime("ConanMods-%Y%m%d-%H%M.zip")
        dest = filedialog.asksaveasfilename(
            title="Сохранить бэкап модов", initialfile=name, defaultextension=".zip",
            filetypes=[("Zip", "*.zip")])
        if not dest:
            return
        game = self.game
        self.log(f"Бэкап → {dest}")
        self.background(
            lambda: game.export_zip(dest, log=self.log_threadsafe),
            lambda total: self.log(f"Бэкап готов: {len(game.mods)} модов, {total // 1024 // 1024} MB → {dest}"))

    @guarded
    def show_conflicts(self):
        ConflictsDialog(self)

    @guarded
    def check(self):
        ids = [m.wid for m in self.game.mods if m.wid]
        if not ids:
            self.log("Нет модов с Workshop ID — нечего проверять")
            return

        def then(details):
            self.details = details
            self.game.apply_details(details)
            n = sum(m.status == "есть обнова" for m in self.game.mods)
            self.log(f"Проверено {len(ids)}, обновлений: {n}")

        self.background(lambda: steam.fetch_details(ids), then)

    @guarded
    def update_selected(self):
        ids = [self.game.get(k).wid for k in self.selected() if self.game.get(k).source == "managed"]
        if not ids:
            self.log("Обновлять можно только моды с источником «менеджер» (Steam обновляет свои сам)")
            return
        self.install(ids)

    @guarded
    def update_all(self):
        ids = [m.wid for m in self.game.mods if m.source == "managed" and m.status in ("есть обнова", "размер не совпал", "файлы пропали")]
        if not ids:
            self.log("Нечего обновлять. Сначала «Проверить обновления».")
            return
        self.install(ids)


class ConflictsDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Конфликты и порядок загрузки")
        self.geometry("900x620")
        self.transient(app)

        self.summary = ttk.Label(self, padding=6)
        self.summary.pack(fill="x")
        hint = ("Побеждает мод ниже в списке. Порядок: патчи — под модом, который они правят; "
                "узкие правки — под крупными модами. Enhanced-моды (UE5) упакованы иначе — их файлы не сравниваются.")
        ttk.Label(self, text=hint, style="Dim.TLabel", wraplength=870, padding=(6, 0)).pack(fill="x")

        top = ttk.Frame(self, padding=6)
        top.pack(fill="both", expand=True)
        self.ctree = ttk.Treeview(top, columns=("kind", "win", "lose", "n"), show="headings", height=8)
        for c, text, w in (("kind", "Тип", 220), ("win", "Побеждает (ниже)", 260), ("lose", "Перекрыт", 260), ("n", "Файлов", 70)):
            self.ctree.heading(c, text=text)
            self.ctree.column(c, width=w, stretch=c in ("win", "lose"))
        self.ctree.pack(fill="both", expand=True)
        self.ctree.bind("<<TreeviewSelect>>", self._show_assets)
        self.assets = tk.Text(top, height=6, wrap="none", font=("Consolas", 9), state="disabled")
        self.assets.pack(fill="x", pady=(6, 0))

        bottom = ttk.LabelFrame(self, text="Предложенный порядок (только включённые моды)", padding=6)
        bottom.pack(fill="both", expand=True, padx=6)
        self.otree = ttk.Treeview(bottom, columns=("n", "now", "new"), show="headings", height=8)
        for c, text, w in (("n", "#", 40), ("now", "Сейчас", 380), ("new", "Предложено", 380)):
            self.otree.heading(c, text=text)
            self.otree.column(c, width=w, stretch=c != "n")
        self.otree.pack(fill="both", expand=True)
        btns = ttk.Frame(self, padding=6)
        btns.pack(fill="x")
        self.apply_btn = ttk.Button(btns, text="Применить порядок", command=self.apply)
        self.apply_btn.pack(side="right")
        ttk.Button(btns, text="Закрыть", command=self.destroy).pack(side="right", padx=6)
        app.apply_theme(app.theme)
        self.refresh()

    def _title(self, key):
        return self.app.game.get(key).title

    def refresh(self):
        app = self.app
        app.analyze()
        enabled = [m for m in app.game.mods if m.enabled]
        pos = {m.key: i for i, m in enumerate(enabled)}
        self.ctree.delete(*self.ctree.get_children())
        self.by_iid = {}
        bad = 0
        for i, c in enumerate(app.conflicts):
            wrong = c.kind == "patch" and pos[c.winner] < pos[c.loser]
            bad += wrong
            label = analyze.KIND_LABEL[c.kind] + (" — патч выше мода!" if wrong else "")
            iid = str(i)
            self.by_iid[iid] = c
            self.ctree.insert("", "end", iid=iid, tags=("bad",) if wrong or c.kind == "duplicate" else (),
                              values=(label, self._title(c.winner), self._title(c.loser), len(c.assets)))
        unread = sum(1 for m in enabled if app.infos.get(m.key) and app.infos[m.key].error)
        ue5 = sum(1 for m in enabled if app.infos.get(m.key) and app.infos[m.key].engine == "UE5")
        self.summary.configure(text=(
            f"Включено модов: {len(enabled)}. Конфликтов: {len(app.conflicts)}"
            + (f", патчей не на месте: {bad}" if bad else "")
            + (f". Без проверки файлов (UE5): {ue5}" if ue5 else "")
            + (f". Не прочитано: {unread}" if unread else "")))

        self.suggested = analyze.suggest_order(enabled, app.infos, app.conflicts)
        self.otree.delete(*self.otree.get_children())
        for i, (m, key) in enumerate(zip(enabled, self.suggested), 1):
            self.otree.insert("", "end", tags=("moved",) if m.key != key else (),
                              values=(i, m.title, self._title(key)))
        changed = [m.key for m in enabled] != self.suggested
        self.apply_btn.state(["!disabled"] if changed else ["disabled"])
        self.apply_btn.configure(text="Применить порядок" if changed else "Порядок уже оптимален")

    def _show_assets(self, _):
        sel = self.ctree.selection()
        c = self.by_iid.get(sel[0]) if sel else None
        self.assets.configure(state="normal")
        self.assets.delete("1.0", "end")
        if c:
            self.assets.insert("end", "\n".join(sorted(c.assets)[:300]))
        self.assets.configure(state="disabled")

    def apply(self):
        game = self.app.game
        slots = [i for i, m in enumerate(game.mods) if m.enabled]
        by_key = {m.key: m for m in game.mods}
        for i, key in zip(slots, self.suggested):
            game.mods[i] = by_key[key]
        game.save()
        self.app.log("Применён предложенный порядок загрузки")
        self.app.redraw()
        self.refresh()


def main():
    App().mainloop()
