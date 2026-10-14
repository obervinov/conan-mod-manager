"""Mod state for one Conan Exiles install: what is on disk, what modlist.txt loads, in which order.

Three kinds of mods are handled side by side:
  managed  - installed by this tool into ConanSandbox/Mods (with or without the Steam client)
  steam    - subscribed in the Steam client, live in steamapps/workshop/content/440900
  local    - a .pak dropped into ConanSandbox/Mods by hand, origin unknown until linked to an id
modlist.txt is the only thing the game reads: listed = enabled, line order = load order.
"""
import json
import os
import shutil
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .i18n import t

MANIFEST = "conan-mod-manager.json"
MODLIST = "modlist.txt"
# The game unpacks enabled mods into ConanSandbox/Saved and rebuilds all of this from the paks.
EXTRACTED = "ExtractedMods"
CACHE_DIRS = ("ExtractedMods", "ModsCached")
CACHE_FILES = ("ModControllerCache.json", "Modrestartdata.json")


def _norm(p):
    return os.path.normcase(os.path.normpath(str(p)))


def find_game_root(picked):
    """User may point at the game folder, ConanSandbox, or ConanSandbox/Mods."""
    p = Path(picked)
    for cand in (p, p.parent, p.parent.parent):
        if (cand / "ConanSandbox").is_dir():
            return cand
    raise ValueError(t("core.no_sandbox", p=p))


@dataclass
class Mod:
    key: str
    source: str  # managed | steam | local | missing
    title: str
    files: list = field(default_factory=list)
    wid: str = None
    enabled: bool = False
    installed_at: int = 0  # workshop time_updated of the installed copy
    status: str = ""  # code: ok | update | steam_updates | size_mismatch | missing_files | no_file | not_in_workshop
    raw_line: str = None  # modlist line we could not resolve (missing)

    @property
    def size(self):
        return sum(f.stat().st_size for f in self.files if f.exists())


class Game:
    def __init__(self, picked, log=print):
        self.root = find_game_root(picked)
        self.mods_dir = self.root / "ConanSandbox" / "Mods"
        self.mods_dir.mkdir(parents=True, exist_ok=True)
        self.modlist_path = self.mods_dir / MODLIST
        self.saved_dir = self.root / "ConanSandbox" / "Saved"
        self.manifest_path = self.mods_dir / MANIFEST
        common = self.root.parent
        self.workshop_dir = None
        if common.name.lower() == "common" and common.parent.name.lower() == "steamapps":
            wd = common.parent / "workshop" / "content" / "440900"
            self.workshop_dir = wd if wd.is_dir() else None
        self.log = log
        self.mods = []
        self.reload()

    # ---------- persistence ----------

    def _load_manifest(self):
        if self.manifest_path.exists():
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        else:
            data = {}
        data.setdefault("mods", {})
        data.setdefault("order", [])
        return data

    def _write(self, path, text):
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)

    def _read_modlist(self):
        if not self.modlist_path.exists():
            return []
        raw = self.modlist_path.read_text(encoding="utf-8-sig", errors="replace")
        return [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith("#")]

    def _resolve_line(self, line):
        p = line.lstrip("*")
        path = Path(p)
        return path if path.is_absolute() else self.mods_dir / path

    def _line(self, f):
        """`*Name.pak` = relative to ConanSandbox/Mods (the documented form), else absolute."""
        return f"*{f.name}" if f.parent == self.mods_dir else str(f)

    def save(self):
        """Writes modlist.txt (enabled mods, in order) and the manifest."""
        if not self.manifest_path.exists() and self.modlist_path.exists():
            backup = self.modlist_path.with_name(MODLIST + ".bak")
            if not backup.exists():
                shutil.copy2(self.modlist_path, backup)
                self.log(t("core.backup", name=backup.name))
        lines = []
        for m in self.mods:
            if not m.enabled:
                continue
            if m.source == "missing":
                lines.append(m.raw_line)
            else:
                lines += [self._line(f) for f in m.files]
        self._write(self.modlist_path, "".join(ln + "\n" for ln in lines))
        self.manifest["order"] = [m.key for m in self.mods if m.source != "missing"]
        self._write(self.manifest_path, json.dumps(self.manifest, indent=2, ensure_ascii=False))

    # ---------- scan ----------

    def reload(self):
        self.manifest = self._load_manifest()
        found = {}
        owned = set()

        for wid, info in self.manifest["mods"].items():
            files = [self.mods_dir / name for name in info.get("files", [])]
            owned |= {_norm(f) for f in files}
            m = Mod(f"ws:{wid}", "managed", info.get("title") or f"#{wid}", files, wid,
                    installed_at=int(info.get("time_updated") or 0))
            if not any(f.exists() for f in files):
                m.status = "missing_files"
            found[m.key] = m

        if self.workshop_dir:
            for d in sorted(self.workshop_dir.iterdir()):
                paks = sorted(d.rglob("*.pak")) if d.is_dir() else []
                if paks:
                    title = self.manifest.get("steam_titles", {}).get(d.name) or paks[0].stem
                    m = Mod(f"steam:{d.name}", "steam", title, paks, d.name,
                            installed_at=int(max(p.stat().st_mtime for p in paks)))
                    found[m.key] = m

        for pak in sorted(self.mods_dir.glob("*.pak")):
            if _norm(pak) not in owned:
                found[f"local:{pak.name}"] = Mod(f"local:{pak.name}", "local", pak.stem, [pak])

        by_file = {_norm(f): m for m in found.values() for f in m.files}
        enabled_order, missing = [], []
        for line in self._read_modlist():
            m = by_file.get(_norm(self._resolve_line(line)))
            if m is None:
                missing.append(Mod(f"missing:{line}", "missing", Path(line.lstrip("*")).name,
                                   enabled=True, raw_line=line, status="no_file"))
                continue
            m.enabled = True
            if m not in enabled_order:
                enabled_order.append(m)

        # Order: manifest order, new mods appended; then enabled mods are re-sorted
        # into their own slots by modlist.txt, so an external edit of the load order wins.
        order = [found.pop(k) for k in self.manifest["order"] if k in found] + list(found.values())
        slots = [i for i, m in enumerate(order) if m.enabled]
        for i, m in zip(slots, enabled_order):
            order[i] = m
        self.mods = order + missing

    # ---------- edits ----------

    def get(self, key):
        return next(m for m in self.mods if m.key == key)

    def set_enabled(self, key, value):
        self.get(key).enabled = value
        self.save()

    def move(self, key, delta):
        i = self.mods.index(self.get(key))
        j = max(0, min(len(self.mods) - 1, i + delta))
        self.mods.insert(j, self.mods.pop(i))
        self.save()

    def remove(self, key):
        """Deletes a mod completely. Returns "steam_hint" when only disabling was possible."""
        m = self.get(key)
        if m.source == "steam":
            m.enabled = False
            self.save()
            return "steam_hint"
        for f in m.files:
            if f.exists():
                f.unlink()
                self.log(t("core.deleted", name=f.name))
        self.purge_extracted([f.name for f in m.files])
        if m.source == "managed":
            self.manifest["mods"].pop(m.wid, None)
        self.mods.remove(m)
        self.save()
        return None

    def link(self, key, wid, title=None):
        """Turns a hand-dropped .pak into a managed mod so updates can be tracked."""
        m = self.get(key)
        if m.source != "local":
            raise ValueError(t("core.link_local_only"))
        if wid in self.manifest["mods"]:
            raise ValueError(t("core.already", wid=wid))
        self.manifest["mods"][wid] = {"title": title or m.title, "files": [m.files[0].name], "time_updated": 0}
        idx = self.mods.index(m)
        m.key, m.source, m.wid, m.title = f"ws:{wid}", "managed", wid, title or m.title
        self.mods[idx] = m
        self.save()

    # ---------- game's mod cache ----------

    @staticmethod
    def _rm(path):
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()

    def _child(self, name):
        """Case-insensitive lookup inside Saved/, as on Windows."""
        if not self.saved_dir.is_dir():
            return None
        return next((c for c in self.saved_dir.iterdir() if c.name.lower() == name.lower()), None)

    def extracted_for(self, pak_names):
        """Entries of Saved/ExtractedMods that belong to these paks.

        Matched by name on the first two levels: `Name`, `Name.<ext>` or `Name-<platform>…`
        for a pak `Name.pak`. A miss only means the game keeps an extra copy; a wrong hit only
        means the game unpacks that mod again on the next start.
        """
        root = self._child(EXTRACTED)
        stems = {Path(n).stem.lower() for n in pak_names}
        if not root or not stems:
            return []

        def hit(name):
            n = name.lower()
            return any(n == s or n.startswith((s + ".", s + "-")) for s in stems)

        out = []
        for entry in root.iterdir():
            if hit(entry.name):
                out.append(entry)
            elif entry.is_dir():
                out += [e for e in entry.iterdir() if hit(e.name)]
        return out

    def purge_extracted(self, pak_names):
        removed = []
        for entry in self.extracted_for(pak_names):
            try:
                self._rm(entry)
            except OSError as e:  # locked by a running game: not worth failing an install for
                self.log(t("log.error", e=e))
                continue
            removed.append(entry.name)
            self.log(t("core.cache_removed", name=entry.name))
        return removed

    def cache_entries(self):
        """Everything the game rebuilds from the paks: unpacked mods and mod caches."""
        out = [c for c in (self._child(n) for n in CACHE_DIRS) if c]
        out += [c for c in (self._child(n) for n in CACHE_FILES) if c]
        return out

    def clear_cache(self):
        """Wipes the game's mod cache. Returns (entries removed, bytes freed)."""
        removed, freed = [], 0
        for entry in self.cache_entries():
            files = [entry] if entry.is_file() else [f for f in entry.rglob("*") if f.is_file()]
            freed += sum(f.stat().st_size for f in files)
            self._rm(entry)
            removed.append(entry.name)
        return removed, freed

    def export_zip(self, dest, log=None):
        """Dumps every mod file + modlist.txt + a self-describing backup.json into one zip.

        Layout: Mods/<pak> for managed/local mods, Workshop/<id>/<pak> for Steam ones,
        so the zip is enough to rebuild the setup on another PC.
        """
        log = log or self.log
        dest = Path(dest)
        tmp = dest.with_name(dest.name + ".tmp")
        entries, total = [], 0
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
            for m in self.mods:
                arc = []
                for f in m.files:
                    if not f.exists():
                        continue
                    name = f"Workshop/{m.wid}/{f.name}" if m.source == "steam" else f"Mods/{f.name}"
                    log(f"zip: {name} ({f.stat().st_size // 1024 // 1024} MB)")
                    zf.write(f, name)
                    arc.append(name)
                    total += f.stat().st_size
                entries.append({"key": m.key, "source": m.source, "wid": m.wid, "title": m.title,
                                "enabled": m.enabled, "files": arc, "raw_line": m.raw_line})
            if self.modlist_path.exists():
                zf.write(self.modlist_path, MODLIST)
            zf.writestr("backup.json", json.dumps({
                "format": 1, "created": int(time.time()), "game_root": str(self.root),
                "manifest": self.manifest, "mods": entries}, indent=2, ensure_ascii=False))
        os.replace(tmp, dest)
        return total

    def install(self, wid, folder, details):
        """Moves freshly downloaded paks from steamcmd's folder into ConanSandbox/Mods."""
        paks = sorted(Path(folder).rglob("*.pak"))
        if not paks:
            raise RuntimeError(t("core.no_paks", wid=wid))
        others = {name for k, info in self.manifest["mods"].items() if k != wid for name in info["files"]}
        clash = [p.name for p in paks if p.name in others]
        if clash:
            raise RuntimeError(t("core.clash", wid=wid, name=clash[0]))
        old = set(self.manifest["mods"].get(wid, {}).get("files", []))
        # stale unpacked copy of the previous version: let the game unpack the new one
        self.purge_extracted(sorted(old | {p.name for p in paks}))
        for p in paks:
            shutil.copy2(p, self.mods_dir / p.name)
        for stale in old - {p.name for p in paks}:
            (self.mods_dir / stale).unlink(missing_ok=True)
        self.manifest["mods"][wid] = {
            "title": details.get("title") or f"#{wid}",
            "files": [p.name for p in paks],
            "time_updated": details.get("time_updated") or int(time.time()),
        }
        key = f"ws:{wid}"
        was = next((m for m in self.mods if m.key == key), None)
        # A pak with the same name may have been sitting there as "local"; it is this mod now.
        names = {p.name for p in paks}
        self.mods = [m for m in self.mods if not (m.source == "local" and m.files[0].name in names)]
        new = Mod(key, "managed", self.manifest["mods"][wid]["title"],
                  [self.mods_dir / p.name for p in paks], wid,
                  enabled=was.enabled if was else True, installed_at=self.manifest["mods"][wid]["time_updated"])
        if was:
            self.mods[self.mods.index(was)] = new
        else:
            self.mods.append(new)
        self.save()
        return new

    def apply_details(self, details):
        """Sets update status from a fetch_details() result."""
        titles = self.manifest.setdefault("steam_titles", {})
        for m in self.mods:
            d = details.get(m.wid) if m.wid else None
            if m.source in ("local", "missing"):
                continue
            if not d or not d["ok"]:
                m.status = "not_in_workshop"
                continue
            if m.source == "steam":
                titles[m.wid] = d["title"]
            m.title = d["title"]
            if m.status == "missing_files":
                continue
            if d["time_updated"] > m.installed_at:
                m.status = "update" if m.source == "managed" else "steam_updates"
            elif m.source == "managed" and d["file_size"] and m.size != d["file_size"]:
                m.status = "size_mismatch"
            else:
                m.status = "ok"
        for m in self.mods:
            if m.source == "managed":
                self.manifest["mods"][m.wid]["title"] = m.title
        self.save()
