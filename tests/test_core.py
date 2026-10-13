import json
import os
import tempfile
import unittest
from pathlib import Path

from conan_mm.core import Game


def make_layout(tmp):
    lib = Path(tmp) / "lib" / "steamapps"
    root = lib / "common" / "Conan Exiles"
    mods = root / "ConanSandbox" / "Mods"
    mods.mkdir(parents=True)
    ws = lib / "workshop" / "content" / "440900" / "111111"
    ws.mkdir(parents=True)
    (ws / "SteamMod.pak").write_bytes(b"s" * 10)
    (mods / "Local.pak").write_bytes(b"l" * 5)
    (mods / MODLIST_NAME).write_text(
        f"{ws / 'SteamMod.pak'}\n*Local.pak\nC:\\gone\\Missing.pak\n", encoding="utf-8")
    return root, mods, ws


MODLIST_NAME = "modlist.txt"


class GameTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root, self.mods, self.ws = make_layout(self.tmp.name)
        self.logs = []
        self.game = Game(self.mods, log=self.logs.append)  # picking Mods/ must find the root too

    def tearDown(self):
        self.tmp.cleanup()

    def modlist(self):
        return (self.mods / MODLIST_NAME).read_text(encoding="utf-8").splitlines()

    def keys(self):
        return [m.key for m in self.game.mods]

    def test_scan(self):
        self.assertEqual(self.game.root, self.root)
        self.assertEqual(self.game.workshop_dir, self.ws.parent)
        self.assertEqual(self.keys(), ["steam:111111", "local:Local.pak", "missing:C:\\gone\\Missing.pak"])
        self.assertTrue(all(m.enabled for m in self.game.mods))

    def test_toggle_backup_and_order(self):
        self.game.set_enabled("local:Local.pak", False)
        self.assertTrue((self.mods / "modlist.txt.bak").exists())
        self.assertEqual(self.modlist(), [str(self.ws / "SteamMod.pak"), "C:\\gone\\Missing.pak"])
        self.game.set_enabled("local:Local.pak", True)
        self.game.move("local:Local.pak", -1)
        self.assertEqual(self.modlist()[:2], ["*Local.pak", str(self.ws / "SteamMod.pak")])
        # survives a rescan
        self.game.reload()
        self.assertEqual(self.keys()[:2], ["local:Local.pak", "steam:111111"])

    def test_disabled_keeps_slot_and_external_reorder_wins(self):
        (self.mods / "Other.pak").write_bytes(b"o")
        self.game.reload()
        self.game.set_enabled("local:Local.pak", False)
        self.game.set_enabled("local:Other.pak", True)
        lines = self.modlist()
        # someone edits modlist.txt by hand: Other before Steam
        (self.mods / MODLIST_NAME).write_text("\n".join([lines[1], lines[0]]) + "\n", encoding="utf-8")
        self.game.reload()
        self.assertEqual(self.keys(), ["local:Other.pak", "local:Local.pak", "steam:111111"])
        self.assertFalse(self.game.get("local:Local.pak").enabled)

    def test_install_update_remove(self):
        dl = Path(self.tmp.name) / "dl"
        dl.mkdir()
        (dl / "Pippi.pak").write_bytes(b"p" * 7)
        (self.mods / "Pippi.pak").write_bytes(b"old")  # hand-dropped copy of the same mod
        self.game.reload()
        self.game.install("880454836", dl, {"title": "Pippi", "time_updated": 100})
        self.assertNotIn("local:Pippi.pak", self.keys())
        self.assertEqual((self.mods / "Pippi.pak").read_bytes(), b"p" * 7)
        self.assertIn("*Pippi.pak", self.modlist())

        self.game.apply_details({"880454836": {"ok": True, "title": "Pippi", "time_updated": 200, "file_size": 7},
                                 "111111": {"ok": True, "title": "Steam One", "time_updated": 1, "file_size": 10}})
        self.assertEqual(self.game.get("ws:880454836").status, "есть обнова")
        self.assertEqual(self.game.get("steam:111111").title, "Steam One")

        # new version renamed its pak: the old file must go
        (dl / "Pippi.pak").unlink()
        (dl / "Pippi2.pak").write_bytes(b"x" * 7)
        self.game.install("880454836", dl, {"title": "Pippi", "time_updated": 200})
        self.assertFalse((self.mods / "Pippi.pak").exists())
        self.assertTrue((self.mods / "Pippi2.pak").exists())

        self.game.remove("ws:880454836")
        self.assertFalse((self.mods / "Pippi2.pak").exists())
        self.assertNotIn("880454836", json.loads((self.mods / "conan-mod-manager.json").read_text())["mods"])
        self.assertFalse(any("Pippi" in ln for ln in self.modlist()))

    def test_remove_steam_only_disables(self):
        hint = self.game.remove("steam:111111")
        self.assertIn("отпишись", hint)
        self.assertTrue((self.ws / "SteamMod.pak").exists())
        self.assertFalse(self.game.get("steam:111111").enabled)

    def test_link_local(self):
        self.game.link("local:Local.pak", "222222")
        self.game.reload()
        m = self.game.get("ws:222222")
        self.assertEqual(m.source, "managed")
        self.assertTrue(m.enabled)

    def test_export_zip(self):
        import zipfile
        self.game.set_enabled("local:Local.pak", False)
        dest = Path(self.tmp.name) / "b.zip"
        total = self.game.export_zip(dest)
        self.assertEqual(total, 15)
        with zipfile.ZipFile(dest) as zf:
            self.assertEqual(sorted(zf.namelist()),
                             ["Mods/Local.pak", "Workshop/111111/SteamMod.pak", "backup.json", "modlist.txt"])
            meta = json.loads(zf.read("backup.json"))
        self.assertEqual([(m["key"], m["enabled"]) for m in meta["mods"]],
                         [("steam:111111", True), ("local:Local.pak", False), ("missing:C:\\gone\\Missing.pak", True)])
        self.assertFalse(Path(str(dest) + ".tmp").exists())

    def test_pirate_layout_without_workshop(self):
        root = Path(self.tmp.name) / "Conan Exiles"
        (root / "ConanSandbox" / "Mods").mkdir(parents=True)
        g = Game(root)
        self.assertIsNone(g.workshop_dir)
        self.assertEqual(g.mods, [])


if __name__ == "__main__":
    unittest.main()
