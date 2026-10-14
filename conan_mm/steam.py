"""Steam side: workshop metadata via Web API, downloads via a private steamcmd."""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from .i18n import t

APP_ID = 440900  # Conan Exiles (workshop items)
DETAILS_URL = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
STEAMCMD_URLS = {
    "win32": "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip",
    "darwin": "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_osx.tar.gz",
    "linux": "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz",
}
_DONE_RE = re.compile(r'Success\. Downloaded item (\d+) to "([^"]+)"')
_ID_RE = re.compile(r"(?:id=)?(\d{6,})")


def parse_workshop_id(text):
    """Accepts a bare id or any workshop URL (…?id=123456789)."""
    m = _ID_RE.search(text.strip())
    if not m:
        raise ValueError(t("steam.bad_id", text=repr(text)))
    return m.group(1)


def workshop_url(wid):
    return f"https://steamcommunity.com/sharedfiles/filedetails/?id={wid}"


def fetch_details(ids, timeout=30):
    """{id: {"title", "time_updated", "file_size", "ok"}} for workshop ids."""
    ids = [str(i) for i in ids]
    if not ids:
        return {}
    form = {"itemcount": str(len(ids))}
    for n, wid in enumerate(ids):
        form[f"publishedfileids[{n}]"] = wid
    req = urllib.request.Request(DETAILS_URL, data=urllib.parse.urlencode(form).encode())
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        items = json.load(resp)["response"].get("publishedfiledetails", [])
    out = {}
    for it in items:
        wid = str(it.get("publishedfileid"))
        ok = it.get("result") == 1 and it.get("consumer_app_id") == APP_ID
        out[wid] = {
            "ok": ok,
            "title": it.get("title") or f"#{wid}",
            "time_updated": int(it.get("time_updated") or 0),
            "file_size": int(it.get("file_size") or 0),
        }
    return out


def default_data_dir():
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".local" / "share"
    return base / "ConanModManager"


class SteamCmd:
    def __init__(self, root=None, log=print):
        self.root = Path(root or default_data_dir() / "steamcmd")
        self.log = log

    @property
    def exe(self):
        return self.root / ("steamcmd.exe" if sys.platform == "win32" else "steamcmd.sh")

    def ensure(self):
        if self.exe.exists():
            return
        url = STEAMCMD_URLS["win32" if sys.platform == "win32" else sys.platform]
        self.log(t("steam.get_cmd", url=url))
        self.root.mkdir(parents=True, exist_ok=True)
        data = urllib.request.urlopen(url, timeout=120).read()
        if url.endswith(".zip"):
            zipfile.ZipFile(io.BytesIO(data)).extractall(self.root)
        else:
            tarfile.open(fileobj=io.BytesIO(data)).extractall(self.root)
        self.log(t("steam.cmd_ready"))

    def _run(self, ids):
        args = [str(self.exe), "+login", "anonymous"]
        for wid in ids:
            args += ["+workshop_download_item", str(APP_ID), str(wid), "validate"]
        args.append("+quit")
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        proc = subprocess.Popen(
            args, cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, text=True, errors="replace", creationflags=flags,
        )
        found = {}
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            m = _DONE_RE.search(line)
            if m:
                found[m.group(1)] = Path(m.group(2))
            if "ERROR" in line or "Downloading item" in line or m:
                self.log(f"steamcmd: {line}")
        proc.wait()
        return found

    def download(self, ids, retries=3):
        """Downloads workshop items, returns {id: folder with .pak files}.

        steamcmd times out on big items now and then; a retry resumes the download.
        On the very first run it self-updates, which is the same retry path.
        """
        self.ensure()
        pending, result = [str(i) for i in ids], {}
        for attempt in range(1, retries + 1):
            if not pending:
                break
            if attempt > 1:
                self.log(t("steam.retry", a=attempt, n=retries, ids=", ".join(pending)))
            got = self._run(pending)
            result.update(got)
            pending = [i for i in pending if i not in got]
        if pending:
            raise RuntimeError(t("steam.failed", ids=", ".join(pending)))
        return result

    @staticmethod
    def discard(folder):
        """Drops steamcmd's own copy after the paks were moved into the game."""
        shutil.rmtree(folder, ignore_errors=True)
