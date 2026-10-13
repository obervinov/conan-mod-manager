# Conan Exiles Mod Manager
[![CI](https://github.com/obervinov/conan-mod-manager/actions/workflows/ci.yaml/badge.svg)](https://github.com/obervinov/conan-mod-manager/actions/workflows/ci.yaml)
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
- remove a mod together with every file it brought

It works for both the Steam version and non-Steam copies. Downloads go through an anonymous `steamcmd`, so it needs no Steam login and no game ownership.

## <img src="https://github.com/obervinov/_templates/blob/v1.2.2/icons/stack2.png" width="25" title="architecture"> How it works
| Piece | What it does |
| --- | --- |
| `ConanSandbox/Mods/modlist.txt` | The only file the game reads: a listed `.pak` is enabled, and line order is load order. The original is backed up once as `modlist.txt.bak`. |
| `ConanSandbox/Mods/conan-mod-manager.json` | Records which `.pak` files belong to which Workshop ID, plus the full order (including disabled mods). This is why removal is exact. |
| `steamcmd` | Fetched automatically on first use into `%LOCALAPPDATA%\ConanModManager\steamcmd`. Runs `+login anonymous +workshop_download_item 440900 <id>` with up to 3 retries. Its own copy of a mod is deleted right after install. |
| Steam Web API | `ISteamRemoteStorage/GetPublishedFileDetails` (no API key needed) supplies titles, `time_updated` for update checks, and file sizes for integrity checks. |

The mod list combines three sources:

| Source | Where the files live | Install / update | Remove |
| --- | --- | --- | --- |
| **менеджер** | `ConanSandbox/Mods` | by this app | deletes the files |
| **Steam** | `steamapps/workshop/content/440900/<id>` | by the Steam client | unsubscribe in Workshop (the app only disables it) |
| **вручную** | `.pak` dropped into `ConanSandbox/Mods` by hand | after *Привязать к Workshop ID* | deletes the file |

If `modlist.txt` is edited by hand (or by the game launcher), that order is picked up on the next refresh.

## <img src="https://github.com/obervinov/_templates/blob/v1.2.2/icons/requirements.png" width="25" title="install"> Install
Download `ConanModManager.exe` from the [latest release](https://github.com/obervinov/conan-mod-manager/releases/latest) and run it. It has no installer and needs no Python.

On first start it finds the Steam install of Conan Exiles through the registry and `libraryfolders.vdf`. For a non-Steam copy, click **Выбрать…** and pick the game folder (the one that contains `ConanSandbox`).

## <img src="https://github.com/obervinov/_templates/blob/v1.2.2/icons/build.png" width="25" title="usage"> Usage
| Button | Action |
| --- | --- |
| Добавить по ID/ссылке | Paste one or more Workshop IDs / URLs; they are downloaded, installed, and enabled at the end of the list |
| Вкл / выкл (or double-click / Space) | Toggle the selected mods |
| ▲ Выше / ▼ Ниже | Change the load order |
| Проверить обновления | Compare installed versions with Workshop |
| Обновить выбранные / все | Re-download the outdated or broken mods |
| Привязать к Workshop ID | Turn a hand-dropped `.pak` into a tracked mod |
| Удалить | Delete the mod files and remove them from `modlist.txt` |

> [!WARNING]
> Removing a mod from a world that already uses it (buildings, items, thralls) can break the save: that data lives in `game.db`, and no file manager can clean it.

## <img src="https://github.com/obervinov/_templates/blob/v1.2.2/icons/github-actions.png" width="25" title="development"> Development
```bat
python main.py          :: run from source (Python 3.10+, stdlib only)
python -m unittest -v   :: tests
build.bat               :: local build into dist\ConanModManager.exe
```
Pushing a `v*` tag makes GitHub Actions build the exe on `windows-latest` and attach it to a release, with notes taken from `CHANGELOG.md`.
