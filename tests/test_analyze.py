import hashlib
import struct
import tempfile
import unittest
from pathlib import Path

from conan_mm import analyze, pak
from conan_mm.core import Mod


def fstr(s):
    b = s.encode() + b"\0"
    return struct.pack("<i", len(b)) + b


def write_pak_v4(path, cooked_name, files):
    """Minimal Conan-style v4 pak: data region is irrelevant, index has Funcom's 4 extra bytes."""
    data = b"\0" * 16
    index = fstr(f"C:/Users/modder/AppData/Local/ConanSandbox/Saved/Mods/CookedMods/{cooked_name}/")
    index += struct.pack("<i", len(files))
    for name, content in files.items():
        index += fstr(name)
        index += struct.pack("<qqqi", 0, 1, 1, 0) + hashlib.sha1(content).digest()
        index += b"\0" + struct.pack("<I", 0) + b"\0\0\0\0"
    footer = struct.pack("<IiQQ", pak.MAGIC, 4, len(data), len(index)) + b"\0" * 20
    Path(path).write_bytes(data + index + footer)


class AnalyzeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        lib = {"ModsShared/Lib/Core.uasset": b"v1"}
        specs = {
            # big overhaul touching many base-game assets
            "Big": {"Mods/Big/A.uasset": b"a", "Systems/T1.uasset": b"1", "Systems/T2.uasset": b"2",
                    "Systems/T3.uasset": b"3", **lib},
            # small tweak touching one of them
            "Tweak": {"Mods/Tweak/B.uasset": b"b", "Systems/T2.uasset": b"x", "Systems/T2.uexp": b"x", **lib},
            # patch for Big, writes into Big's own folder
            "BigPatch": {"Mods/BigPatch/P.uasset": b"p", "Mods/Big/A.uasset": b"patched"},
            # carries an older copy of the shared library
            "OldLib": {"Mods/OldLib/C.uasset": b"c", "ModsShared/Lib/Core.uasset": b"v0"},
        }
        self.mods = []
        for name, files in specs.items():
            p = d / f"{name}.pak"
            write_pak_v4(p, name, files)
            self.mods.append(Mod(f"local:{name}.pak", "local", name, [p], enabled=True))
        # wrong order on purpose: patch and tweak above what they change
        self.mods = [self.mods[i] for i in (2, 1, 0, 3)]
        sc = analyze.Scanner()
        self.infos = {m.key: sc.mod(m) for m in self.mods}

    def tearDown(self):
        self.tmp.cleanup()

    def test_index_and_engine(self):
        info = self.infos["local:Big.pak"]
        self.assertEqual((info.version, info.engine, info.error), (4, "UE4", None))
        self.assertIn("systems/t1", info.assets)
        self.assertEqual(info.own, {"big"})
        self.assertEqual(analyze.compat_issue("UE4", "UE5"), "legacy_in_enhanced")
        self.assertIsNone(analyze.compat_issue("UE4", None))

    def test_conflicts(self):
        cs = analyze.find_conflicts(self.mods, self.infos)
        got = {(c.kind, c.winner, c.loser, tuple(sorted(c.assets))) for c in cs}
        self.assertEqual(got, {
            ("patch", "local:BigPatch.pak", "local:Big.pak", ("mods/big/a",)),
            ("override", "local:Big.pak", "local:Tweak.pak", ("systems/t2",)),
            ("shared", "local:OldLib.pak", "local:Big.pak", ("modsshared/lib/core",)),
            ("shared", "local:OldLib.pak", "local:Tweak.pak", ("modsshared/lib/core",)),
        })

    def test_suggest_order(self):
        cs = analyze.find_conflicts(self.mods, self.infos)
        order = analyze.suggest_order(self.mods, self.infos, cs)
        self.assertLess(order.index("local:Big.pak"), order.index("local:BigPatch.pak"))
        self.assertLess(order.index("local:Big.pak"), order.index("local:Tweak.pak"))
        # already-good order is left alone
        good = sorted(self.mods, key=lambda m: order.index(m.key))
        self.assertEqual(analyze.suggest_order(good, self.infos, analyze.find_conflicts(good, self.infos)), order)

    def test_duplicate(self):
        dup = Mod("steam:1", "steam", "Big again", self.mods[2].files, enabled=True)
        self.infos[dup.key] = self.infos["local:Big.pak"]
        cs = analyze.find_conflicts(self.mods + [dup], self.infos)
        self.assertEqual(cs[0].kind, "duplicate")

    def test_garbage_file(self):
        p = Path(self.tmp.name) / "junk.pak"
        p.write_bytes(b"nope" * 100)
        self.assertIn("signature", analyze.Scanner().info(p).error)


if __name__ == "__main__":
    unittest.main()
