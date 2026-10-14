import re
import unittest
from pathlib import Path

from conan_mm import i18n

SRC = Path(__file__).resolve().parent.parent / "conan_mm"


class I18nTest(unittest.TestCase):
    def test_every_used_key_exists(self):
        used = set()
        for f in (p for p in SRC.glob("*.py") if p.name != "i18n.py"):
            used |= set(re.findall(r'\bt\("([a-z_.0-9A-Z]+)"', f.read_text(encoding="utf-8")))
        # keys built at runtime from codes
        used |= {f"status.{c}" for c in ("ok", "update", "steam_updates", "size_mismatch", "missing_files",
                                          "no_file", "not_in_workshop")}
        used |= {f"src.{c}" for c in ("managed", "steam", "local", "missing")}
        used |= {f"kind.{c}" for c in ("override", "patch", "shared", "duplicate")}
        used |= {f"compat.{c}" for c in ("legacy_in_enhanced", "enhanced_in_legacy")}
        used |= {f"engine.{c}" for c in ("UE4", "UE5", "unknown")}
        self.assertEqual(sorted(used - set(i18n.STRINGS)), [])

    def test_both_languages_and_placeholders_match(self):
        for key, (en, ru) in i18n.STRINGS.items():
            self.assertTrue(en and ru, key)
            self.assertEqual(sorted(re.findall(r"{(\w+)}", en)), sorted(re.findall(r"{(\w+)}", ru)), key)

    def test_switch(self):
        try:
            i18n.set_lang("ru")
            self.assertEqual(i18n.t("btn.remove"), "Удалить")
            i18n.set_lang("xx")
            self.assertEqual(i18n.t("check.done", n=3, u=1), "Checked 3, updates: 1")
        finally:
            i18n.set_lang("en")


if __name__ == "__main__":
    unittest.main()
