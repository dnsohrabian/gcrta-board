"""Draws pages on the 64x32 LED matrix.

    y 0-4    INBOUND                15:53    header: page title and clock (4x6 font)
    y 6-13   [22] DOWNTOWN            15     route badge (5x7), destination (4x6), minutes (5x7)
    y 15-22  [RL] AIRPORT             16
    y 24-31  [45] PARMA TC            19
A dot left of the clock lights up while data is loading.

With TIMES_PER_ROW = 2 the minutes read "15,29" in the small font, and destinations get
less room.

A destination too long for its slot scrolls. Destinations are drawn underneath two black
masks so only the middle of each row shows through, and scrolling only moves a label;
it never re-renders one. Re-rendering text is the slow part, so it happens only when
the text actually changes.
"""
import displayio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
from adafruit_display_text.bitmap_label import Label
from adafruit_matrixportal.matrix import Matrix

import config

WIDTH, HEIGHT = 64, 32
ROWS = 3
ROW_TOPS = (6, 15, 24)  # each row is 8 px tall: the badge height
ROW_HEIGHT = 8
BADGE_WIDTH = 11        # two 4 px characters, 1 px apart, with a 1 px border all round
DEST_X = BADGE_WIDTH + 2
# Widest minutes text: "99" in the 5x7 font, or "99,99" in the 4x6 font
TIMES_WIDTH = 10 if config.TIMES_PER_ROW == 1 else 20
DEST_END = WIDTH - TIMES_WIDTH - 4  # keep 4 px clear before the minutes

SCROLL_HOLD = 2.0       # seconds to rest at the start of a long destination
SCROLL_END_HOLD = 1.0   # seconds to rest at the end before jumping back
SCROLL_STEP = 0.08      # seconds per pixel (~12 px/s)

GAMMA = 2.2


def color(rgb):
    """Gamma-correct a 0xRRGGBB color, so the panel shows it the way a monitor would.
    LEDs are linear: without this, dim values (like the 0x40 blue in a green) come
    out far too strong and colors look washed out."""
    out = 0
    for shift in (16, 8, 0):
        out |= round(((rgb >> shift & 0xFF) / 255) ** GAMMA * 255) << shift
    return out



def _ink(font, text):
    """(first, last) x of the lit pixels in text. Letter boxes include blank columns
    that differ from glyph to glyph, so centering by box looks off. This centers by ink."""
    first, last, x = None, None, 0
    for ch in text:
        g = font.get_glyph(ord(ch))
        for col in range(g.width):
            if any(g.bitmap[col, row] for row in range(g.height)):
                first = x + g.dx + col if first is None else first
                last = x + g.dx + col
        x += g.shift_x
    return (first or 0), (last or 0)


def _label(font, rgb, anchor, position, text=""):
    return Label(font, text=text, color=color(rgb), anchor_point=anchor, anchored_position=position)


def _set_text(label, text):
    if label.text != text:
        label.text = text
        return True
    return False


class Row:
    def __init__(self, top, font, small, back, front):
        self.top = top
        # A label's ink starts 1 px below its anchored y. Badge digits (6 px) fill rows
        # top+1..top+6 of the 8 px badge; destination letters (5 px) end on the same row.
        self.dest = _label(small, config.DEST_COLOR, (0, 0), (DEST_X, top + 1))
        back.append(self.dest)

        self.font = font
        self.badge = Rect(0, top, BADGE_WIDTH, ROW_HEIGHT, fill=0x000000)
        self.route = _label(font, 0x000000, (0, 0), (1, top))
        # WIDTH + 1: the last column of a label is blank letter spacing, so the minutes
        # end on the panel's last column
        if config.TIMES_PER_ROW == 1:
            self.times = _label(font, config.TIME_COLOR, (1, 0), (WIDTH + 1, top))
        else:
            self.times = _label(small, config.TIME_COLOR, (1, 0), (WIDTH + 1, top + 1))
        self.parts = (self.dest, self.badge, self.route, self.times)
        for part in self.parts[1:]:
            front.append(part)

        self._rgb = None
        self._overflow = 0     # pixels of destination that don't fit
        self._scroll_from = 0.0
        self._offset = 0
        self.hide()

    def show(self, label, rgb, minutes, dest, now):
        if rgb != self._rgb:
            self._rgb = rgb
            self.badge.fill = color(rgb)
        if _set_text(self.route, label):
            first, last = _ink(self.font, label)
            self.route.anchored_position = ((BADGE_WIDTH - (last - first + 1)) // 2 - first, self.top)
        _set_text(self.times, ",".join(str(min(m, 99)) for m in minutes))
        if _set_text(self.dest, dest):
            # the last column of a label is blank letter spacing
            self._overflow = max(0, self.dest.bounding_box[2] - 1 - (DEST_END - DEST_X))
            self._scroll_from = now
            self._move(0)
        for part in self.parts:
            part.hidden = False

    def hide(self):
        for part in self.parts:
            part.hidden = True

    def scroll(self, now):
        if not self._overflow or self.dest.hidden:
            return
        cycle = SCROLL_HOLD + self._overflow * SCROLL_STEP + SCROLL_END_HOLD
        t = (now - self._scroll_from) % cycle - SCROLL_HOLD
        self._move(min(self._overflow, max(0, int(t / SCROLL_STEP))))

    def _move(self, offset):
        if offset != self._offset:
            self._offset = offset
            self.dest.anchored_position = (DEST_X - offset, self.top + 1)


class Screen:
    def __init__(self):
        self.matrix = Matrix(width=WIDTH, height=HEIGHT, bit_depth=config.BIT_DEPTH)
        font = bitmap_font.load_font(config.FONT)
        small = bitmap_font.load_font(config.SMALL_FONT)
        # Load the characters up front so the first draw of each one isn't slow
        font.load_glyphs("0123456789 ABCDEFGHIJKLMNOPQRSTUVWXYZ")  # badges, minutes, messages
        small.load_glyphs("0123456789:,ABCDEFGHIJKLMNOPQRSTUVWXYZ -/.&'")

        # Layers, bottom to top: scrolling destinations, masks, everything else
        back, front = displayio.Group(), displayio.Group()
        root = displayio.Group()
        root.append(back)
        rows_height = ROW_TOPS[-1] + ROW_HEIGHT - ROW_TOPS[0]
        for x, w in ((0, DEST_X), (DEST_END, WIDTH - DEST_END)):
            root.append(Rect(x, ROW_TOPS[0], w, rows_height, fill=0x000000))
        root.append(front)
        self.rows = [Row(top, font, small, back, front) for top in ROW_TOPS]

        # y = -1 puts the header's ink on rows 0-4, leaving row 5 clear above the badges
        self.title = _label(small, config.TITLE_COLOR, (0, 0), (0, -1))
        self.clock = _label(small, config.CLOCK_COLOR, (1, 0), (WIDTH + 1, -1))
        self.message = _label(font, config.MESSAGE_COLOR, (0.5, 0.5), (WIDTH // 2, 19))
        for item in (self.title, self.clock, self.message):
            front.append(item)

        self.busy_mark = Rect(WIDTH - 23, 2, 1, 1, fill=color(config.CLOCK_COLOR))
        self.busy_mark.hidden = True
        front.append(self.busy_mark)

        self.matrix.display.root_group = root

    def show_message(self, title, text):
        _set_text(self.title, title)
        for row in self.rows:
            row.hide()
        _set_text(self.message, text)
        self.message.hidden = False

    def show_page(self, title, rows, status, now):
        _set_text(self.title, title)
        if status:
            self.show_message(title, status)
            return
        self.message.hidden = True
        for i, row in enumerate(self.rows):
            if i < len(rows):
                row.show(*rows[i], now)
            else:
                row.hide()

    def scroll(self, now):
        for row in self.rows:
            row.scroll(now)

    def set_clock(self, text):
        _set_text(self.clock, text)

    def set_busy(self, busy):
        self.busy_mark.hidden = not busy
