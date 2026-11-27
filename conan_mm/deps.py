"""Workshop dependencies ("Required items") between mods.

The public Web API does not return them (GetPublishedFileDetails has no children field,
IPublishedFileService needs an API key), so they are read from the item's Workshop page.
A requirement has to be installed, enabled and loaded ABOVE the mod that needs it.
"""
import re
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

_BLOCK = re.compile(r'id="RequiredItems"(.*?)(?:<!--|class="panel"|$)', re.S)
_LINK = re.compile(r"filedetails/\?id=(\d+)")
LIMIT = 200  # safety net against a runaway chain


def parse_required(html, wid=None):
    """Ids listed under "Required items" on a Workshop page, page order, without the item itself."""
    m = _BLOCK.search(html)
    if not m:
        return []
    return [i for i in dict.fromkeys(_LINK.findall(m.group(1))) if i != str(wid)]


def resolve(roots, fetch, known=None, refresh=(), workers=8):
    """Transitive requirements of `roots`: {wid: [required ids]} for every id reached.

    `known` is a cache ({wid: [ids]}) used for ids not listed in `refresh`; `fetch(wid)`
    returns the direct requirements and may raise, which leaves that id out of the result.
    Returns (graph, failed ids).
    """
    known, refresh = dict(known or {}), {str(r) for r in refresh}
    graph, failed = {}, []
    queue, seen = deque(str(r) for r in roots), set()

    def get(wid):
        try:
            return wid, fetch(wid), None
        except Exception as e:  # noqa: BLE001 — network / parsing: reported, never fatal
            return wid, None, e

    with ThreadPoolExecutor(workers) as pool:
        while queue and len(seen) < LIMIT:
            level = []
            while queue:
                wid = queue.popleft()
                if wid not in seen:
                    seen.add(wid)
                    level.append(wid)
            todo = [w for w in level if w in refresh or w not in known]
            for wid in level:
                if wid not in todo:
                    graph[wid] = list(known[wid])
            for wid, req, err in pool.map(get, todo):
                if err is None:
                    graph[wid] = req
                else:
                    failed.append(wid)
            for wid in level:
                queue.extend(r for r in graph.get(wid, []) if r not in seen)
    return graph, failed


def closure(wid, graph):
    """Every id `wid` needs, directly or through others (not including itself)."""
    out, stack = [], list(graph.get(str(wid), []))
    while stack:
        r = stack.pop()
        if r not in out and r != str(wid):
            out.append(r)
            stack.extend(graph.get(r, []))
    return out


def install_order(ids, graph):
    """`ids` sorted so a requirement is installed (= appended to the load order) before its user."""
    ids = [str(i) for i in ids]
    done, out = set(), []

    def visit(wid, path):
        if wid in done or wid in path:
            return
        for r in graph.get(wid, []):
            if r in ids:
                visit(r, path | {wid})
        done.add(wid)
        out.append(wid)

    for wid in ids:
        visit(wid, frozenset())
    return out


@dataclass
class Issue:
    mod: str  # key of the mod that needs something
    need: str  # workshop id it needs
    kind: str  # missing | disabled | below
    have: str = None  # key of the installed requirement, if any


def check(mods, graph):
    """Problems of the ENABLED mods in `mods` (load order). Disabled mods need nothing."""
    by_wid = {}
    for m in mods:
        if m.wid and m.source != "missing":
            by_wid.setdefault(m.wid, m)
    pos = {m.key: i for i, m in enumerate(mods)}
    out = []
    for m in mods:
        if not m.enabled or not m.wid:
            continue
        for need in graph.get(m.wid, []):
            dep = by_wid.get(need)
            if dep is None:
                out.append(Issue(m.key, need, "missing"))
            elif not dep.enabled:
                out.append(Issue(m.key, need, "disabled", dep.key))
            elif pos[dep.key] > pos[m.key]:
                out.append(Issue(m.key, need, "below", dep.key))
    return out


def dependents(wids, mods, graph):
    """Enabled mods (other than `wids` themselves) that need any of `wids`, directly or not."""
    wids = {str(w) for w in wids}
    return [m for m in mods if m.enabled and m.wid and m.wid not in wids and wids & set(closure(m.wid, graph))]


def must_load_before(mods, graph):
    """{mod key: {keys of installed requirements}} — hard ordering edges for suggest_order."""
    by_wid = {m.wid: m.key for m in mods if m.wid}
    out = {}
    for m in mods:
        if m.wid:
            req = {by_wid[r] for r in graph.get(m.wid, []) if r in by_wid and by_wid[r] != m.key}
            if req:
                out[m.key] = req
    return out
