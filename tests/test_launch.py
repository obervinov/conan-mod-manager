import tempfile
import unittest
from pathlib import Path

from conan_mm import launch


class LaunchPlanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "Conan Exiles"
        exe = self.root / launch.GAME_EXE
        exe.parent.mkdir(parents=True)
        exe.write_bytes(b"")
        self.exe = exe

    def tearDown(self):
        self.tmp.cleanup()

    def _file(self, name):
        f = Path(self.tmp.name) / "my tools" / name
        f.parent.mkdir(exist_ok=True)
        f.write_text("@echo off\n")
        return f

    def test_default_is_steam(self):
        for cfg in (None, {}, {"mode": "bogus"}):
            self.assertEqual(launch.plan(cfg, self.root), {"kind": "url", "target": "steam://rungameid/440900"})

    def test_game_exe_with_args(self):
        p = launch.plan({"mode": "exe", "args": "-log -windowed"}, self.root)
        self.assertEqual(p["kind"], "process")
        self.assertEqual(p["cmdline"], f'"{self.exe}" -log -windowed')
        self.assertEqual(p["cwd"], str(self.exe.parent))
        self.assertFalse(p["console"])

    def test_bat_runs_through_cmd_in_own_console(self):
        bat = self._file("debug run.bat")
        p = launch.plan({"mode": "custom", "path": f'"{bat}"', "args": '-log "-ini:Engine:[Core.Log]"'}, self.root)
        self.assertEqual(p["cmdline"], f'cmd.exe /c ""{bat}" -log "-ini:Engine:[Core.Log]""')
        self.assertEqual(p["cwd"], str(bat.parent))
        self.assertTrue(p["console"])

    def test_bat_without_args(self):
        bat = self._file("go.CMD")
        self.assertEqual(launch.plan({"mode": "custom", "path": str(bat)}, self.root)["cmdline"],
                         f'cmd.exe /c ""{bat}""')

    def test_shortcut_is_opened(self):
        lnk = self._file("Conan.lnk")
        self.assertEqual(launch.plan({"mode": "custom", "path": str(lnk), "args": "-x"}, self.root),
                         {"kind": "open", "target": str(lnk)})

    def test_missing_files(self):
        with self.assertRaises(ValueError):
            launch.plan({"mode": "custom", "path": ""}, self.root)
        with self.assertRaises(ValueError):
            launch.plan({"mode": "custom", "path": str(Path(self.tmp.name) / "nope.bat")}, self.root)
        self.exe.unlink()
        with self.assertRaises(ValueError):
            launch.plan({"mode": "exe"}, self.root)


if __name__ == "__main__":
    unittest.main()
