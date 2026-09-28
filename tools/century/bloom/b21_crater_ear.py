"""b21 CRATER EAR: text, field notes and side diagrams.

Numbers (narrative, consistent with the model):
Dish 1 km across (radius 500 m), paraboloid f = 250 m, in a 1.5 km crater.
Band 5-40 MHz -> wavelengths 60-7.5 m. Mesh spacing 40 cm = lambda / 19 at
40 MHz, fine enough to reflect.
Hydrogen 21 cm line: f = 1420 MHz / (1 + z). 40 MHz -> z = 34.5;
5 MHz -> z = 283: the cosmic dark ages, before and around the first stars.
Earth's ionosphere reflects or absorbs most radio below ~10 MHz, and
Earth's own transmitters drown the rest; the far side is shielded by
3 474 km of Moon. Data leave through a relay orbiter (one pass a day).
"""
import math

ENTRY = dict(
    id='b21', series='B21', number=221, slug='crater-ear', title='CRATER EAR',
    domain='astronomy', category='serious', model='CE-1', palette='graphite', seed=260121,
    purpose='LUNAR CRATER RADIO TELESCOPE',
    narrative=('A wire-mesh dish strung across a crater on the far side of the Moon listens to the '
               "universe's first hydrogen, shielded from every radio on Earth. Robots hung and "
               'tensioned the whole kilometre of mesh.'),
    enabled_by=[
        ('FAR-SIDE QUIET', 'The Moon itself blocks every transmitter on Earth from the far side.'),
        ('CRATER DISHES', 'Studies such as LCRT: a wire dish hung in a natural crater instead of on towers.'),
        ('CABLE ROBOTS', 'Climbing robots that deploy and tension long cables without people.'),
    ],
    real_basis='The LCRT study, the radio quiet of the lunar far side and wire-climbing robots.',
    required_breakthroughs='Deploying and tensioning a kilometre-wide mesh by robots alone.',
    view_A='KILOMETRE MESH IN A FAR-SIDE CRATER',
    view_B='RECEIVER CABIN', view_B_note='FEED HORN / CROSSED DIPOLES / WINCH PODS / RADIATORS',
    view_C='ANCHOR CLIMBER', view_C_note='DRIVE SHEAVES / SOLAR DECK / TENSIONER / BALLAST',
    service_year='2048',
    sources=['https://www.nasa.gov/general/lunar-crater-radio-telescope-lcrt-on-the-far-side-of-the-moon/',
             'https://doi.org/10.1016/j.physrep.2006.08.002'],
    source_scope='Real basis only: the LCRT concept study, 21 cm cosmology and far-side radio quiet. The dish, crater, robots and all figures are an original concept.',
)

DOSSIER = dict(
    kind='far side',
    fact=('Before the first stars, hydrogen gas filled the universe. Its faint 21 cm signal is '
          'now stretched into waves metres long, and only a sky without radios can hear it.'),
    rows=[('DISH', '1 km / WIRES EVERY 40 cm'),
          ('LISTENS AT', '5 TO 40 MHz / 60 TO 7.5 m WAVES'),
          ('HYDROGEN FROM', 'REDSHIFT 35 TO 280'),
          ('DATA HOME', 'RELAY ORBITER / ONE PASS A DAY')],
    note='ON EARTH, A TEN-YEAR-OLD LISTENS TO THE FIRST HYDROGEN, PLAYED AS SOUND.',
    left=('OLDER LIGHT, LONGER WAVES', 'f = 1420 MHz / (1 + z) / DECLARED BAND',
          "Below about 10 MHz Earth's ionosphere closes the sky; the far side stays open."),
    right=('THE MOON AS A SHIELD', 'RADIO SHADOW / NOT TO SCALE',
           'The far side never faces Earth; the relay carries the data home.'),
)


def figure(s, side, x, y, w):
    from sheet import WHITE, ARC, GOLD
    from century.editorial import tx, arrow, axes, curve
    if side == 'left':
        px, py, pw, ph = x + 30, y, 330, 100
        axes(s, px, py, pw, ph, 'REDSHIFT z', '100 MHz', '0')
        f = lambda z: 1420 / (1 + z)
        X = lambda z: px + pw * z / 300
        Y = lambda mhz: py + ph * (1 - mhz / 100)
        pts = [(X(z), Y(f(z))) for z in [13.2 + (300 - 13.2) * i / 160 for i in range(161)]]
        s.poly(pts, .5, .6, close=False)
        band = [(X(z), Y(f(z))) for z in [34.5 + (283 - 34.5) * i / 120 for i in range(121)]]
        curve(s, band, ARC)
        for mhz in (40, 5):
            s.ln(px, Y(mhz), px + pw, Y(mhz), .3, .5, dash=[2, 3], color=ARC)
        tx(s, '40', px - 9, Y(40) + 3, 6.2, .7, align='r', color=ARC)
        s.ln(px, Y(10), px + pw, Y(10), .35, .5, dash=[1, 4], color=GOLD)
        tx(s, 'IONOSPHERE', px + pw + 8, Y(10) + 3, 6.2, .75, color=GOLD)
        if s.type_growth(6.4):
            # Enlarged type (composed profiles): right-aligned between the
            # 50 and 75 MHz grid lines, clear of the curve.
            tx(s, 'DARK AGES / 5 TO 40 MHz', px + pw, Y(54), 6.4, .85, align='r', color=ARC)
        else:
            tx(s, 'DARK AGES / 5 TO 40 MHz', X(215), Y(66), 6.4, .85, align='c', color=ARC)
        for z in (0, 100, 200, 300):
            tx(s, str(z), X(z), py + ph + 13, 6.2, .6, align='c')
    else:
        cy = y + 62
        ex, er = x + 40, 26
        mx, mr = x + 250, 34
        s.circ(ex, cy, er, .8, .7)
        tx(s, 'EARTH', ex, cy + er + 16, 6.4, .7, align='c')
        s.circ(mx, cy, mr, .8, .7)
        tx(s, 'MOON', mx, cy + mr + 16, 6.4, .7, align='c')
        # Radio from Earth stops at the near side.
        for dy in (-22, -8, 8, 22):
            arrow(s, (ex + er + 6, cy + dy * .6), (mx - math.sqrt(max(0, mr * mr - dy * dy)) - 3, cy + dy), GOLD)
        # Shadow behind the Moon: tangent lines, hatched quiet zone.
        for sg in (-1, 1):
            s.ln(mx, cy + sg * mr, x + 430, cy + sg * (mr - 12), .45, .55, dash=[3, 3])
        for k in range(6):
            xx = mx + mr + 14 + k * 22
            s.ln(xx, cy - mr + 8, xx + 10, cy + mr - 8, .15, .5)
        tx(s, 'RADIO SHADOW', x + 330, cy + mr + 16, 6.4, .8)
        s.dot(mx + mr, cy, 3.4, .95, color=ARC)
        tx(s, 'THE DISH', mx + mr + 12, cy - mr - 2, 6.4, .9, color=ARC)
        # Relay orbiter: a dashed link up to it and back toward Earth.
        rx, ry = mx + 20, y + 4
        s.rect(rx - 4, ry - 3, 8, 6, .8, .6)
        tx(s, 'RELAY', rx + 10, ry + 3, 6.4, .75)
        s.ln(mx + mr - 2, cy - 4, rx, ry + 4, .5, .55, dash=[2, 2], color=ARC)
        s.ln(rx - 5, ry, ex + er * .7, cy - er * .7, .4, .5, dash=[2, 3], color=ARC)
