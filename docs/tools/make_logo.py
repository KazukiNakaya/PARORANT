"""PARORANT 独自の P マークを生成する（標準ライブラリのみ）。

使い方: python docs/tools/make_logo.py <出力フォルダ>
出力: logo_mark.png（透過）、icon_1024.png、icon_192.png、PARORANT.ico
"""
import math
import os
import struct
import sys
import zlib

NAVY = (14, 26, 48)
AMBER = (255, 176, 46)
S = 1024


def clamp(v):
    return max(0.0, min(1.0, v))


def box(x, y, x0, y0, x1, y1):
    dx = max(x0 - x, x - x1)
    dy = max(y0 - y, y - y1)
    return math.hypot(max(dx, 0), max(dy, 0)) + min(max(dx, dy), 0)


def circle(x, y, cx, cy, r):
    return math.hypot(x - cx, y - cy) - r


def mark(x, y):
    """P の符号付き距離。太い縦棒と丸い頭、中心に照準の点。"""
    stem = box(x, y, 292, 190, 442, 834)
    bowl = min(circle(x, y, 520, 412, 222), box(x, y, 292, 190, 520, 634))
    counter = circle(x, y, 520, 412, 92)
    dot = circle(x, y, 520, 412, 34)
    return min(max(min(stem, bowl), -counter), dot)


def rounded(x, y, r=190, inset=12):
    c = S / 2
    h = c - inset - r
    ax, ay = abs(x - c) - h, abs(y - c) - h
    return math.hypot(max(ax, 0), max(ay, 0)) + min(max(ax, ay), 0) - r


def render():
    logo, icon = bytearray(S * S), bytearray(S * S)
    for j in range(S):
        for i in range(S):
            x, y = i + 0.5, j + 0.5
            logo[j * S + i] = int(clamp(0.5 - mark(x, y)) * 255)
            icon[j * S + i] = int(clamp(0.5 - rounded(x, y)) * 255)
    return logo, icon


def rgba(logo, icon, opaque):
    out = bytearray(S * S * 4)
    for k in range(S * S):
        m = logo[k] / 255
        if opaque:
            alpha = icon[k]
            col = [int(NAVY[n] * (1 - m) + AMBER[n] * m) for n in range(3)]
        else:
            alpha, col = logo[k], AMBER
        out[k * 4:k * 4 + 4] = bytes((col[0], col[1], col[2], alpha))
    return out


def shrink(buf, size):
    """箱フィルタで縮小。透過の縁が濁らないようアルファで重み付けする。"""
    out = bytearray(size * size * 4)
    for j in range(size):
        y0 = j * S // size
        y1 = max((j + 1) * S // size, y0 + 1)
        for i in range(size):
            x0 = i * S // size
            x1 = max((i + 1) * S // size, x0 + 1)
            r = g = b = a = n = 0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    k = (y * S + x) * 4
                    al = buf[k + 3]
                    r += buf[k] * al
                    g += buf[k + 1] * al
                    b += buf[k + 2] * al
                    a += al
                    n += 1
            o = (j * size + i) * 4
            if a:
                out[o:o + 3] = bytes((r // a, g // a, b // a))
            out[o + 3] = a // n
    return out


def png(buf, size):
    raw = b"".join(b"\0" + bytes(buf[y * size * 4:(y + 1) * size * 4]) for y in range(size))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def ico(images):
    head = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    body = b""
    for size, data in images:
        d = 0 if size == 256 else size
        head += struct.pack("<BBBBHHII", d, d, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
        body += data
    return head + body


def main(out):
    os.makedirs(out, exist_ok=True)
    logo, icon = render()
    mark_rgba, icon_rgba = rgba(logo, icon, False), rgba(logo, icon, True)

    def save(name, data):
        with open(os.path.join(out, name), "wb") as f:
            f.write(data)

    save("logo_mark.png", png(mark_rgba, S))
    save("icon_1024.png", png(icon_rgba, S))
    save("icon_192.png", png(shrink(icon_rgba, 192), 192))
    save("PARORANT.ico", ico([(n, png(shrink(icon_rgba, n), n)) for n in (256, 64, 48, 32, 16)]))


if __name__ == "__main__":
    main(sys.argv[1])
