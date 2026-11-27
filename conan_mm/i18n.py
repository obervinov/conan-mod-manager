"""UI strings in English and Russian. t("key", **fmt) returns the text in the current language."""
import locale
import sys

LANGS = ("en", "ru")
_lang = "en"

STRINGS = {
    # main window
    "app.game_folder": ("Game folder:", "Папка игры:"),
    "app.not_selected": ("not selected", "не выбрана"),
    "app.pick": ("Browse…", "Выбрать…"),
    "app.to_light": ("☀ Light", "☀ Светлая"),
    "app.to_dark": ("☾ Dark", "☾ Тёмная"),
    "app.other_lang": ("Русский", "English"),
    "app.no_workshop": (" | no Steam Workshop", " | без Steam Workshop"),
    "col.on": ("On", "Вкл"),
    "col.title": ("Mod", "Мод"),
    "col.src": ("Source", "Источник"),
    "col.eng": ("Engine", "Движок"),
    "col.cnf": ("Confl.", "Конфл."),
    "col.status": ("Status", "Статус"),
    "col.added": ("Added", "Добавлен"),
    "col.updated": ("Updated", "Обновлён"),
    "src.managed": ("manager", "менеджер"),
    "src.steam": ("Steam", "Steam"),
    "src.local": ("manual", "вручную"),
    "src.missing": ("—", "—"),
    "menu.copy_title": ("Copy title", "Копировать название"),
    "menu.copy_wid": ("Copy Workshop ID", "Копировать Workshop ID"),
    "menu.copy_url": ("Copy link", "Копировать ссылку"),
    "menu.copy_path": ("Copy file path", "Копировать путь к файлу"),
    "menu.install_deps": ("Install missing requirements", "Доставить недостающие зависимости"),
    "btn.play": ("▶ Play", "▶ Играть"),
    "btn.add": ("Add by ID / link", "Добавить по ID/ссылке"),
    "btn.toggle": ("Enable / disable", "Вкл / выкл"),
    "btn.up": ("▲ Up", "▲ Выше"),
    "btn.down": ("▼ Down", "▼ Ниже"),
    "btn.conflicts": ("Conflicts & load order…", "Конфликты и порядок…"),
    "btn.check": ("Check for updates", "Проверить обновления"),
    "btn.update_sel": ("Update selected", "Обновить выбранные"),
    "btn.update_all": ("Update all", "Обновить все"),
    "btn.link": ("Link to Workshop ID", "Привязать к Workshop ID"),
    "btn.open": ("Open in Workshop", "Открыть в Workshop"),
    "btn.remove": ("Remove", "Удалить"),
    "btn.backup": ("Backup to zip…", "Бэкап в zip…"),
    "btn.reload": ("Reload from disk", "Перечитать с диска"),
    "btn.clear_cache": ("Clear game mod cache…", "Очистить кэш модов игры…"),
    # statuses (codes come from core / analyze)
    "status.ok": ("up to date", "актуален"),
    "status.update": ("update available", "есть обнова"),
    "status.steam_updates": ("Steam will update it", "Steam обновит сам"),
    "status.size_mismatch": ("size mismatch", "размер не совпал"),
    "status.missing_files": ("files missing", "файлы пропали"),
    "status.no_file": ("file not found", "нет файла"),
    "status.not_in_workshop": ("not in Workshop", "нет в Workshop"),
    "status.unreadable": ("unreadable: {e}", "не читается: {e}"),
    "compat.legacy_in_enhanced": ("Legacy mod: Enhanced won't load it", "Legacy-мод: Enhanced его не загрузит"),
    "compat.enhanced_in_legacy": ("Enhanced mod: this game version won't load it",
                                  "мод для Enhanced: эта версия игры не загрузит"),
    "engine.UE5": ("Enhanced (UE5)", "Enhanced (UE5)"),
    "engine.UE4": ("Legacy (UE4)", "Legacy (UE4)"),
    "engine.unknown": ("unknown", "не определена"),
    # log and dialogs
    "log.error": ("Error: {e}", "Ошибка: {e}"),
    "log.cfg_fail": ("Could not save settings: {e}", "Не сохранил настройки: {e}"),
    "log.opened": ("Mods found: {n}. Game version: {ver}", "Модов найдено: {n}. Версия игры: {ver}"),
    "log.copied": ("Copied: {first}", "Скопировано: {first}"),
    "log.sorted": ("Sorted by \"{col}\", newest first. Load order is in the # column; "
                   "click # to go back to it", "Отсортировано по «{col}», новые сверху. Порядок загрузки — "
                   "в колонке #, клик по # возвращает к нему"),
    "log.downloading": ("Downloading {title} ({mb} MB)", "Качаю {title} ({mb} MB)"),
    "log.installed": ("Installed: {title} → {files}", "Установлен: {title} → {files}"),
    "log.order_applied": ("Suggested load order applied", "Применён предложенный порядок загрузки"),
    "dlg.no_game_title": ("No game", "Нет игры"),
    "play.title": ("Play", "Играть"),
    "play.running": ("Conan Exiles is already running", "Conan Exiles уже запущена"),
    "play.bad": ("Cannot start the game: {e}\n\nOpen launch settings?",
                 "Не могу запустить игру: {e}\n\nОткрыть настройки запуска?"),
    "play.started": ("Starting: {what}", "Запускаю: {what}"),
    "launch.title": ("Launch settings", "Настройки запуска"),
    "launch.mode_steam": ("Through Steam", "Через Steam"),
    "launch.mode_exe": ("Game exe directly (ConanSandbox.exe)", "Напрямую exe игры (ConanSandbox.exe)"),
    "launch.mode_custom": ("My own file: .bat / .cmd / .exe / shortcut", "Свой файл: .bat / .cmd / .exe / ярлык"),
    "launch.file": ("File:", "Файл:"),
    "launch.args": ("Arguments:", "Аргументы:"),
    "launch.types": ("Batch files, programs, shortcuts", "Батники, программы, ярлыки"),
    "launch.save": ("Save", "Сохранить"),
    "launch.saved": ("Launch: {mode}", "Запуск: {mode}"),
    "launch.hint_steam": ("Opens steam://rungameid/440900. Steam's own launch options apply "
                          "(Library → Conan Exiles → Properties).",
                          "Открывает steam://rungameid/440900. Действуют параметры запуска из самого Steam "
                          "(Библиотека → Conan Exiles → Свойства)."),
    "launch.hint_exe": ("Starts ConanSandbox/Binaries/Win64/ConanSandbox.exe with the arguments as typed.",
                        "Запускает ConanSandbox/Binaries/Win64/ConanSandbox.exe с аргументами как есть."),
    "launch.hint_custom": ("Arguments go after the file exactly as typed (in a .bat they arrive as %*). "
                           "A .bat opens in its own console window. A shortcut (.lnk) uses its own arguments.",
                           "Аргументы идут после файла как написаны (в .bat приходят как %*). "
                           ".bat открывается в своём окне консоли. Ярлык (.lnk) берёт свои аргументы."),
    "dlg.no_game": ("Pick the game folder first", "Сначала выбери папку игры"),
    "pick.title": ("Conan Exiles folder (the one containing ConanSandbox)",
                   "Папка Conan Exiles (где лежит ConanSandbox)"),
    "remove.title": ("Remove", "Удалить"),
    "remove.ask": ("Delete these mods' files?\n\n{names}", "Удалить файлы модов?\n\n{names}"),
    "remove.steam_hint": (
        "Steam subscription mod: disabled. To delete its files, unsubscribe in Workshop and Steam removes them.",
        "Мод из подписки Steam: выключен. Чтобы удалить файлы — отпишись в Workshop, Steam сотрёт сам."),
    "link.title": ("Link", "Привязка"),
    "link.pick_one": ("Select one mod with source “manual”", "Выбери один мод с источником «вручную»"),
    "link.ask": ("Workshop ID or mod link:", "Workshop ID или ссылка на мод:"),
    "link.done": ("Linked to {wid}. “Check for updates” will tell whether the file is current.",
                  "Привязан к {wid}. «Проверить обновления» покажет, свежий ли файл."),
    "add.title": ("Add mod", "Добавить мод"),
    "add.ask": ("Workshop IDs or links (several allowed, separated by spaces or new lines):",
                "Workshop ID или ссылки (можно несколько через пробел/перенос):"),
    "add.not_conan": ("Not Conan Exiles mods or unavailable: {ids}", "Не моды Conan Exiles или недоступны: {ids}"),
    "backup.title": ("Save mods backup", "Сохранить бэкап модов"),
    "backup.start": ("Backup → {dest}", "Бэкап → {dest}"),
    "backup.done": ("Backup ready: {n} mods, {mb} MB → {dest}", "Бэкап готов: {n} модов, {mb} MB → {dest}"),
    "check.none": ("No mods with a Workshop ID, nothing to check", "Нет модов с Workshop ID — нечего проверять"),
    "check.done": ("Checked {n}, updates: {u}", "Проверено {n}, обновлений: {u}"),
    "update.only_managed": ("Only mods with source “manager” can be updated (Steam updates its own)",
                            "Обновлять можно только моды с источником «менеджер» (Steam обновляет свои сам)"),
    "update.nothing": ("Nothing to update. Run “Check for updates” first.",
                       "Нечего обновлять. Сначала «Проверить обновления»."),
    "cache.title": ("Clear game mod cache", "Очистить кэш модов игры"),
    "cache.ask": (
        "Delete these from ConanSandbox\\Saved?\n\n{names}\n\nThe game unpacks the mods again on the next start "
        "(the first start takes longer). Your world and characters are not touched.",
        "Удалить из ConanSandbox\\Saved?\n\n{names}\n\nИгра заново распакует моды при следующем запуске "
        "(первый запуск будет дольше). Мир и персонажи не затрагиваются."),
    "cache.empty": ("The game's mod cache is already empty", "Кэш модов игры уже пуст"),
    "cache.done": ("Mod cache cleared: {names} ({mb} MB)", "Кэш модов очищен: {names} ({mb} MB)"),
    "cache.auto": ("Auto-reset mod cache", "Автосброс кэша модов"),
    "cache.auto_done": ("Mod set changed, game cache reset: {names} ({mb} MB)",
                        "Набор модов изменился, кэш игры сброшен: {names} ({mb} MB)"),
    "cache.skipped_running": ("Game is running: cache reset skipped, run it after closing the game",
                              "Игра запущена: сброс кэша пропущен, сделай его после выхода из игры"),
    "game.running": ("Close Conan Exiles first: the game is running", "Сначала закрой Conan Exiles: игра запущена"),
    # conflicts dialog
    "conf.title": ("Conflicts and load order", "Конфликты и порядок загрузки"),
    "conf.hint": (
        "The mod lower in the list wins. Order: patches go below the mod they patch; narrow tweaks go below "
        "broad overhauls. Enhanced (UE5) mods are packaged differently, so their files are not compared.",
        "Побеждает мод ниже в списке. Порядок: патчи — под модом, который они правят; узкие правки — под "
        "крупными модами. Enhanced-моды (UE5) упакованы иначе — их файлы не сравниваются."),
    "conf.col_kind": ("Type", "Тип"),
    "conf.col_win": ("Wins (lower)", "Побеждает (ниже)"),
    "conf.col_lose": ("Overridden", "Перекрыт"),
    "conf.col_n": ("Files", "Файлов"),
    "conf.order_frame": ("Suggested order (enabled mods only)", "Предложенный порядок (только включённые моды)"),
    "conf.col_now": ("Now", "Сейчас"),
    "conf.col_new": ("Suggested", "Предложено"),
    "conf.apply": ("Apply order", "Применить порядок"),
    "conf.optimal": ("Order is already optimal", "Порядок уже оптимален"),
    "conf.close": ("Close", "Закрыть"),
    "conf.patch_above": (" — patch is above the mod!", " — патч выше мода!"),
    "conf.summary": ("Enabled mods: {n}. Conflicts: {c}", "Включено модов: {n}. Конфликтов: {c}"),
    "conf.bad": (", misplaced patches: {n}", ", патчей не на месте: {n}"),
    "conf.ue5": (". Files not checked (UE5): {n}", ". Без проверки файлов (UE5): {n}"),
    "conf.unread": (". Unreadable: {n}", ". Не прочитано: {n}"),
    "conf.deps": (", dependency problems: {n}", ", проблем с зависимостями: {n}"),
    # Workshop dependencies (Required items)
    "dep.title": ("Mod dependencies", "Зависимости модов"),
    "dep.status_missing": ("needs {name}: not installed", "нужен {name}: не установлен"),
    "dep.status_disabled": ("needs {name}: disabled", "нужен {name}: выключен"),
    "dep.status_below": ("needs {name}: loads below, move it up", "нужен {name}: грузится ниже, подними его"),
    "dep.kind_missing": ("requirement not installed", "зависимость не установлена"),
    "dep.kind_disabled": ("requirement disabled", "зависимость выключена"),
    "dep.kind_below": ("requirement loads below", "зависимость грузится ниже"),
    "dep.ask_install": ("These mods need other Workshop items that are not installed:\n\n{names}\n\n"
                        "Yes: install them too. No: only the mods you asked for. Cancel: install nothing.",
                        "Этим модам нужны другие моды из Workshop, их нет:\n\n{names}\n\n"
                        "Да: поставить и их. Нет: только то, что просил. Отмена: ничего не ставить."),
    "dep.ask_enable": ("Enable the mods they need too?\n\n{names}", "Включить заодно моды, которые им нужны?\n\n{names}"),
    "dep.ask_disable": ("Other enabled mods need these:\n\n{mods}\n\nThey may break:\n\n{users}\n\nDisable anyway?",
                        "Эти моды нужны другим включённым:\n\n{mods}\n\nМогут сломаться:\n\n{users}\n\nВсё равно выключить?"),
    "dep.ask_remove": ("Other enabled mods need these:\n\n{mods}\n\nThey may break:\n\n{users}\n\nRemove anyway?",
                       "Эти моды нужны другим включённым:\n\n{mods}\n\nМогут сломаться:\n\n{users}\n\nВсё равно удалить?"),
    "dep.skipped": ("Requirements not installed: {n}. The mods may not work", "Зависимости не поставлены: {n}. Моды могут не работать"),
    "dep.reading": ("Reading Required items from Workshop for {n} mods (one page every 1.5 s)…",
                    "Читаю зависимости из Workshop для {n} модов (страница раз в 1,5 с)…"),
    "dep.blocked": ("Steam is refusing Workshop page requests from this IP for now ({e}), so dependencies "
                    "of {n} mods were not read. It usually lifts within an hour: run Check for updates later. "
                    "Install, update and the game are not affected.",
                    "Steam временно не отдаёт страницы Workshop на этот IP ({e}), зависимости {n} модов не "
                    "прочитаны. Обычно проходит за час: потом нажми «Проверить обновления». На установку, "
                    "обновления и игру это не влияет."),
    "dep.reading_api": ("Reading Required items for {n} mods through the Steam Web API…",
                        "Читаю зависимости {n} модов через Steam Web API…"),
    "dep.key_rejected": ("Steam Web API refused the key ({e}): check it in 🔑", "Steam Web API не принял ключ ({e}): проверь его в 🔑"),
    "dep.off": ("Dependency check is off (checkbox in the side panel): installing only what you asked for",
                "Проверка зависимостей выключена (чекбокс в боковой панели): ставлю только то, что просил"),
    "depcfg.check": ("Check dependencies", "Проверять зависимости"),
    "depcfg.warn": ("Without a Steam Web API key, dependencies are read from Workshop pages, one page every "
                    "1.5 s. Steam's CDN may still block this IP for a while (HTTP 403) with many mods. "
                    "A free key (🔑 next to the checkbox) avoids it: one API request per 100 mods.\n\nEnable?",
                    "Без ключа Steam Web API зависимости читаются со страниц Workshop, по странице раз в 1,5 с. "
                    "При большом списке модов CDN Steam всё равно может временно забанить IP (HTTP 403). "
                    "Бесплатный ключ (🔑 рядом с чекбоксом) это обходит: один запрос к API на 100 модов.\n\nВключить?"),
    "depcfg.key_title": ("Steam Web API key", "Ключ Steam Web API"),
    "depcfg.key_hint": ("Optional. With a key, dependencies come from the Steam Web API in one request "
                        "per 100 mods instead of Workshop pages, which Steam rate-limits. Get a free key "
                        "on the page below (any domain name works), paste it here. It is stored only in "
                        "this app's settings file on this PC.",
                        "Необязательно. С ключом зависимости берутся из Steam Web API, один запрос на 100 модов, "
                        "а не со страниц Workshop, которые Steam режет. Бесплатный ключ выдают на странице ниже "
                        "(домен можно указать любой), вставь его сюда. Хранится только в файле настроек "
                        "приложения на этом ПК."),
    "depcfg.key": ("Key:", "Ключ:"),
    "depcfg.key_saved": ("Steam Web API key saved", "Ключ Steam Web API сохранён"),
    "depcfg.key_cleared": ("Steam Web API key removed", "Ключ Steam Web API удалён"),
    "dep.unknown": ("Could not read Required items from Workshop for: {ids}", "Не прочитал зависимости из Workshop для: {ids}"),
    "dep.not_conan": ("Required items that are not Conan Exiles mods were skipped: {ids}",
                      "Пропущены зависимости, которые не моды Conan Exiles: {ids}"),
    "dep.found": ("Dependency problems: {n}, see the Status column or Conflicts & load order",
                  "Проблем с зависимостями: {n}, смотри колонку «Статус» или «Конфликты и порядок»"),
    "dep.none_missing": ("No missing requirements", "Недостающих зависимостей нет"),
    "kind.override": ("both change game files", "оба меняют файлы игры"),
    "kind.patch": ("patch on top of another mod", "патч поверх другого мода"),
    "kind.shared": ("different versions of a shared library", "разные версии общей библиотеки"),
    "kind.duplicate": ("same mod installed twice", "один и тот же мод дважды"),
    # core
    "core.no_sandbox": ("{p} has no ConanSandbox folder. Pick the game folder",
                        "В {p} нет папки ConanSandbox — укажи папку игры"),
    "core.backup": ("Original modlist backed up: {name}", "Бэкап исходного modlist: {name}"),
    "core.deleted": ("Deleted {name}", "Удалён {name}"),
    "core.link_local_only": ("Only a hand-dropped .pak can be linked to an ID",
                             "Привязать к id можно только локальный .pak"),
    "core.already": ("Mod {wid} is already installed", "Мод {wid} уже установлен"),
    "core.no_paks": ("Mod {wid} has no .pak files", "В моде {wid} нет .pak файлов"),
    "core.clash": ("{wid}: file {name} already belongs to another mod", "{wid}: файл {name} уже принадлежит другому моду"),
    "core.cache_removed": ("Removed from the game's mod cache: {name}", "Удалено из кэша модов игры: {name}"),
    # steam
    "steam.bad_id": ("Doesn't look like a Workshop ID or link: {text}", "Не похоже на workshop id / ссылку: {text}"),
    "steam.get_cmd": ("Downloading steamcmd: {url}", "Скачиваю steamcmd: {url}"),
    "steam.cmd_ready": ("steamcmd installed", "steamcmd установлен"),
    "steam.retry": ("Retry {a}/{n}: {ids}", "Повтор {a}/{n}: {ids}"),
    "steam.failed": ("steamcmd did not download: {ids}", "steamcmd не скачал: {ids}"),
    # pak
    "pak.no_magic": ("not a pak: signature missing", "не pak: нет сигнатуры"),
    "pak.bad_footer": ("broken footer (v{v})", "битый футер (v{v})"),
    "pak.bad_entry": ("unexpected entry layout", "неверная разметка записи"),
    "pak.unknown_layout": ("unknown index layout v{v}", "незнакомая разметка индекса v{v}"),
    "pak.no_dir": ("pak has no full file list", "в pak нет полного списка файлов"),
    "pak.encrypted": ("index is encrypted", "индекс зашифрован"),
    "pak.parse": ("could not parse index v{v}: {e}", "не смог разобрать индекс v{v}: {e}"),
}


def t(key, **fmt):
    text = STRINGS[key][LANGS.index(_lang)]
    return text.format(**fmt) if fmt else text


def get_lang():
    return _lang


def set_lang(lang):
    global _lang
    _lang = lang if lang in LANGS else "en"


def system_lang():
    """Russian if the OS UI language is Russian, English otherwise."""
    if sys.platform == "win32":
        try:
            import ctypes
            if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x19:  # LANG_RUSSIAN
                return "ru"
            return "en"
        except (OSError, AttributeError):
            pass
    name = (locale.getlocale()[0] or "").lower()
    return "ru" if name.startswith(("ru", "russian")) else "en"
