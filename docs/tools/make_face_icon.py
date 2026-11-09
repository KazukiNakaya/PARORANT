"""PARORANT 独自の顔アイコン（頭と肩の単純なシルエット）を生成する（標準ライブラリのみ）。

使い方: python docs/tools/make_face_icon.py <出力PNG>
出力: 128x128 の白シルエット（透過）。色は UMG の ColorAndOpacity で味方／敵／死亡を切り替える。
"""
import math
import struct
import sys
import zlib

S = 128
SS = 4  # スーパーサンプリング


def circle(x, y, cx, cy, r):
    return math.hypot(x - cx, y - cy) - r


def ellipse(x, y, cx, cy, rx, ry):
    # 近似符号付き距離
    k = math.hypot((x - cx) / rx, (y - cy) / ry)
    return (k - 1.0) * min(rx, ry)


def inside(x, y):
    head = circle(x, y, 64, 46, 24) <= 0
    shoulders = ellipse(x, y, 64, 128, 50, 46) <= 0 and y <= 118
    return head or shoulders


def main(path):
    raw = bytearray()
    for py in range(S):
        raw.append(0)
        for px in range(S):
            cnt = 0
            for sy in range(SS):
                for sx in range(SS):
                    x = px + (sx + 0.5) / SS
                    y = py + (sy + 0.5) / SS
                    if inside(x, y):
                        cnt += 1
            a = int(255 * cnt / (SS * SS))
            raw += bytes((255, 255, 255, a))

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", S, S, 8, 6, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


if __name__ == "__main__":
    main(sys.argv[1])
