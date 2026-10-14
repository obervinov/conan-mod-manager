# Change Log
All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).


## v0.7.0 - 2026-10-14
#### 🚀 Features
* **Auto-reset mod cache** (on by default, remembered): whenever the set of loaded mods changes (install, update, remove, enable/disable), the whole game mod cache in `ConanSandbox/Saved` is wiped, so no stale unpacked mod can survive regardless of how the game names its cache entries. Reordering does not trigger it. If the game is running, the reset is skipped with a note in the log. The next game start takes longer while the game unpacks the mods again.

## v0.6.0 - 2026-10-14
#### 🚀 Features
* Cleans the game's own mod cache in `ConanSandbox/Saved`, which the game rebuilds from the `.pak` files:
  - removing a mod also deletes its unpacked copy in `Saved/ExtractedMods` (matched by pak name: `Name`, `Name.*`, `Name-*`)
  - updating a mod deletes the unpacked copy of the old version, so the game unpacks the new one
  - **Clear game mod cache…** wipes `ExtractedMods`, `ModsCached`, `ModControllerCache.json` and `Modrestartdata.json` after a confirmation; `SaveGames` and `Config` are never touched
* Remove, install/update and cache clearing refuse to run while Conan Exiles (client or server) is running.
#### 🐛 Bug Fixes
* Neutral wording about Steam client support in docs and code comments.

## v0.5.0 - 2026-10-14
#### 🚀 Features
* English and Russian interface. The default follows the Windows UI language; the **Русский / English** button switches it on the fly (the window is rebuilt, the log is kept) and the choice is remembered.
* Releases now ship `ConanModManager.exe.sha256`, and the SHA256 is printed in the release notes.
#### 🔧 Internal
* Mod statuses and conflict kinds are codes in the logic layer; all user-facing text lives in `conan_mm/i18n.py`. A test checks that every key used in the code exists in both languages with matching placeholders.
#### 📝 Docs
* README: English button names, "works with or without the Steam client", a "not affiliated with Funcom or Valve" note, and how to verify the exe checksum.

## v0.4.0 - 2026-10-13
#### 🚀 Features
* Dark theme by default (Windows 11 "Sun Valley" look via `sv-ttk`), switchable to light with the ☀/☾ button; the choice is remembered.
* Native Windows title bar follows the theme (DWM immersive dark mode).
* Falls back to a hand-made dark/light palette on stock ttk when `sv-ttk` is missing or unsupported (Tk 9).

## v0.3.0 - 2026-10-13
#### 🚀 Features
* **Конфликты и порядок…**: reads the file index of every `.pak` (footer + index only, no data) and lists, among enabled mods:
  - two mods overriding the same base-game asset (the one lower in the load order wins)
  - a patch writing into another mod's `Mods/<Name>/` folder, flagged red when it sits above that mod
  - different copies of the same `ModsShared/<Lib>` library (SHA1 differs)
  - the same mod installed twice
* Suggested load order (stable topological sort): patches under the mod they patch, narrow tweaks under broad overhauls, everything else keeps its place. Preview side by side, applied with one click.
* Engine check: `Движок` column (UE4 = Legacy, UE5 = Enhanced) compared with the game's own content paks. A Legacy mod in Enhanced (or the reverse) is flagged, since the game silently skips it.
* `Конфл.` column with the conflict count per mod.
#### 🐛 Bug Fixes
* `modlist.txt` now lists mods from `ConanSandbox/Mods` as `*Name.pak` (the documented relative form), so moving the game folder does not break the list.
#### 📝 Notes
* Supports Conan's v4 pak index (with Funcom's 4 extra bytes per entry) and the UE5 v10–v12 directory index. Enhanced mods are containers of IoStore packages, so their assets are not compared, only the engine.

## v0.2.0 - 2026-10-13
#### 🚀 Features
* Copy from the mod table: `Ctrl+C` copies titles of the selected mods; the right-click menu also copies Workshop ID, Workshop link or `.pak` path.
* **Бэкап в zip…**: dumps every mod file (`Mods/…` and `Workshop/<id>/…`), `modlist.txt` and a self-describing `backup.json` (order, on/off, ids, titles) into one archive.

## v0.1.0 - 2026-10-13
#### 🚀 Features
* Windows GUI (Tkinter) for Conan Exiles mods: install, update, remove, enable/disable and reorder without starting the game.
* Workshop downloads through a bundled-on-demand anonymous `steamcmd`, works with or without the Steam client.
* Update check through Steam Web API `GetPublishedFileDetails`, with file-size validation of installed `.pak` files.
* Load order and on/off state written to `ConanSandbox/Mods/modlist.txt`, one-time backup of the original as `modlist.txt.bak`.
* Ownership manifest `conan-mod-manager.json`: removal deletes exactly the files a mod installed, and stale files after an update.
* Steam-subscribed mods and hand-dropped `.pak` files shown alongside; hand-dropped ones can be linked to a Workshop ID.
* GitHub Actions: tests on every push, single-file `ConanModManager.exe` attached to releases on `v*` tags.
