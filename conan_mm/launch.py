"""Starting the game: through Steam, the game exe directly, or the user's own file (a .bat with debug args)."""
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

from .steam import APP_ID

MODES = ("steam", "exe", "custom")
GAME_EXE = Path("ConanSandbox") / "Binaries" / "Win64" / "ConanSandbox.exe"
STEAM_URL = f"steam://rungameid/{APP_ID}"


def normalize(cfg):
    """The stored launch settings with defaults filled in."""
    cfg = dict(cfg or {})
    mode = cfg.get("mode")
    return {
        "mode": mode if mode in MODES else "steam",
        "path": str(cfg.get("path") or "").strip().strip('"'),
        "args": str(cfg.get("args") or "").strip(),
    }


def plan(cfg, game_root):
    """What to start, without starting it.

    Returns one of:
      {"kind": "url", "target": "steam://…"}
      {"kind": "open", "target": path}                     — .lnk: Windows resolves the shortcut itself
      {"kind": "process", "cmdline": str, "cwd": dir, "console": bool}

    `args` is passed through verbatim, the way it would be typed after the program
    in a .bat, so quoting stays the user's (no re-splitting that would mangle it).
    Raises ValueError when the chosen file is not there.
    """
    cfg = normalize(cfg)
    mode, args = cfg["mode"], cfg["args"]
    if mode == "steam":
        return {"kind": "url", "target": STEAM_URL}
    target = Path(game_root) / GAME_EXE if mode == "exe" else Path(cfg["path"])
    if mode == "custom" and not cfg["path"]:
        raise ValueError("no file chosen")
    if not target.is_file():
        raise ValueError(f"not found: {target}")
    ext = target.suffix.lower()
    if ext == ".lnk":
        return {"kind": "open", "target": str(target)}
    exe = f'"{target}"' + (f" {args}" if args else "")
    if ext in (".bat", ".cmd"):
        # cmd /c strips the outer quote pair, so a quoted path plus quoted args survive intact
        return {"kind": "process", "cmdline": f'cmd.exe /c "{exe}"', "cwd": str(target.parent), "console": True}
    return {"kind": "process", "cmdline": exe, "cwd": str(target.parent), "console": False}


def run(p):
    """Starts what plan() described and returns immediately (the game is not awaited)."""
    if p["kind"] == "url":
        if sys.platform == "win32":
            os.startfile(p["target"])  # noqa: S606 — steam:// handler registered by the Steam client
        else:
            webbrowser.open(p["target"])
    elif p["kind"] == "open":
        os.startfile(p["target"])  # noqa: S606
    else:
        flags, quiet = 0, {}
        if sys.platform == "win32":
            # a .bat gets its own console so its echo/pause stay visible; the game itself detaches
            flags = subprocess.CREATE_NEW_CONSOLE if p["console"] else subprocess.DETACHED_PROCESS
            flags |= subprocess.CREATE_NEW_PROCESS_GROUP
        if not p["console"]:
            quiet = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        subprocess.Popen(p["cmdline"], cwd=p["cwd"], creationflags=flags, close_fds=True,  # noqa: S603
                         shell=sys.platform != "win32", **quiet)
