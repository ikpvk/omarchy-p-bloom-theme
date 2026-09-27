"""b18 STELLARATOR HEARTH: text, field notes and side diagrams.

Narrative numbers, consistent with the model docstring:
Plasma: R0 = 12 m, rotating ellipse 1.9 x 0.9 m half-axes -> volume
2 pi R0 x pi a b = 2 pi 12 x pi 1.9 x 0.9 = 405 m3.
Fusion power 800 MW (about 2 MW per m3, D-T). Blanket energy gain 1.1
-> 880 MW of heat. Turbine efficiency 40 % -> 350 MW gross electric.
Cryoplant, heating, pumps: 50 MW -> 300 MW net. 300 MW / 200 000 people
= 1.5 kW per person on average (homes, trams, workplaces).
Rejected heat 880 - 350 = 530 MW.
Fuel: 17.6 MeV per D-T reaction -> 800e6 / 2.82e-12 J = 2.84e20 /s
-> 2.45e25 reactions a day -> deuterium 2.45e25 x 3.34e-27 kg = 82 g,
tritium 2.45e25 x 5.01e-27 kg = 123 g: about 200 g of fuel a day
(the tritium is bred from lithium in the blanket).
Field on axis 5 T from fifty HTS coils at 20 K (-253 C).
"""
import math

ENTRY = dict(
    id='b18', series='B18', number=218, slug='stellarator-hearth', title='STELLARATOR HEARTH',
    domain='energy', category='serious', model='SH-5', palette='violet', seed=260118,
    purpose='SMALL FUSION POWER PLANT',
    narrative=('A twisted ring of superconducting coils holds a burning plasma steady enough to '
               'light a city of 200 000 without smoke. It runs for months at a time on about '
               '200 grams of fuel a day.'),
    enabled_by=[
        ('STELLARATORS', 'Wendelstein 7-X showed that computer-shaped coils hold a steady plasma for minutes.'),
        ('HTS MAGNETS', 'Superconducting tape that makes strong fields at 20 K from compact coils.'),
        ('COIL DESIGN', 'Codes that shape each coil so the twisted field keeps the plasma off the wall.'),
    ],
    real_basis='Wendelstein 7-X, high-temperature superconducting magnets and stellarator optimisation.',
    required_breakthroughs='Materials and blankets that survive years of fusion neutrons.',
    view_A='FIVE-PERIOD STELLARATOR, CUT OPEN',
    view_B='TWISTED COIL', view_B_note='CASING OPEN / WINDING PACK / HELIUM LINES / LUGS',
    view_C='DIVERTOR TILE', view_C_note='TUNGSTEN MONOBLOCKS / COOLING TUBES / MANIFOLDS',
    service_year='2052',
    sources=['https://www.ipp.mpg.de/w7x', 'https://doi.org/10.1017/S0022377823000971'],
    source_scope='Real basis only: the stellarator principle and Wendelstein 7-X results, HTS magnet development, divertor monoblock technology. The plant, its geometry, power figures and service year are an original concept.',
)

DOSSIER = dict(
    kind='hearth',
    fact=('The coils are twisted so the magnetic field twists by itself. No current has to be '
          'driven through the plasma, so it can burn steadily for months.'),
    rows=[('FUSION POWER', '800 MW / DEUTERIUM + TRITIUM'),
          ('NET ELECTRICITY', '300 MW / 200 000 PEOPLE'),
          ('FUEL', 'ABOUT 200 g A DAY'),
          ('FIELD ON AXIS', '5 T / 50 COILS AT 20 K')],
    note='ON WINTER EVENINGS THE CITY IS LIT AND THE AIR IS CLEAR.',
    left=('WHERE THE 800 MW GO', 'DECLARED DESIGN BUDGET / MEGAWATTS',
          '800 x 1.1 = 880 MW of heat; 40 % becomes 350 MW; 50 MW runs the plant.'),
    right=('A TWIST INSTEAD OF A CURRENT', 'ROTATING ELLIPSE / ONE FIELD PERIOD / SIMPLIFIED',
           'The section turns half a turn per period; a field line circles the plasma.'),
)


def figure(s, side, x, y, w):
    from sheet import WHITE, ARC, GOLD
    from century.editorial import tx, arrow
    if side == 'left':
        bx = x + 110; k = 290 / 880       # 880 MW spans 290 units
        rows = [('HEAT', [(880, WHITE, .75)], '880'),
                ('ELECTRIC', [(300, ARC, .9), (50, GOLD, .9)], '350'),
                ('TO COOLING', [(530, WHITE, .35)], '530')]
        for i, (label, parts, total) in enumerate(rows):
            yy = y + 10 + i * 34
            tx(s, label, x, yy + 5, 6.6, .72)
            xx = bx
            for v, col, a in parts:
                s.rect(xx, yy - 5, v * k, 12, a, .7, color=col)
                xx += v * k
            tx(s, total + ' MW', xx + 8, yy + 5, 6.6, .8)
        tx(s, 'CITY 300', bx + 6, y + 49, 6.2, .9, color=ARC)
        tx(s, 'FUSION 800 MW + BLANKET GAIN 80 MW', bx, y + 118, 6.2, .6)
        # Short labels under the electric bar: city (accent) and the plant's own share (gold).
        s.ln(bx + 300 * k + 1, y + 51, bx + 325 * k, y + 60, .4, .5, color=GOLD)
        tx(s, 'PLANT 50', bx + 330 * k, y + 64, 6.2, .8, color=GOLD)
    else:
        # Five sections along one period: the ellipse turns by half a turn;
        # the dot is where one field line crosses each section (iota ~ 0.9).
        cy = y + 55
        for i in range(5):
            cx = x + 40 + i * 80
            al = math.pi * i / 4
            pts = []
            for j in range(49):
                t = math.tau * j / 48
                u = 26 * math.cos(t); v = 12 * math.sin(t)
                pts.append((cx + u * math.cos(al) - v * math.sin(al), cy - (u * math.sin(al) + v * math.cos(al))))
            s.poly(pts, .75, .7, close=True)
            t = .5 + math.tau * .9 * i / 5 / 2
            u = 20 * math.cos(t); v = 9 * math.sin(t)
            s.dot(cx + u * math.cos(al) - v * math.sin(al), cy - (u * math.sin(al) + v * math.cos(al)), 2.2, .95, color=ARC)
            s.ln(cx, cy - 34, cx, cy + 34, .15, .4)
            tx(s, ('0', '1/4', '1/2', '3/4', '1')[i], cx, cy + 50, 6.2, .6, align='c')
        arrow(s, (x + 40, cy + 64), (x + 360, cy + 64), WHITE)
        tx(s, 'ALONG THE RING', x + 370, cy + 67, 6.4, .65)
        tx(s, 'FIELD LINE', x + 370, cy - 30, 6.4, .8, color=ARC)
