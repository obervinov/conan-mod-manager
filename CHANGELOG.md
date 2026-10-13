# Change Log
All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).


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
* Workshop downloads through a bundled-on-demand anonymous `steamcmd`, works for Steam and non-Steam copies alike.
* Update check through Steam Web API `GetPublishedFileDetails`, with file-size validation of installed `.pak` files.
* Load order and on/off state written to `ConanSandbox/Mods/modlist.txt`, one-time backup of the original as `modlist.txt.bak`.
* Ownership manifest `conan-mod-manager.json`: removal deletes exactly the files a mod installed, and stale files after an update.
* Steam-subscribed mods and hand-dropped `.pak` files shown alongside; hand-dropped ones can be linked to a Workshop ID.
* GitHub Actions: tests on every push, single-file `ConanModManager.exe` attached to releases on `v*` tags.
