"""Compatibility, conflicts and a suggested load order, built from the .pak indexes.

Asset paths inside a cooked mod fall into three groups:
  Mods/<Name>/...      the mod's own namespace - never a conflict, unless the same mod is installed twice;
                       another mod writing into it is a patch and has to load after it
  ModsShared/<Lib>/... shared libraries copied into many mods - fine if byte-identical (same SHA1)
  anything else        an override of a base-game asset - two mods touching it is a real conflict,
                       the one lower in modlist.txt wins
Enhanced (UE5) mods are containers with IoStore packages inside, their assets are not listed
in the outer index, so they only get the engine check.
"""
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from . import pak

IGNORED = {"modinfo.json", "preview.png", "manifest.json"}
_COOKED = re.compile(r"^.*?/cookedmods/[^/]+/")


@dataclass
class PakInfo:
    version: int = 0
    engine: str = "?"
    assets: dict = field(default_factory=dict)  # normalized asset key -> sha1 or None
    own: set = field(default_factory=set)  # lower-case names of Mods/<Name> this mod owns
    error: str = None


@dataclass
class Conflict:
    winner: str  # mod key that wins: lower in the load order (for a patch: the patch itself)
    loser: str
    kind: str  # override | shared | duplicate
    assets: list = field(default_factory=list)


KIND_LABEL = {
    "override": "оба меняют файлы игры",
    "patch": "патч поверх другого мода",
    "shared": "разные версии общей библиотеки",
    "duplicate": "один и тот же мод дважды",
}


def normalize(path):
    p = path.replace("\\", "/").lower()
    p = _COOKED.sub("", p)
    for prefix in ("conansandbox/content/", "conansandbox/", "content/"):
        if p.startswith(prefix):
            p = p[len(prefix):]
    return pak.asset_key(p)


def category(key):
    if key.startswith("mods/"):
        return "mod"
    if key.startswith("modsshared/"):
        return "shared"
    return "override"


def _mod_folder(key):
    return key.split("/")[1] if key.count("/") >= 2 else ""


class Scanner:
    """Caches pak indexes by (path, size, mtime) so re-analysis after a reorder is free."""

    def __init__(self):
        self.cache = {}

    def info(self, path):
        try:
            st = os.stat(path)
        except OSError as e:
            return PakInfo(error=str(e))
        sig = (str(path), st.st_size, st.st_mtime_ns)
        if sig not in self.cache:
            self.cache[sig] = self._read(path)
        return self.cache[sig]

    @staticmethod
    def _read(path):
        try:
            idx = pak.read_index(path)
        except (pak.PakError, OSError) as e:
            return PakInfo(error=str(e))
        assets, own = {}, set()
        for name, sha in idx["files"].items():
            m = re.search(r"/cookedmods/([^/]+)/", name.lower())
            if m:
                own.add(m.group(1))
            if Path(name).name.lower() in IGNORED:
                continue
            assets[normalize(name)] = sha
        if idx["version"] >= pak.UE5_MIN_VERSION:
            assets = {}  # container: inner IoStore packages are opaque
        return PakInfo(idx["version"], pak.engine(idx["version"]), assets, own)

    def mod(self, mod):
        """Merges all paks of one mod."""
        infos = [self.info(f) for f in mod.files]
        out = PakInfo()
        for i in infos:
            if i.error:
                out.error = i.error
                continue
            out.version = max(out.version, i.version)
            out.engine = i.engine
            out.assets.update(i.assets)
            out.own |= i.own
        return out


def game_engine(game):
    """Engine of the installed game, read from its own content paks."""
    paks_dir = game.root / "ConanSandbox" / "Content" / "Paks"
    for p in sorted(paks_dir.glob("*.pak")) if paks_dir.is_dir() else []:
        try:
            return pak.engine(pak.read_version(p))
        except (pak.PakError, OSError):
            continue
    return None


def compat_issue(mod_engine, engine):
    if not engine or mod_engine == "?" or mod_engine == engine:
        return None
    if engine == "UE5":
        return "Legacy-мод: Enhanced его не загрузит"
    return "мод для Enhanced: эта версия игры не загрузит"


def find_conflicts(mods, infos):
    """mods: enabled mods in load order. Returns [Conflict], one per (pair, kind)."""
    owners = defaultdict(list)  # asset -> [(position, mod key, sha)]
    for pos, m in enumerate(mods):
        info = infos.get(m.key)
        if not info:
            continue
        for key, sha in info.assets.items():
            owners[key].append((pos, m.key, sha))
    pairs = {}
    for key, own in owners.items():
        if len(own) < 2:
            continue
        cat = category(key)
        for i in range(len(own)):
            for j in range(i + 1, len(own)):
                (_, a, sa), (_, b, sb) = own[i], own[j]
                if cat == "mod":
                    folder = _mod_folder(key)
                    oa, ob = folder in infos[a].own, folder in infos[b].own
                    kind = "duplicate" if oa and ob else "patch" if oa or ob else "override"
                    if kind == "patch":  # winner = the patch, loser = the mod it patches
                        a, b = (b, a) if oa else (a, b)
                        pairs.setdefault((a, b, kind), Conflict(a, b, kind)).assets.append(key)
                        continue
                elif cat == "shared":
                    if sa and sa == sb:
                        continue  # identical copy of the library
                    kind = "shared"
                else:
                    kind = "override"
                c = pairs.setdefault((b, a, kind), Conflict(b, a, kind))
                c.assets.append(key)
    order = {"duplicate": 0, "patch": 1, "override": 2, "shared": 3}
    return sorted(pairs.values(), key=lambda c: (order[c.kind], -len(c.assets)))


def suggest_order(mods, infos, conflicts):
    """Stable topological sort of the enabled mods.

    A patch goes below the mod it patches. For every override conflict the more specific
    mod (fewer overridden base-game assets, i.e. a tweak) goes below the broader one so it
    wins. Mods without conflicts keep their relative position.
    """
    pos = {m.key: i for i, m in enumerate(mods)}
    weight = {m.key: sum(category(k) == "override" for k in infos.get(m.key, PakInfo()).assets) for m in mods}
    after = defaultdict(set)  # key -> keys that must load before it
    for c in conflicts:
        if c.kind == "patch":
            after[c.winner].add(c.loser)
            continue
        if c.kind != "override":
            continue
        a, b = c.winner, c.loser
        broad, narrow = sorted((a, b), key=lambda k: (-weight[k], pos[k]))
        after[narrow].add(broad)
    done, out = set(), []
    remaining = [m.key for m in mods]
    while remaining:
        ready = next((k for k in remaining if after[k] <= done), remaining[0])
        remaining.remove(ready)
        done.add(ready)
        out.append(ready)
    return out

