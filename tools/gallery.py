"""p(bloom) Wallpapers: the full-screen gallery.

GTK 4 with python-gobject (both in Omarchy's base), drawn like the sheets themselves: the image fills the screen,
and a 30-unit strip along the bottom edge (units of 1/1080 of the screen height) carries the position and the keys,
set in Nimbus Sans with the sheets' tracking and their boxed letters. The strip fades out after three seconds without
input and comes back on any key or pointer movement.

Keys: Left/Right browse (wrapping), Home/End, Enter makes the wallpaper the desktop background, S opens settings and
reloads the set when they are saved, I hides or shows the strip, F toggles fullscreen, Esc or Q closes.
The file on screen is re-read when it changes on disk, so the development viewers see new renders live.
"""
import sys
import threading
import time
from pathlib import Path

import cairo
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

NAVY = (9/255, 13/255, 22/255)
ICE = (217/255, 232/255, 1.0)
MUTED = (140/255, 160/255, 192/255)
POLLEN = (245/255, 201/255, 69/255)
BOX = (150/255, 170/255, 200/255)
FACE = 'Nimbus Sans'
CAP = 0.729              # Nimbus Sans cap height, in em
KEYS = ((('←', '→'), 'BROWSE'), (('↵',), 'SET AS DESKTOP'), (('S',), 'SETTINGS'), (('I',), 'HIDE'), (('ESC',), 'CLOSE'))
IDLE = 3.0               # seconds before the strip fades
FADE = 0.22              # seconds of the fade


def _face(cr, size, bold=False):
    cr.select_font_face(FACE, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(size)


def _tracked(cr, x, baseline, text, track, draw=True):
    """Set text letter by letter with tracking (em); returns the advance."""
    size = cr.get_font_matrix().xx
    x0 = x
    for i, ch in enumerate(text):
        if draw:
            cr.move_to(x, baseline)
            cr.show_text(ch)
        x += cr.text_extents(ch).x_advance + (track*size if i < len(text)-1 else 0)
    return x - x0


def draw_strip(cr, width, height, index, count, alpha=1.0, keys=KEYS):
    """The strip, `height` device pixels tall, drawn with its top-left corner at the origin.

    Laid out in units of height/30 and snapped to device pixels. The one-pixel hairline is the strip's top edge;
    everything else is centred in the band below it, by ink: each run of caps or digits, each key box, each glyph
    inside its box. Box heights are chosen so the space above and below them is equal to the pixel."""
    u = height/30
    snap = round
    centre = (1 + height)/2                                 # the band below the hairline, rows 1 .. height-1

    def baseline(text):
        ext = cr.text_extents(text)
        return snap(centre - (ext.y_bearing + ext.height/2))

    cr.save()
    # unhinted outlines and metrics, so the ink lands where text_extents says it does
    options = cairo.FontOptions()
    options.set_hint_style(cairo.HINT_STYLE_NONE)
    options.set_hint_metrics(cairo.HINT_METRICS_OFF)
    options.set_antialias(cairo.ANTIALIAS_GRAY)
    cr.set_font_options(options)
    cr.push_group()
    cr.set_source_rgba(*NAVY, 0.93)
    cr.rectangle(0, 0, width, height)
    cr.fill()
    cr.set_source_rgba(1, 1, 1, 0.14)
    cr.rectangle(0, 0, width, 1)
    cr.fill()
    margin = snap(24*u)
    # position: the number in Pollen, the count muted, one size, one centre line
    _face(cr, 12*u, bold=True)
    number = f'{index:02d}'
    base = baseline(number + str(count))
    cr.set_source_rgb(*POLLEN)
    x = margin + _tracked(cr, margin, base, number, 0.08)
    _face(cr, 12*u)
    cr.set_source_rgb(*MUTED)
    _tracked(cr, x + snap(8*u), base, f'/  {count}', 0.16)
    # keys, right-aligned: boxed key caps like the sheets' view letters, then the action in tracked caps
    box_h = snap(19*u)
    if (height - 1 - box_h) % 2:
        box_h += 1
    top = 1 + (height - 1 - box_h)//2

    def layout(draw, x):
        for caps, label in keys:
            for key in caps:
                arrow = key in '←→↵'
                _face(cr, (14 if arrow else 11)*u, bold=True)
                ext = cr.text_extents(key)
                w = max(box_h, snap(ext.width + 10*u))
                if draw:
                    cr.set_source_rgba(*BOX, 0.95)
                    cr.set_line_width(1)
                    cr.rectangle(x + 0.5, top + 0.5, w - 1, box_h - 1)
                    cr.stroke()
                    cr.set_source_rgb(*ICE)
                    cr.move_to(snap(x + (w - ext.width)/2 - ext.x_bearing),
                               snap(top + box_h/2 - ext.y_bearing - ext.height/2))
                    cr.show_text(key)
                x += w + snap(4*u)
            x += snap(6*u)
            _face(cr, 10*u)
            cr.set_source_rgb(*MUTED)
            x += _tracked(cr, x, baseline(label), label, 0.24, draw)
            x += snap(26*u)
        return x - snap(26*u)

    total = layout(False, 0)
    layout(True, width - margin - total)
    cr.pop_group_to_source()
    cr.paint_with_alpha(alpha)
    cr.restore()


class Gallery:
    def __init__(self, files, first, set_desktop=None, settings=None):
        # the strip lists only the keys this gallery answers (the development viewers have no desktop or settings)
        self.keys = tuple(k for k in KEYS if (k[1] != 'SET AS DESKTOP' or set_desktop) and (k[1] != 'SETTINGS' or settings))
        self.files = [Path(f) for f in files]
        self.index = self.files.index(Path(first)) if Path(first) in self.files else 0
        self.set_desktop, self.settings = set_desktop, settings
        self.cache, self.mtimes, self.lock = {}, {}, threading.Lock()
        self.size = None
        self.strip_on, self.alpha, self.last_input = True, 1.0, time.monotonic()
        self.loop = GLib.MainLoop()
        GLib.set_prgname('p-bloom-wallpapers')               # the window class Omarchy's Super+O rule matches
        GLib.set_application_name('p(bloom) Wallpapers')
        win = self.window = Gtk.Window(title='p(bloom) Wallpapers')
        win.set_decorated(False)
        win.set_default_size(1600, 900)                       # the size after F leaves fullscreen
        provider = Gtk.CssProvider()
        provider.load_from_string('window { background: #000; }')
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        overlay = Gtk.Overlay()
        self.picture = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN, can_shrink=True)
        overlay.set_child(self.picture)
        self.strip = Gtk.DrawingArea(valign=Gtk.Align.END, halign=Gtk.Align.FILL, can_target=False)
        self.strip.set_draw_func(self._draw_strip)
        self.strip.set_content_height(30)
        overlay.add_overlay(self.strip)
        win.set_child(overlay)
        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', self._key)
        win.add_controller(keys)
        motion = Gtk.EventControllerMotion()
        motion.connect('motion', lambda *_: self._wake())
        win.add_controller(motion)
        win.connect('close-request', lambda *_: self.loop.quit() or False)
        win.connect('notify::default-height', lambda *_: self._resized())
        win.fullscreen()
        win.present()
        GLib.timeout_add(16, self._tick)
        GLib.timeout_add(1000, self._watch)

    # images: scaled once to the window on a worker thread, neighbours prepared ahead
    def _target(self):
        w, h = self.window.get_width(), self.window.get_height()
        scale = self.window.get_scale_factor() or 1
        return (max(1, w*scale), max(1, h*scale)) if w and h else None

    def _load(self, path, size):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(path))
        k = min(size[0]/pixbuf.get_width(), size[1]/pixbuf.get_height())
        if k < 1:
            pixbuf = pixbuf.scale_simple(max(1, round(pixbuf.get_width()*k)), max(1, round(pixbuf.get_height()*k)),
                                         GdkPixbuf.InterpType.HYPER)
        return Gdk.Texture.new_for_pixbuf(pixbuf)

    def _prepare(self, i, size):
        files = self.files
        path = files[i % len(files)]
        key = (path, size, path.stat().st_mtime_ns)
        with self.lock:
            if key in self.cache:
                return self.cache[key]
        texture = self._load(path, size)
        with self.lock:
            self.cache[key] = texture
            # keep the shown sheet and its two neighbours at the current size
            near = {files[(self.index + d) % len(files)] for d in (-1, 0, 1)}
            for old in [k for k in self.cache if k[1] != size or k[0] not in near]:
                self.cache.pop(old, None)
        return texture

    def _show(self):
        size = self._target()
        if not size:
            return
        self.size = size
        self.strip.set_content_height(self._strip_height())
        self.picture.set_paintable(self._prepare(self.index, size))
        self.window.set_title(f'p(bloom) Wallpapers — {self.index + 1}/{len(self.files)} — {self.files[self.index].name}')
        self.strip.queue_draw()
        for step in (1, -1):
            threading.Thread(target=self._prepare, args=(self.index + step, size), daemon=True).start()

    def _resized(self):
        if self._target() != self.size:
            self._show()

    def _watch(self):
        path = self.files[self.index]
        try:
            mtime = path.stat().st_mtime_ns
        except OSError:
            return True
        if self.mtimes.get(path, mtime) != mtime:
            self._show()
        self.mtimes[path] = mtime
        return True

    # the strip: drawn in cairo, faded by alpha
    def _strip_height(self):
        return max(24, round((self.window.get_height() or 1080)*30/1080))

    def _draw_strip(self, area, cr, width, height):
        if self.alpha > 0:
            draw_strip(cr, width, height, self.index + 1, len(self.files), self.alpha, self.keys)

    def _wake(self):
        self.last_input = time.monotonic()

    def _tick(self):
        if self.size is None:
            self._show()
        idle = time.monotonic() - self.last_input
        want = 1.0 if self.strip_on and idle < IDLE else 0.0
        if want != self.alpha:
            step = 0.016/FADE
            self.alpha = min(want, self.alpha + step) if want > self.alpha else max(want, self.alpha - step)
            self.strip.queue_draw()
        return True

    def _key(self, controller, keyval, keycode, state):
        self._wake()
        name = Gdk.keyval_name(keyval) or ''
        if name in ('Right', 'Left'):
            self.index = (self.index + (1 if name == 'Right' else -1)) % len(self.files)
            self._show()
        elif name in ('Home', 'End'):
            self.index = 0 if name == 'Home' else len(self.files) - 1
            self._show()
        elif name in ('Return', 'KP_Enter') and self.set_desktop:
            threading.Thread(target=self.set_desktop, args=(self.files[self.index],), daemon=True).start()
        elif name.lower() == 's' and self.settings:
            self.settings(self)
        elif name.lower() == 'i':
            self.strip_on = not self.strip_on
        elif name.lower() == 'f':
            if self.window.is_fullscreen():
                self.window.unfullscreen()
            else:
                self.window.fullscreen()
        elif name in ('Escape',) or name.lower() == 'q':
            self.loop.quit()
        return True

    def replace(self, files):
        """A new set after settings were saved: same wallpaper, new files."""
        name = self.files[self.index].name
        self.files = [Path(f) for f in files]
        self.index = next((i for i, f in enumerate(self.files) if f.name == name), 0)
        with self.lock:
            self.cache.clear()
        self._show()

    def run(self):
        self.loop.run()


def run(files, first, set_desktop=None, settings=None):
    Gallery(files, first, set_desktop, settings).run()


if __name__ == '__main__':
    files = sorted(Path(sys.argv[1]).glob('*.webp'))
    run(files, files[0])
