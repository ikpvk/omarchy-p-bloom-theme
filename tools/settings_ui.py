"""p(bloom) Wallpapers: the settings menu, drawn over the gallery's wallpaper like a game's pause menu.

The gallery dims the wallpaper and shows a centred panel set like its strip and the sheets. Background level (Muted,
Default, Vivid) is a three-way switch; resolution is a list, Automatic first, every set with its size and whether it is
the optimal one, installed or still a download. Keys are boxed like the gallery's: ← → background, ↑ ↓ resolution,
Enter saves, Esc or S closes. Units are 1/1080 of the window's height; everything is drawn at the screen's own pixels
and centred by ink, as in gallery.draw_strip.
"""
import cairo

from gallery import BOX, ICE, MUTED, NAVY, POLLEN, _face, _tracked, key_hints, keycap_metrics

LEVELS = ('muted', 'default', 'vivid')
LEVEL_LABELS = {'muted': 'MUTED', 'default': 'DEFAULT', 'vivid': 'VIVID'}
HINT = 'How strong the background colour is.'
KEYS = ((('←', '→'), 'BACKGROUND'), (('↑', '↓'), 'RESOLUTION'), (('↵',), 'SAVE'), (('ESC',), 'CANCEL'))


def rows(plan, level):
    """(profile, resolution, megabytes, tag) for the list; the first row is Automatic."""
    options = (plan.get('options_by_level') or {}).get(level) or plan['options']
    best = plan.get('profile')
    out = [('auto', 'AUTOMATIC', None, None)]
    for o in options:
        size = ' × '.join(map(str, o['size']))
        mb = f"{o['total_bytes']/1_000_000:.1f} MB" if o.get('total_bytes') is not None else ''
        tag = 'OPTIMAL' if o['profile'] == best else ('INSTALLED' if o.get('local', True) else 'DOWNLOAD')
        out.append((o['profile'], size, mb, tag))
    return out


def optimal_size(plan, level):
    options = (plan.get('options_by_level') or {}).get(level) or plan['options']
    best = plan.get('profile')
    o = next((o for o in options if o['profile'] == best), None)
    return ' × '.join(map(str, o['size'])) if o else ''


def draw_settings(cr, W, H, plan, level, selected):
    u = min(H/1080, W/1000)                                    # a portrait screen: the panel fits its width
    snap = round
    options = cairo.FontOptions()
    options.set_hint_style(cairo.HINT_STYLE_NONE)
    options.set_hint_metrics(cairo.HINT_METRICS_OFF)
    options.set_antialias(cairo.ANTIALIAS_GRAY)
    cr.set_font_options(options)
    cr.set_source_rgba(4/255, 6/255, 11/255, 0.70)          # the wallpaper behind stays visible, quieted
    cr.paint()

    def centred(text, mid):
        ext = cr.text_extents(text)
        return snap(mid - (ext.y_bearing + ext.height/2))

    def width_of(text, track):
        return _tracked(cr, 0, 0, text, track, draw=False)

    table = rows(plan, level)
    # one vertical scale: a section starts SECTION below what precedes it, its label LABEL above its content
    pw, pad, row_h = snap(760*u), snap(44*u), snap(30*u)
    SECTION, LABEL, footer_h = snap(36*u), snap(18*u), snap(76*u)
    title_mid, rule_y = snap(46*u), snap(80*u)                   # from the panel's top padding
    seg_h, hint_gap = snap(36*u), snap(22*u)
    fixed = (pad + rule_y + SECTION + LABEL + seg_h + hint_gap + SECTION + LABEL + SECTION//2 + footer_h)
    room = H - snap(120*u) - fixed
    visible = max(5, min(len(table), room//row_h))
    first = min(max(0, selected - visible//2), max(0, len(table) - visible))
    ph = fixed + visible*row_h
    x0, y0 = snap((W - pw)/2), snap((H - ph)/2)
    inner0, inner1 = x0 + pad, x0 + pw - pad
    # the panel: navy, a hairline border, the sheets' corner marks just outside it
    cr.set_source_rgba(*NAVY, 0.95)
    cr.rectangle(x0, y0, pw, ph)
    cr.fill()
    cr.set_source_rgba(1, 1, 1, 0.14)
    cr.set_line_width(1)
    cr.rectangle(x0 + 0.5, y0 + 0.5, pw - 1, ph - 1)
    cr.stroke()
    mark, off = snap(22*u), snap(10*u)
    cr.set_source_rgba(*ICE, 0.55)
    for cx, cy, sx, sy in ((x0 - off, y0 - off, 1, 1), (x0 + pw + off, y0 - off, -1, 1),
                           (x0 - off, y0 + ph + off, 1, -1), (x0 + pw + off, y0 + ph + off, -1, -1)):
        cr.move_to(cx + 0.5*sx, cy + sy*mark)
        cr.line_to(cx + 0.5*sx, cy + 0.5*sy)
        cr.line_to(cx + sx*mark, cy + 0.5*sy)
    cr.stroke()
    # header: the app's name small, SETTINGS as a sheet title, a rule
    y = y0 + pad
    _face(cr, 10*u)
    cr.set_source_rgb(*MUTED)
    _tracked(cr, inner0, centred('P', y + snap(6*u)), 'P(BLOOM) WALLPAPERS', 0.28)
    _face(cr, 26*u, bold=True)
    cr.set_source_rgb(*ICE)
    _tracked(cr, inner0, centred('S', y + title_mid), 'SETTINGS', 0.3)
    y += rule_y
    cr.set_source_rgba(1, 1, 1, 0.14)
    cr.rectangle(inner0, y, inner1 - inner0, 1)
    cr.fill()

    def label(text, y):
        _face(cr, 9*u)
        cr.set_source_rgb(*MUTED)
        _tracked(cr, inner0, centred(text[0], y), text, 0.28)
    # background level: a three-way switch
    y += SECTION
    label('BACKGROUND', y)
    seg_top = y + LABEL
    cell = (inner1 - inner0)//3
    for k, name in enumerate(LEVELS):
        cx0 = inner0 + k*cell
        cw = cell if k < 2 else inner1 - cx0
        on = name == level
        if on:
            cr.set_source_rgba(*ICE, 0.10)
            cr.rectangle(cx0, seg_top, cw, seg_h)
            cr.fill()
        cr.set_source_rgba(*(ICE if on else BOX), 0.95 if on else 0.55)
        cr.rectangle(cx0 + 0.5, seg_top + 0.5, cw - 1, seg_h - 1)
        cr.stroke()
        _face(cr, 11*u, bold=on)
        cr.set_source_rgb(*(ICE if on else MUTED))
        text = LEVEL_LABELS[name]
        _tracked(cr, snap(cx0 + (cw - width_of(text, 0.24))/2), centred('M', seg_top + seg_h/2), text, 0.24)
    y = seg_top + seg_h + hint_gap
    _face(cr, 11*u)
    cr.set_source_rgb(*MUTED)
    cr.move_to(inner0, centred('H', y))
    cr.show_text(HINT)
    # resolution: Automatic, then every set; the selected row lit, with a Pollen bar in the margin at its left
    y += SECTION
    label('RESOLUTION', y)
    if first > 0 or first + visible < len(table):            # more rows than fit: a quiet count of what is shown
        _face(cr, 9*u)
        cr.set_source_rgb(*MUTED)
        more = f'{first + 1}–{first + visible} OF {len(table)}'
        _tracked(cr, inner1 - snap(width_of(more, 0.24)), centred('R', y), more, 0.24)
    top = y + LABEL
    mb_right = inner0 + snap(330*u)
    for n, (profile, name, mb, tag) in enumerate(table[first:first + visible]):
        i = first + n
        ry = top + n*row_h
        mid = ry + row_h/2
        if i == selected:
            bleed = snap(14*u)
            cr.set_source_rgba(*ICE, 0.08)
            cr.rectangle(inner0 - bleed, ry, inner1 - inner0 + 2*bleed, row_h)
            cr.fill()
            cr.set_source_rgb(*POLLEN)
            cr.rectangle(inner0 - bleed, ry, max(2, snap(3*u)), row_h)
            cr.fill()
        if profile == 'auto':
            _face(cr, 12*u, bold=True)
            cr.set_source_rgb(*ICE)
            _tracked(cr, inner0, centred('A', mid), 'AUTOMATIC', 0.2)
            note = f'OPTIMAL SET  {optimal_size(plan, level)}'
            _face(cr, 10*u)
            cr.set_source_rgb(*POLLEN)
            _tracked(cr, inner1 - snap(width_of(note, 0.2)), centred('O', mid), note, 0.2)
            continue
        _face(cr, 12*u, bold=i == selected)
        cr.set_source_rgb(*(ICE if i == selected else (0.82, 0.88, 0.97)))
        cr.move_to(inner0, centred('5', mid))
        cr.show_text(name)
        _face(cr, 12*u)
        cr.set_source_rgb(*MUTED)
        ext = cr.text_extents(mb)
        cr.move_to(mb_right - ext.x_advance, centred('5', mid))
        cr.show_text(mb)
        _face(cr, 9*u, bold=tag == 'OPTIMAL')
        cr.set_source_rgb(*(POLLEN if tag == 'OPTIMAL' else MUTED))
        _tracked(cr, inner1 - snap(width_of(tag, 0.24)), centred('O', mid), tag, 0.24)
    # footer: the keys, centred
    fy = top + visible*row_h + SECTION//2
    cr.set_source_rgba(1, 1, 1, 0.14)
    cr.rectangle(inner0, fy, inner1 - inner0, 1)
    cr.fill()
    metrics = keycap_metrics(cr, u, footer_h - 1)
    ktop = fy + 1 + (footer_h - 1 - metrics[1])//2
    band = fy + (1 + footer_h)/2
    total = key_hints(cr, 0, ktop, band, KEYS, metrics, u, draw=False)
    key_hints(cr, snap(x0 + (pw - total)/2), ktop, band, KEYS, metrics, u)


class Menu:
    """The menu's state and keys; the gallery draws it with draw() and passes it the keys while it is open."""

    def __init__(self, plan):
        self.plan = plan
        self.level = plan.get('setting_level', 'default')
        if self.level not in LEVELS:
            self.level = 'default'
        self.selected = next((i for i, r in enumerate(rows(plan, self.level)) if r[0] == plan.get('setting', 'auto')), 0)

    def state(self):
        return self.level, self.selected

    def draw(self, cr, width, height):
        draw_settings(cr, width, height, self.plan, self.level, self.selected)

    def key(self, name):
        """('save', choice), ('cancel', None), or None when the menu stays open."""
        count = len(rows(self.plan, self.level))
        if name in ('Left', 'Right'):
            i = LEVELS.index(self.level) + (1 if name == 'Right' else -1)
            self.level = LEVELS[max(0, min(2, i))]
        elif name in ('Up', 'Down', 'Tab'):
            self.selected = (self.selected + (-1 if name == 'Up' else 1)) % count
        elif name in ('Home', 'End'):
            self.selected = 0 if name == 'Home' else count - 1
        elif name in ('Return', 'KP_Enter'):
            return 'save', {'profile': rows(self.plan, self.level)[self.selected][0], 'level': self.level}
        elif name in ('Escape', 's', 'S', 'q', 'Q'):
            return 'cancel', None
        return None
