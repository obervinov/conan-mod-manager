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
    "src.managed": ("manager", "менеджер"),
    "src.steam": ("Steam", "Steam"),
    "src.local": ("manual", "вручную"),
    "src.missing": ("—", "—"),
    "menu.copy_title": ("Copy title", "Копировать название"),
    "menu.copy_wid": ("Copy Workshop ID", "Копировать Workshop ID"),
    "menu.copy_url": ("Copy link", "Копировать ссылку"),
    "menu.copy_path": ("Copy file path", "Копировать путь к файлу"),
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
    "log.downloading": ("Downloading {title} ({mb} MB)", "Качаю {title} ({mb} MB)"),
    "log.installed": ("Installed: {title} → {files}", "Установлен: {title} → {files}"),
    "log.order_applied": ("Suggested load order applied", "Применён предложенный порядок загрузки"),
    "dlg.no_game_title": ("No game", "Нет игры"),
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
