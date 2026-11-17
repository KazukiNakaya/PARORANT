"""soak43_<MAP>.jsonl の集計：Pawn ごとの移動距離・最長の停止（1m 以内）と位置、プレイヤーの移動後の味方の動き、State の変化。使い方: python analyze_soak_43.py <jsonl>"""
import json, math, sys, collections
rows = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
ev = [r for r in rows if "gt" not in r]
rows = [r for r in rows if "gt" in r]
print("samples", len(rows), "gt", rows[0]["gt"], "->", rows[-1]["gt"], "events", ev)
infos = collections.OrderedDict()
for r in rows: infos.setdefault(json.dumps(r["info"], sort_keys=True), 0)
print("info 例", list(infos)[:2], list(infos)[-1:])
tr = collections.defaultdict(list)
for r in rows:
    for p in r["pawns"]: tr[p["n"]].append((r["gt"], p["p"][0], p["p"][1], p["state"], p["peek"], p["team"]))
for n, t in sorted(tr.items()):
    best = (0, None, None); s = 0
    for i in range(1, len(t) + 1):
        if i == len(t) or math.hypot(t[i][1] - t[s][1], t[i][2] - t[s][2]) > 1.0:
            d = t[i - 1][0] - t[s][0]
            if d > best[0]: best = (d, (t[s][1], t[s][2]), (t[s][3], t[s][4]))
            s = i
    path = sum(math.hypot(t[i][1] - t[i - 1][1], t[i][2] - t[i - 1][2]) for i in range(1, len(t)))
    print(n, "team", t[0][5], "n", len(t), "path m", round(path), "longest still(game s)", round(best[0], 1), "at", best[1], "state/peek", best[2])
