"""PARORANT L_Proto blockout generator.
Coordinates in meters. X = north (defender side +), Y = east (B side +).
Walkable rectangles are carved out of a solid 80x80 block; the remainder is
merged into maximal rectangles that become 4m-tall wall blocks.
"""
import json

N = 40  # half size (m)

# (name, x0, x1, y0, y1)
WALK = [
    ("AtkSpawn",   -40, -28, -37,  37),
    ("ALane",      -28,   6, -37, -31),
    ("AMain",        6,  12, -36, -32),
    ("ASite",       12,  34, -38, -16),
    ("AShort",       4,  14, -20, -12),
    ("BLane",      -28,   6,  31,  37),
    ("BMain",        6,  12,  32,  36),
    ("BSite",       12,  34,  16,  38),
    ("BShort",       4,  14,  12,  20),
    ("MidLane",    -28, -10,  -3,   3),
    ("Mid",        -10,  10, -12,  12),
    ("MidTop",      10,  30,  -4,   4),
    ("DefSpawn",    30,  40, -10,  10),
    ("DefA",        24,  40, -16, -10),
    ("DefB",        24,  40,  10,  16),
]

walk = [[False] * (2 * N) for _ in range(2 * N)]  # [ix][iy]
for _, x0, x1, y0, y1 in WALK:
    for x in range(x0, x1):
        for y in range(y0, y1):
            walk[x + N][y + N] = True

# greedy maximal-rectangle merge of solid cells
used = [[False] * (2 * N) for _ in range(2 * N)]
rects = []
for ix in range(2 * N):
    for iy in range(2 * N):
        if walk[ix][iy] or used[ix][iy]:
            continue
        # extend in y
        h = 0
        while iy + h < 2 * N and not walk[ix][iy + h] and not used[ix][iy + h]:
            h += 1
        # extend in x while full column of height h is solid
        w = 1
        while ix + w < 2 * N and all(not walk[ix + w][iy + k] and not used[ix + w][iy + k] for k in range(h)):
            w += 1
        for a in range(w):
            for b in range(h):
                used[ix + a][iy + b] = True
        rects.append((ix - N, ix - N + w, iy - N, iy - N + h))

WALL_H = 4.0
blocks = []
for i, (x0, x1, y0, y1) in enumerate(rects):
    blocks.append({
        "name": f"Wall_{i:02d}",
        "loc": [(x0 + x1) / 2 * 100, (y0 + y1) / 2 * 100, WALL_H / 2 * 100],
        "scale": [(x1 - x0), (y1 - y0), WALL_H],
    })
# outer ring (1m thick) so the border is closed
ring = [
    ("Wall_N", [40.5, 0], [1, 82]), ("Wall_S", [-40.5, 0], [1, 82]),
    ("Wall_E", [0, 40.5], [80, 1]), ("Wall_W", [0, -40.5], [80, 1]),
]
for n, (x, y), (sx, sy) in ring:
    blocks.append({"name": n, "loc": [x * 100, y * 100, 200], "scale": [sx, sy, WALL_H]})

# cover boxes: (name, x, y, size_xy, height)
COVER = [
    ("CoverA_1", 24, -30, 2, 2), ("CoverA_2", 28, -24, 2, 1), ("CoverA_3", 19, -34, 2, 1),
    ("CoverA_4", 30, -19, 2, 2), ("CoverA_5", 17, -24, 1.5, 1),
    ("CoverB_1", 24, 30, 2, 2), ("CoverB_2", 28, 24, 2, 1), ("CoverB_3", 19, 34, 2, 1),
    ("CoverB_4", 30, 19, 2, 2), ("CoverB_5", 17, 24, 1.5, 1),
    ("CoverMid_1", 2, 5, 2, 2), ("CoverMid_2", -4, -6, 2, 1),
    ("CoverALane", -12, -35, 2, 1), ("CoverBLane", -12, 35, 2, 1),
]
cover = [{"name": n, "loc": [x * 100, y * 100, h / 2 * 100], "scale": [s, s, h]} for n, x, y, s, h in COVER]

out = {"walls": blocks, "cover": cover, "walk": WALK}
json.dump(out, open("/home/claude/map/layout.json", "w"), indent=1)
print("walls", len(blocks), "cover", len(cover))

# ascii preview (north up, east right), 1 char = 1m, sample every 2m
for x in range(N - 1, -N - 1, -2):
    row = ""
    for y in range(-N, N, 1):
        row += "." if walk[x + N][y + N] else "#"
    print(f"{x:4d} {row}")
