"""Tkinter window. Network/steamcmd work runs in a worker thread, the UI polls a queue."""
import json
import queue
import re
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import __version__, steam
from .core import Game

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
        self.steamcmd = steam.SteamCmd(self.data_dir / "steamcmd", log=self.log_threadsafe)
        self._build()
        self.after(100, self._pump)
        cfg = self._load_cfg()
        start = cfg.get("game_dir") or detect_game_dir()
        if start:
            self.open_game(start)

    # ---------- layout ----------

    def _build(self):
        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")
        ttk.Label(top, text="Папка игры:").pack(side="left")
        self.path_var = tk.StringVar(value="не выбрана")
        ttk.Label(top, textvariable=self.path_var, foreground="#555").pack(side="left", padx=6, fill="x", expand=True)
        ttk.Button(top, text="Выбрать…", command=self.pick_game).pack(side="right")

        mid = ttk.Frame(self, padding=(6, 0))
        mid.pack(fill="both", expand=True)
        cols = ("n", "on", "title", "wid", "src", "status")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="extended")
        for c, text, w, anchor in (
            ("n", "#", 40, "e"), ("on", "Вкл", 45, "center"), ("title", "Мод", 420, "w"),
            ("wid", "Workshop ID", 110, "w"), ("src", "Источник", 90, "w"), ("status", "Статус", 150, "w"),
        ):
            self.tree.heading(c, text=text)
            self.tree.column(c, width=w, anchor=anchor, stretch=(c == "title"))
        self.tree.tag_configure("off", foreground="#999")
        self.tree.tag_configure("warn", foreground="#b35c00")
        sb = ttk.Scrollbar(mid, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tree.bind("<Double-1>", lambda e: self.toggle())
        self.tree.bind("<space>", lambda e: self.toggle())

        side = ttk.Frame(mid, padding=(8, 0))
        side.pack(side="left", fill="y")
        self.buttons = []
        for text, cmd in (
            ("Добавить по ID/ссылке", self.add),
            ("Вкл / выкл", self.toggle),
            ("▲ Выше", lambda: self.move(-1)),
            ("▼ Ниже", lambda: self.move(1)),
            (None, None),
            ("Проверить обновления", self.check),
            ("Обновить выбранные", self.update_selected),
            ("Обновить все", self.update_all),
            (None, None),
            ("Привязать к Workshop ID", self.link),
            ("Открыть в Workshop", self.open_page),
            ("Удалить", self.remove),
            (None, None),
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
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cfg_path.write_text(json.dumps({"game_dir": str(self.game.root)}), encoding="utf-8")

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

    def redraw(self):
        if not self.game:
            return
        sel = set(self.tree.selection())
        self.tree.delete(*self.tree.get_children())
        n = 0
        for m in self.game.mods:
            n += m.enabled
            tags = ("off",) if not m.enabled else ()
            if m.status and m.status != "актуален":
                tags += ("warn",)
            self.tree.insert("", "end", iid=m.key, tags=tags, values=(
                n if m.enabled else "", "✔" if m.enabled else "", m.title, m.wid or "",
                SOURCE_LABEL[m.source], m.status))
        keep = [k for k in sel if self.tree.exists(k)]
        if keep:
            self.tree.selection_set(keep)

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
        self.log(f"Модов найдено: {len(self.game.mods)}")
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


def main():
    App().mainloop()
