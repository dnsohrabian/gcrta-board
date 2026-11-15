"""Laser-cut SVGs for the board's plywood frame.

The frame is three rings of 1/8" (3 mm) birch glued into one ~9 mm stack that sits on the
front of the panel. Nothing reaches the back, so the magnet feet still touch the fridge.

  test.svg    cut 1   two 60 mm test corners: face (1 hole) and spacer (2 holes). Cut these
                      first, at the right end of the first sheet, and check them on the board.
  face.svg    cut 1   the visible layer: overlaps the diffuser 1 mm
  spacer.svg  cut 2   wraps the diffuser and the front of the panel's edge

face.svg and spacer.svg are each laid out on one 12" x 24" sheet (the library's $8 birch),
ring at the left. The ring uses the left 418 mm, so the right ~190 mm is free for the tests.

Panel: Adafruit 2276 (6 mm pitch, 64x32). Its drawing gives 383.90 x 191.90 mm (+0/-0.30).
Diffuser: Adafruit 4594, 2.6 mm thick.

Cut lines are 0.025 mm red (255,0,0) hairlines, no fill: the usual vector-cut setup for
Epilog lasers. Run: python frame/make_frame.py   (writes face.svg and spacer.svg next to it)
"""
from pathlib import Path

# all sizes in mm
SHEET_W, SHEET_H = 609.6, 304.8          # 24" x 12"
PANEL_W, PANEL_H = 383.9, 191.9
BORDER = 12.0                             # frame width around the panel
OUT_W, OUT_H = round(PANEL_W + 2 * BORDER), round(PANEL_H + 2 * BORDER)  # 408 x 216
CORNER_R = 3.0                            # rounded outside corners

FACE_OVERLAP = 1.0                        # face covers this much of the diffuser on each side
SPACER_GAP = 0.55                         # clearance around the panel on each side
DIFFUSER_LEFT = 2.6                       # the diffuser overhangs the panel's left edge by up to
                                          # 3/32" (2.4 mm), tapering to 2/32" lower down

MARGIN = 5.0                              # ring's distance from the sheet edge
TEST_ARM = 60.0                           # test corner size

STYLE = 'fill="none" stroke="#FF0000" stroke-width="0.025"'


def rect(x, y, w, h, r=0.0):
    rx = f' rx="{r:g}" ry="{r:g}"' if r else ""
    return f'<rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}"{rx} {STYLE}/>'


def corner(x, y, arm, band, left_band=None):
    """L-shaped test piece: the top-left corner of a ring whose border is `band` wide
    (`left_band` on the left side, if different)."""
    lb = band if left_band is None else left_band
    pts = [(0, 0), (arm, 0), (arm, band), (lb, band), (lb, arm), (0, arm)]
    d = "M " + " L ".join(f"{x + px:.3f},{y + py:.3f}" for px, py in pts) + " Z"
    return f'<path d="{d}" {STYLE}/>'


def hole(cx, cy, r=1.5):
    return f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{r:g}" {STYLE}/>'


def svg(shapes, label, w=SHEET_W, h=SHEET_H):
    body = "\n  ".join(shapes)
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<!-- {label} -->\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:g}mm" height="{h:g}mm" '
            f'viewBox="0 0 {w:g} {h:g}">\n  {body}\n</svg>\n')


def main():
    ox, oy = MARGIN, MARGIN
    px, py = ox + (OUT_W - PANEL_W) / 2, oy + (OUT_H - PANEL_H) / 2   # panel's top-left on the sheet
    outer = rect(ox, oy, OUT_W, OUT_H, CORNER_R)

    # face: window 1 mm inside the panel outline
    wx, wy = px + FACE_OVERLAP, py + FACE_OVERLAP
    wr, wb = px + PANEL_W - FACE_OVERLAP, py + PANEL_H - FACE_OVERLAP
    face_band = (px - ox) + FACE_OVERLAP
    face = [outer, rect(wx, wy, wr - wx, wb - wy)]

    # spacer: window just outside the panel outline, wider on the left for the diffuser's overhang
    spacer_band = (px - ox) - SPACER_GAP
    spacer_left = spacer_band - DIFFUSER_LEFT
    spacer_w = PANEL_W + 2 * SPACER_GAP + DIFFUSER_LEFT
    spacer_h = PANEL_H + 2 * SPACER_GAP
    spacer = [outer, rect(ox + spacer_left, py - SPACER_GAP, spacer_w, spacer_h)]

    # tests: the top-left corner of each ring; holes tell them apart (face 1, spacer 2)
    t = MARGIN
    t2 = t + TEST_ARM + 10
    hy = t + TEST_ARM - 12
    test = [
        corner(t, t, TEST_ARM, face_band), hole(t + face_band / 2, hy),
        corner(t2, t, TEST_ARM, spacer_band, spacer_left),
        hole(t2 + spacer_left / 2, hy), hole(t2 + spacer_left / 2, hy - 8),
    ]
    test_w, test_h = t2 + TEST_ARM + MARGIN, TEST_ARM + 2 * MARGIN

    here = Path(__file__).parent
    (here / "face.svg").write_text(svg(face, f"face: cut 1. Ring {OUT_W} x {OUT_H} mm."))
    (here / "spacer.svg").write_text(svg(spacer, f"spacer: cut 2. Ring {OUT_W} x {OUT_H} mm."))
    (here / "test.svg").write_text(svg(test, "test corners: face (1 hole), spacer (2 holes). Cut first.", test_w, test_h))
    print(f"test corners {test_w:.0f} x {test_h:.0f} mm")
    print(f"ring {OUT_W} x {OUT_H} mm")
    print(f"face window {wr - wx:.1f} x {wb - wy:.1f} mm")
    print(f"spacer window {spacer_w:.2f} x {spacer_h:.1f} mm, border {spacer_left:.2f} mm on the left, {spacer_band:.2f} mm elsewhere")


if __name__ == "__main__":
    main()
