# Conan Exiles Mod Manager
[![PR](https://github.com/obervinov/conan-mod-manager/actions/workflows/pr.yaml/badge.svg)](https://github.com/obervinov/conan-mod-manager/actions/workflows/pr.yaml)
[![Release](https://github.com/obervinov/conan-mod-manager/actions/workflows/release.yaml/badge.svg)](https://github.com/obervinov/conan-mod-manager/actions/workflows/release.yaml)

![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/obervinov/conan-mod-manager?style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/obervinov/conan-mod-manager?style=for-the-badge)
![GitHub Release Date](https://img.shields.io/github/release-date/obervinov/conan-mod-manager?style=for-the-badge)
[![Python version](https://img.shields.io/badge/python-3.12-blue.svg?style=for-the-badge)](https://www.python.org/downloads/)
![Platform](https://img.shields.io/badge/platform-windows-0078D6.svg?style=for-the-badge)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

## Table of contents
- [About this project](#-about-this-project)
- [How it works](#-how-it-works)
- [Install](#-install)
- [Usage](#-usage)
- [Development](#-development)

## <img src="https://github.com/obervinov/_templates/blob/v1.2.2/icons/book.png" width="25" title="about"> About this project
A small single-exe Windows app to keep Conan Exiles mods in order **without starting the game**. With it you can:

- install mods from Steam Workshop by ID or link (several at once)
- check installed mods for updates and update them in one click
- enable/disable mods and change their load order
- remove a mod together with every file it brought, including the game's unpacked copy in `Saved/ExtractedMods`
- back up the whole mod setup into one zip
- see conflicts between mods, Legacy/Enhanced mismatches, and get a suggested load order

It works with or without the Steam client: downloads go through an anonymous `steamcmd`, so no Steam login is needed. The interface is in English and Russian (picked from the Windows language, switchable in the app), with dark and light themes.

> [!NOTE]
> This is a fan-made tool. It is not affiliated with or endorsed by Funcom or Valve. Conan Exiles is a trademark of its respective owners.

## <img src="https://github.com/obervinov/_templates/blob/v1.2.2/icons/stack2.png" width="25" title="architecture"> How it works
| Piece | What it does |
| --- | --- |
| `ConanSandbox/Mods/modlist.txt` | The only file the game reads: a listed `.pak` is enabled, and line order is load order. The original is backed up once as `modlist.txt.bak`. |
| `ConanSandbox/Mods/conan-mod-manager.json` | Records which `.pak` files belong to which Workshop ID, plus the full order (including disabled mods). This is why removal is exact. |
| `steamcmd` | Fetched automatically on first use into `%LOCALAPPDATA%\ConanModManager\steamcmd`. Runs `+login anonymous +workshop_download_item 440900 <id>` with up to 3 retries. Its own copy of a mod is deleted right after install. |
| `ConanSandbox/Saved/ExtractedMods`, `ModsCached`, `ModControllerCache.json`, `Modrestartdata.json` | The game's own mod cache, rebuilt from the paks on start. A removed or updated mod's unpacked copy is deleted; the whole cache can be cleared with one button. World saves (`SaveGames`) and `Config` are never touched. |
| Steam Web API | `ISteamRemoteStorage/GetPublishedFileDetails` (no API key needed) supplies titles, `time_updated` for update checks, and file sizes for integrity checks. |

The mod list combines three sources:

| Source | Where the files live | Install / update | Remove |
| --- | --- | --- | --- |
| **manager** | `ConanSandbox/Mods` | by this app | deletes the files |
| **Steam** | `steamapps/workshop/content/440900/<id>` | by the Steam client | unsubscribe in Workshop (the app only disables it) |
| **manual** | `.pak` dropped into `ConanSandbox/Mods` by hand | after *Link to Workshop ID* | deletes the file |

### Conflicts and load order
Only the index of every `.pak` is read (footer + file list, a few hundred KB even for a 2 GB mod). Asset paths are sorted into three groups:

| Path in the pak | Meaning | Reported when |
| --- | --- | --- |
| `Mods/<Name>/…` | the mod's own content | another mod writes there (**patch**, which must load below it), or the same mod is installed twice |
| `ModsShared/<Lib>/…` | a library bundled into many mods | the copies differ (SHA1) |
| anything else | an override of a base-game asset | two enabled mods override it; the one **lower** in the list wins |

The suggested order puts patches under the mod they patch and narrow tweaks under broad overhauls, and leaves everything else where it was.

The `Engine` column shows UE4 (Legacy) or UE5 (Enhanced) from the pak format version. A mod built for the other engine is flagged, because Enhanced silently skips Legacy mods. Enhanced mods are containers of IoStore packages, so for them only the engine is checked.

If `modlist.txt` is edited by hand (or by the game launcher), that order is picked up on the next refresh.

## <img src="https://github.com/obervinov/_templates/blob/v1.2.2/icons/requirements.png" width="25" title="install"> Install
Download `ConanModManager.exe` from the [latest release](https://github.com/obervinov/conan-mod-manager/releases/latest) and run it. It has no installer and needs no Python.

The exe is not code-signed, so Windows SmartScreen may warn about an unknown publisher (**More info → Run anyway**). Each release has a `SHA256SUMS` file; compare its line with:

```powershell
Get-FileHash .\ConanModManager.exe -Algorithm SHA256
```

On first start it finds the Steam install of Conan Exiles through the registry and `libraryfolders.vdf`. Otherwise click **Browse…** and pick the game folder (the one that contains `ConanSandbox`).

## <img src="https://github.com/obervinov/_templates/blob/v1.2.2/icons/build.png" width="25" title="usage"> Usage
| Button | Action |
| --- | --- |
| Add by ID / link | Paste one or more Workshop IDs / URLs; they are downloaded, installed, and enabled at the end of the list |
| Enable / disable (or double-click / Space) | Toggle the selected mods |
| ▲ Up / ▼ Down | Change the load order |
| Check for updates | Compare installed versions with Workshop |
| Update selected / Update all | Re-download the outdated or broken mods |
| Link to Workshop ID | Turn a hand-dropped `.pak` into a tracked mod |
| Remove | Delete the mod files and remove them from `modlist.txt` |
| Conflicts & load order… | Conflicts between enabled mods and a suggested load order you can apply in one click |
| Clear game mod cache… | Wipe the game's unpacked mods and mod caches (fixes a stale or broken mod cache); the game rebuilds them on the next start |
| Auto-reset mod cache (checkbox, on by default) | Wipe the whole game mod cache whenever the set of mods changes (install, update, remove, enable/disable), so nothing stale is left; the next game start is slower |
| Backup to zip… | Save all mod files, `modlist.txt` and `backup.json` (order, on/off, ids) into one archive |
| ☀ Light / ☾ Dark | Switch between the dark (default) and light themes |
| Русский / English | Switch the interface language |
| `Ctrl+C` / right click | Copy title, Workshop ID, link or file path of the selected mods |

> [!WARNING]
> Removing a mod from a world that already uses it (buildings, items, thralls) can break the save: that data lives in `game.db`, and no file manager can clean it.

## <img src="https://github.com/obervinov/_templates/blob/v1.2.2/icons/github-actions.png" width="25" title="development"> Development
```bat
pip install -r requirements.txt  :: optional: sv-ttk theme, falls back to plain ttk without it
python main.py          :: run from source (Python 3.10+)
python -m unittest -v   :: tests
build.bat               :: local build into dist\ConanModManager.exe (from ConanModManager.spec)
```
CI/CD comes from [obervinov/_templates](https://github.com/obervinov/_templates):
- a push to a branch opens or updates the pull request from `CHANGELOG.md` (`pr.yaml`), runs the unit tests on `windows-latest`, and builds the exe as a run artifact (`python-windows-exe.yaml`);
- merging the pull request creates the tag and release from the top `CHANGELOG.md` entry (`release.yaml`) and attaches `ConanModManager.exe` with `SHA256SUMS`.
