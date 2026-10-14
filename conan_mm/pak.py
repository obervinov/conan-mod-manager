"""Reads the file index of an Unreal .pak without touching the data.

Conan Exiles mods come in two generations:
  pak v1..v9   - UE4 (old Conan / "Legacy" mods), flat index with per-file SHA1
  pak v10..v12 - UE4.26+/UE5 (Conan Exiles Enhanced), path-hash + full directory index
Only the footer and the index are read, so a 2 GB mod costs a few hundred KB of I/O.
"""
import os
import struct

from .i18n import t

MAGIC = 0x5A6F12E1
UE5_MIN_VERSION = 10  # first version with the path-hash/directory index (UE4.26+, all UE5)


class PakError(Exception):
    pass


class _Reader:
    def __init__(self, data):
        self.d, self.p = data, 0

    def take(self, fmt):
        v = struct.unpack_from(fmt, self.d, self.p)
        self.p += struct.calcsize(fmt)
        return v if len(v) > 1 else v[0]

    def skip(self, n):
        self.p += n

    def fstring(self):
        n = self.take("<i")
        if n == 0:
            return ""
        if n < 0:  # UTF-16, length in chars including the terminator
            raw = self.d[self.p:self.p - n * 2]
            self.p += -n * 2
            return raw.decode("utf-16-le", errors="replace").rstrip("\0")
        raw = self.d[self.p:self.p + n]
        self.p += n
        return raw.decode("utf-8", errors="replace").rstrip("\0")


def _footer(f, size):
    tail_len = min(size, 512)
    f.seek(size - tail_len)
    tail = f.read(tail_len)
    i = tail.rfind(struct.pack("<I", MAGIC))
    if i < 0:
        raise PakError(t("pak.no_magic"))
    _, version, offset, idx_size = struct.unpack_from("<IiQQ", tail, i)
    encrypted = version >= 7 and tail[i - 1] == 1
    if not (0 < offset < size and 0 < idx_size <= size - offset):
        raise PakError(t("pak.bad_footer", v=version))
    return version, offset, idx_size, encrypted


def _legacy_entries(r, version, count, extra):
    """v1..v9: [FString name][FPakEntry] * count. Returns {path: sha1-hex}.

    Funcom's engine adds `extra` bytes after each entry (4 zero bytes in Conan's v4 paks).
    """
    out = {}
    for _ in range(count):
        name = r.fstring()
        r.skip(8 + 8 + 8)  # offset, size, uncompressed size
        compression = r.take("<i") if version < 8 else r.take("<I")
        if version == 1:
            r.skip(8)  # timestamp
        sha1 = r.d[r.p:r.p + 20].hex()
        r.skip(20)
        if version >= 3:
            if compression:
                r.skip(r.take("<i") * 16)
            r.skip(1 + 4)  # encrypted flag, compression block size
        r.skip(extra)
        if not name or not name.isprintable():
            raise PakError(t("pak.bad_entry"))
        out[name] = sha1
    return out


def _legacy_any(r, version, count):
    start = r.p
    for extra in (0, 4):
        r.p = start
        try:
            files = _legacy_entries(r, version, count, extra)
        except (PakError, struct.error):
            continue
        if r.p <= len(r.d):
            return files
    raise PakError(t("pak.unknown_layout", v=version))


def _directory_entries(f, r):
    """v10+: primary index points at a separate full directory index."""
    r.skip(8)  # path hash seed
    if r.take("<i"):
        r.skip(8 + 8 + 20)  # path hash index: we only need names
    if not r.take("<i"):
        raise PakError(t("pak.no_dir"))
    off, size = r.take("<QQ")
    f.seek(off)
    dr = _Reader(f.read(size))
    out = {}
    for _ in range(dr.take("<i")):
        directory = dr.fstring()
        for _ in range(dr.take("<i")):
            name = dr.fstring()
            dr.skip(4)  # encoded entry offset
            out[directory + name] = None  # no per-file hash in this format
    return out


def read_index(path):
    """{"version", "mount", "files": {asset path: sha1 or None}}."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        version, offset, idx_size, encrypted = _footer(f, size)
        if encrypted:
            raise PakError(t("pak.encrypted"))
        f.seek(offset)
        r = _Reader(f.read(idx_size))
        try:
            mount = r.fstring()
            count = r.take("<i")
            if version >= UE5_MIN_VERSION:
                files = _directory_entries(f, r)
            else:
                files = _legacy_any(r, version, count)
        except struct.error as e:
            raise PakError(t("pak.parse", v=version, e=e)) from None
    mount = mount.replace("../../../", "")
    files = {_join(mount, k): v for k, v in files.items()}
    return {"version": version, "mount": mount, "files": files}


def read_version(path):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        return _footer(f, size)[0]


def _join(mount, name):
    name = name.lstrip("/")
    return f"{mount.rstrip('/')}/{name}" if mount.strip("/") else name


def engine(version):
    return "UE5" if version >= UE5_MIN_VERSION else "UE4"


def asset_key(path):
    """One asset is spread over .uasset/.uexp/.ubulk — compare them as one."""
    p = path.lower()
    for ext in (".uasset", ".uexp", ".ubulk", ".uptnl"):
        if p.endswith(ext):
            return p[: -len(ext)]
    return p
