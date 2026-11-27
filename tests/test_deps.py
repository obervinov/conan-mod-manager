import io
import json
import unittest
import urllib.error
from unittest import mock

from conan_mm import analyze, deps, steam
from conan_mm.core import Mod

PAGE = """
<div class="workshopItemTitle">Some Mod</div>
<div class="panel">
  <div class="rightSectionTopTitle condensed">Required items</div>
  <div class="requiredItemsContainer" id="RequiredItems">
    <a href="https://steamcommunity.com/workshop/filedetails/?id=1000002" target="_blank">
      <div class="requiredItem">Library A</div></a>
    <a href="https://steamcommunity.com/workshop/filedetails/?id=1000003" target="_blank">
      <div class="requiredItem">Library B</div></a>
    <a href="https://steamcommunity.com/workshop/filedetails/?id=1000002"><div>dup</div></a>
  </div>
</div>
<!-- created by -->
<div class="panel"><a href="https://steamcommunity.com/sharedfiles/filedetails/?id=1000009">other</a></div>
"""


def mod(key, wid, enabled=True):
    return Mod(key, "managed", key, wid=wid, enabled=enabled)


class ParseTest(unittest.TestCase):
    def test_required_block_only(self):
        self.assertEqual(deps.parse_required(PAGE, "1000001"), ["1000002", "1000003"])

    def test_no_block(self):
        self.assertEqual(deps.parse_required("<html>no requirements</html>"), [])


class GraphTest(unittest.TestCase):
    # top -> mid -> base, top -> base, loop <-> loop2
    PAGES = {"top": ["mid", "base"], "mid": ["base"], "base": [], "loop": ["loop2"], "loop2": ["loop"]}

    def fetch(self, wid):
        self.calls.append(wid)
        if wid == "broken":
            raise OSError("timeout")
        return self.PAGES.get(wid, [])

    def setUp(self):
        self.calls = []

    def test_resolve_transitive(self):
        graph, failed, _ = deps.resolve(["top"], self.fetch)
        self.assertEqual(graph, {"top": ["mid", "base"], "mid": ["base"], "base": []})
        self.assertEqual(failed, [])
        self.assertEqual(sorted(self.calls), ["base", "mid", "top"])  # each page read once

    def test_resolve_uses_cache_and_refresh(self):
        graph, _, _ = deps.resolve(["top"], self.fetch, known={"top": ["mid"], "mid": []}, refresh=["top"])
        self.assertEqual(self.calls.count("top"), 1)
        self.assertNotIn("mid", self.calls)  # cached, not refreshed
        self.assertEqual(graph["top"], ["mid", "base"])

    def test_resolve_cycle_and_failure(self):
        graph, failed, blocked = deps.resolve(["loop", "broken"], self.fetch)
        self.assertIsNone(blocked)
        self.assertEqual(set(graph), {"loop", "loop2"})
        self.assertEqual(failed, ["broken"])
        self.assertEqual(sorted(deps.closure("loop", graph)), ["loop2"])

    def test_blocked_stops_fetching(self):
        pages = {"a": ["b", "c"], "b": ["d"]}

        def fetch(wid):
            self.calls.append(wid)
            if wid == "b":
                raise deps.Blocked("HTTP 403")
            return pages.get(wid, [])

        graph, failed, blocked = deps.resolve(["a", "x"], fetch)
        self.assertEqual(str(blocked), "HTTP 403")
        self.assertEqual(self.calls, ["a", "x", "b"])  # nothing after the block
        self.assertEqual(graph, {"a": ["b", "c"], "x": []})
        self.assertEqual(sorted(failed), ["b", "c"])

    def test_batch_source(self):
        batches = []

        def batch(ids):
            batches.append(sorted(ids))
            return {w: self.PAGES[w] for w in ids if w in self.PAGES}

        graph, failed, blocked = deps.resolve(["top", "gone"], None, batch=batch)
        self.assertEqual(batches, [["gone", "top"], ["base", "mid"]])  # one call per level
        self.assertEqual(set(graph), {"top", "mid", "base"})
        self.assertEqual((failed, blocked), (["gone"], None))

    def test_batch_key_rejected(self):
        def batch(ids):
            raise deps.KeyRejected("HTTP 403")

        graph, failed, blocked = deps.resolve(["top"], None, batch=batch)
        self.assertIsInstance(blocked, deps.KeyRejected)
        self.assertEqual((graph, failed), ({}, ["top"]))

    def test_closure_and_install_order(self):
        graph = dict(self.PAGES)
        self.assertEqual(sorted(deps.closure("top", graph)), ["base", "mid"])
        self.assertEqual(deps.install_order(["top", "mid", "base"], graph), ["base", "mid", "top"])
        self.assertEqual(deps.install_order(["loop", "loop2"], graph), ["loop2", "loop"])


class ApiTest(unittest.TestCase):
    def test_children_parsed(self):
        body = {"response": {"publishedfiledetails": [
            {"publishedfileid": "1000001", "result": 1,
             "children": [{"publishedfileid": "1000002", "sortorder": 0, "file_type": 0}]},
            {"publishedfileid": "1000003", "result": 1},
            {"publishedfileid": "1000004", "result": 9}]}}
        with mock.patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(body).encode())) as op:
            got = steam.fetch_required_api(["1000001", "1000003", "1000004"], "SECRETKEY")
        self.assertEqual(got, {"1000001": ["1000002"], "1000003": []})
        self.assertIn("includechildren=true", op.call_args[0][0])

    def test_rejected_key_not_leaked(self):
        err = urllib.error.HTTPError("https://x/?key=SECRETKEY", 403, "Forbidden", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(deps.KeyRejected) as cm:
                steam.fetch_required_api(["1000001"], "SECRETKEY")
        self.assertNotIn("SECRETKEY", str(cm.exception))
        self.assertIsNone(cm.exception.__cause__)


class CheckTest(unittest.TestCase):
    graph = {"10": ["20", "30"], "20": ["40"]}

    def test_issue_kinds(self):
        mods = [mod("ws:30", "30"), mod("ws:10", "10"), mod("ws:20", "20", enabled=False)]
        got = {(i.mod, i.need, i.kind) for i in deps.check(mods, self.graph)}
        self.assertEqual(got, {("ws:10", "20", "disabled")})  # disabled ws:20 needs nothing itself
        mods[2].enabled = True
        got = {(i.mod, i.need, i.kind) for i in deps.check(mods, self.graph)}
        self.assertEqual(got, {("ws:10", "20", "below"), ("ws:20", "40", "missing")})

    def test_dependents(self):
        mods = [mod("ws:40", "40"), mod("ws:20", "20"), mod("ws:10", "10"), mod("ws:99", "99")]
        self.assertEqual([m.key for m in deps.dependents(["40"], mods, self.graph)], ["ws:20", "ws:10"])
        mods[2].enabled = False
        self.assertEqual([m.key for m in deps.dependents(["40"], mods, self.graph)], ["ws:20"])

    def test_suggest_order_puts_requirements_above(self):
        mods = [mod("ws:10", "10"), mod("ws:x", "x"), mod("ws:30", "30"), mod("ws:20", "20")]
        order = analyze.suggest_order(mods, {}, [], deps.must_load_before(mods, self.graph))
        self.assertLess(order.index("ws:20"), order.index("ws:10"))
        self.assertLess(order.index("ws:30"), order.index("ws:10"))
        self.assertEqual(order.index("ws:x"), 0)  # unrelated mod keeps its place at the top

    def test_dependency_beats_override_heuristic(self):
        mods = [mod("ws:20", "20"), mod("ws:10", "10")]
        infos = {"ws:20": analyze.PakInfo(assets={"a": None}), "ws:10": analyze.PakInfo(assets={"a": None, "b": None})}
        # 10 is broader, so the heuristic alone would put it above 20; but 10 needs 20
        conflict = analyze.Conflict("ws:10", "ws:20", "override", ["a"])
        order = analyze.suggest_order(mods, infos, [conflict], deps.must_load_before(mods, self.graph))
        self.assertEqual(order, ["ws:20", "ws:10"])


if __name__ == "__main__":
    unittest.main()
