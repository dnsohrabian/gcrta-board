"""Preview the LED matrix layout on your computer, pixel for pixel.

Runs the board's own screen.py and config.py with the real Adafruit display libraries
(downloaded once into tools/.cache) on a stand-in for CircuitPython's displayio, then
writes a PNG of a few sample screens. Colors are shown as they look on the LEDs: the
panel's 5-bit color steps are applied and the gamma correction is undone.

    python tools/preview.py                     # writes preview.png
    python tools/preview.py -o out.png --ascii  # also prints the pixel map

Needs Python 3.8+ and no packages. The fonts come from src/lib.
"""
import argparse
import builtins
import collections
import os
import struct
import sys
import types
import urllib.request
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# The board files sit in src/ in the repo, or next to tools/ on the CIRCUITPY drive
BOARD = os.path.join(ROOT, "src") if os.path.exists(os.path.join(ROOT, "src", "screen.py")) else ROOT
CACHE = os.path.join(HERE, ".cache", "adafruit")

# Library versions in the CircuitPython 10.x bundle the board uses
SOURCES = {
    "adafruit_display_text": ("Adafruit_CircuitPython_Display_Text", "5.0.6", ["__init__.py", "bitmap_label.py"]),
    "adafruit_bitmap_font": ("Adafruit_CircuitPython_Bitmap_Font", "2.5.1", ["__init__.py", "bitmap_font.py", "bdf.py", "glyph_cache.py"]),
    "adafruit_display_shapes": ("Adafruit_CircuitPython_Display_Shapes", "2.10.6", ["__init__.py", "rect.py"]),
}


def fetch_sources():
    for package, (repo, tag, files) in SOURCES.items():
        folder = os.path.join(CACHE, tag + "-" + package, package)
        os.makedirs(folder, exist_ok=True)
        for name in files:
            path = os.path.join(folder, name)
            if not os.path.exists(path):
                url = "https://raw.githubusercontent.com/adafruit/%s/%s/%s/%s" % (repo, tag, package, name)
                try:
                    data = urllib.request.urlopen(url, timeout=30).read()
                except OSError:
                    data = b""  # some packages have no __init__.py
                with open(path, "wb") as f:
                    f.write(data)
        sys.path.insert(0, os.path.dirname(folder))


# ---------------------------------------------------------------- displayio stand-in
class Bitmap:
    def __init__(self, width, height, colors):
        self.width, self.height = width, height
        self.data = [0] * (width * height)

    def _i(self, k):
        return k[1] * self.width + k[0] if isinstance(k, tuple) else k

    def __getitem__(self, k):
        return self.data[self._i(k)]

    def __setitem__(self, k, v):
        self.data[self._i(k)] = v

    def fill(self, v):
        self.data = [v] * len(self.data)

    def blit(self, x, y, src, *, x1=0, y1=0, x2=None, y2=None, skip_index=None):
        x2 = src.width if x2 is None else x2
        y2 = src.height if y2 is None else y2
        for sy in range(y1, y2):
            for sx in range(x1, x2):
                v = src[sx, sy]
                tx, ty = x + sx - x1, y + sy - y1
                if v != skip_index and 0 <= tx < self.width and 0 <= ty < self.height:
                    self[tx, ty] = v


class Palette:
    def __init__(self, n):
        self.colors, self.clear = [0] * n, [False] * n

    def __len__(self):
        return len(self.colors)

    def __getitem__(self, i):
        return self.colors[i]

    def __setitem__(self, i, v):
        self.colors[i] = v

    def make_transparent(self, i):
        self.clear[i] = True

    def make_opaque(self, i):
        self.clear[i] = False

    def is_transparent(self, i):
        return self.clear[i]


class TileGrid:
    def __init__(self, bitmap, *, pixel_shader, x=0, y=0, **_):
        self.bitmap, self.pixel_shader, self.x, self.y = bitmap, pixel_shader, x, y
        self.hidden = False
        self.transpose_xy = self.flip_x = self.flip_y = False


class Group(list):
    def __init__(self, *, scale=1, x=0, y=0):
        super().__init__()
        # set directly: Label overrides the scale property
        self.__dict__.update(scale=scale, x=x, y=y, hidden=False)

    def pop(self, i=-1):
        return list.pop(self, i)


class Matrix:
    def __init__(self, **_):
        self.display = types.SimpleNamespace(root_group=None, refresh=lambda **kw: True)


def install_fakes(fonts):
    def module(name, **attrs):
        m = types.ModuleType(name)
        m.__dict__.update(attrs)
        sys.modules[name] = m

    module("displayio", Bitmap=Bitmap, Palette=Palette, TileGrid=TileGrid, Group=Group)
    module("fontio", FontProtocol=object, Glyph=collections.namedtuple(
        "Glyph", "bitmap tile_index width height dx dy shift_x shift_y"))
    module("micropython", const=lambda v: v)
    module("bitmaptools")
    module("adafruit_ticks", ticks_ms=lambda: 0, ticks_diff=lambda a, b: a - b, ticks_add=lambda a, b: a + b)
    for name in ("lvfontbin", "pcf", "ttf"):
        module("adafruit_bitmap_font." + name)
    module("adafruit_matrixportal")
    module("adafruit_matrixportal.matrix", Matrix=Matrix)

    # config.py names fonts as "lib/..." on the CIRCUITPY drive
    real_open = builtins.open

    def board_open(path, *args, **kwargs):
        if isinstance(path, str) and path.startswith("lib/"):
            path = os.path.join(fonts, path[4:])
        return real_open(path, *args, **kwargs)

    builtins.open = board_open


# ---------------------------------------------------------------- rendering
def render(root, width=64, height=32):
    px = [[0] * width for _ in range(height)]

    def draw(node, gx, gy):
        if node.hidden:
            return
        if isinstance(node, Group):
            for child in node:
                draw(child, gx + node.x, gy + node.y)
            return
        bitmap, palette = node.bitmap, node.pixel_shader
        for y in range(bitmap.height):
            for x in range(bitmap.width):
                v = bitmap[x, y]
                X, Y = gx + node.x + x, gy + node.y + y
                if not palette.is_transparent(v) and 0 <= X < width and 0 <= Y < height:
                    px[Y][X] = palette[v]

    draw(root, 0, 0)
    return px


def perceived(rgb, bit_depth, gamma):
    """What a monitor should show for the LED driven with rgb: drop to the panel's color
    steps, then undo the gamma correction screen.color() applied."""
    out = 0
    for shift in (16, 8, 0):
        c = (rgb >> shift) & 0xFF
        step = 256 >> bit_depth
        c = (c // step) * step
        out |= round((c / 255) ** (1 / gamma) * 255) << shift
    return out


def write_png(frames, path, bit_depth, gamma, scale=12):
    width = len(frames[0][0]) * scale
    rows = []
    for i, frame in enumerate(frames):
        if i:
            rows += [b"\x00" + b"\x50\x50\x50" * width] * 4
        for y in range(len(frame) * scale):
            line = bytearray(b"\x00")
            for x in range(width):
                dy, dx = y % scale - scale / 2 + .5, x % scale - scale / 2 + .5
                if dx * dx + dy * dy <= (scale * .42) ** 2:
                    c = frame[y // scale][x // scale]
                    c = perceived(c, bit_depth, gamma) if c else 0x161616
                else:
                    c = 0
                line += bytes(((c >> 16) & 255, (c >> 8) & 255, c & 255))
            rows.append(bytes(line))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", width, len(rows), 8, 2, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(b"".join(rows), 9)))
        f.write(chunk(b"IEND", b""))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", default="preview.png")
    ap.add_argument("--fonts", default=os.path.join(BOARD, "lib"), help="folder with the .bdf fonts")
    ap.add_argument("--ascii", action="store_true", help="print the pixel map too")
    args = ap.parse_args()

    fetch_sources()
    install_fakes(args.fonts)
    sys.path.insert(0, BOARD)
    import config
    import screen

    # Sample rows with every badge on the first page, three per frame
    page = config.PAGES[0]
    badges = [(a.get("label", a["route"]), a.get("color", 0x808080)) for a in page["arrivals"]]
    samples = [("DOWNTOWN", 7), ("WESTGATE TC", 12), ("TOWER CITY VIA KAMMS", 19),
               ("STEARNS RD", 24), ("AIRPORT", 31), ("PUBLIC SQ", 38)]
    rows = [(label, rgb, [samples[i % len(samples)][1]], samples[i % len(samples)][0])
            for i, (label, rgb) in enumerate(badges)]

    display = screen.Screen()
    display.set_clock("15:53")
    frames = []
    for start in range(0, len(rows), screen.ROWS):
        display.show_page(page["title"], rows[start:start + screen.ROWS], None)
        display._scroll_start = screen._ms() - 6000  # partway through scrolling long destinations
        display.scroll()
        frames.append(render(display.matrix.display.root_group))
    display.show_message(config.PAGES[-1]["title"], "NONE SOON")
    frames.append(render(display.matrix.display.root_group))

    if args.ascii:
        for frame in frames:
            for y, line in enumerate(frame):
                print("%2d %s" % (y, "".join("#" if c else "." for c in line)))
            print()
    write_png(frames, args.out, config.BIT_DEPTH, screen.GAMMA)
    print("Wrote", args.out)


if __name__ == "__main__":
    main()
