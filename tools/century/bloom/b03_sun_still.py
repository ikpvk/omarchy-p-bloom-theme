"""b03 SUN STILL: text, field notes and side diagrams.

Numbers are narrative, kept consistent with the model notes:
Town of 4 000 x 120 L a day = 480 m3 of fresh water a day.
Zero liquid discharge: 500 t seawater a day (35 g salts per kg)
  = 480 t fresh water + 17.5 t salts + 2.5 t moisture left in wet product.
Salts 17.5 t: sodium chloride 13.6, magnesium salts 2.7, gypsum 0.6,
  potassium salts 0.4, other 0.2 (seawater proportions, rounded).
Heat: 14 effects, 70 -> 36 C, gained output ratio 12 -> 2 300 kJ/kg / 12
  = 0.19 MJ/kg x 480 000 kg = 92 GJ = 25.6 MWh of heat a day.
Field: 6.5 kWh/m2 a day direct sun x 0.65 field efficiency = 4.2 kWh/m2
  -> 6 100 m2 of mirror = 380 heliostats of 16 m2. A 16 h hot-water store
  keeps the stack running through the night.
"""

ENTRY = dict(
    id='b03', series='B03', number=203, slug='sun-still', title='SUN STILL',
    domain='water', category='serious', model='SS-14', palette='saffron', seed=260103,
    purpose='SOLAR DESALINATION TOWER',
    narrative=('Gives a coastal town of 4 000 its drinking water from the sea using only '
               'sunlight, and bags the salts as table salt, magnesium and gypsum instead '
               'of returning a brine plume to the bay.'),
    enabled_by=[
        ('DISTILLATION', 'Multi-effect stacks that reuse one input of heat a dozen times, as coastal plants do.'),
        ('SOLAR THERMAL', 'A heliostat field and tower receiver that heat water, with a store for the night.'),
        ('MINERAL RECOVERY', 'Staged crystallisation that separates sodium, magnesium and calcium salts.'),
    ],
    real_basis='Multi-effect distillation, solar thermal collectors, mineral recovery from brine.',
    required_breakthroughs='Low-cost, scale-free evaporator surfaces that last many years in hot brine.',
    view_A='HELIOSTAT-FED DISTILLATION TOWER',
    view_B='EFFECT STACK', view_B_note='SHELL CUT AWAY / TUBE BUNDLES / SPRAY BARS / TRAYS',
    view_C='MIRROR ROW', view_C_note='TWO-AXIS DRIVES / CLEANING ROBOT / ROTARY BRUSH',
    service_year='2036',
    sources=['https://www.iea-shc.org/', 'https://www.nrel.gov/csp/'],
    source_scope='Real basis only: multi-effect distillation, central-receiver solar thermal, brine mineral recovery. The tower, its output and every figure are an original concept.',
)

DOSSIER = dict(
    kind='still',
    fact=('The stack is widest at the bottom: colder vapour is thinner and needs more room. '
          'Heat enters once, at the top, and is used again all the way down.'),
    rows=[('FRESH WATER', '480 m³ A DAY / 4 000 PEOPLE'),
          ('EFFECTS', '14 / 70 TO 36 °C'),
          ('MIRRORS', '380 x 16 m² / 16 h HEAT STORE'),
          ('RECOVERED SALTS', '17.5 t A DAY / NO BRINE')],
    note='THE FIRST BAGS OF SALT WENT TO THE SCHOOL KITCHEN.',
    left=('ONE HEAT, FOURTEEN USES', 'MULTI-EFFECT CASCADE / DECLARED TEMPERATURES',
          'Vapour from each effect condenses in the tubes of the next: heat is used about 12 times.'),
    right=('NOTHING GOES BACK AS BRINE', 'DAILY MASS BALANCE / t PER DAY / DECLARED DESIGN',
           'Seawater 500 t = fresh water 480 t + salts 17.5 t + moisture in the bags 2.5 t.'),
)


def figure(s, side, x, y, w):
    from sheet import WHITE, ARC, GOLD
    from century.editorial import tx, arrow
    if side == 'left':
        # Staircase of effects: 1, 2, 3 ... 14, each 2.6 C cooler than the last.
        shown = [1, 2, 3, None, 13, 14]
        bw, bh = 46, 20
        for i, k in enumerate(shown):
            bx = x + 8 + i * 58; by = y + 8 + i * 16
            if k is None:
                for d in range(3):
                    s.dot(bx + 14 + d * 9, by + bh / 2, 1.2, .7)
                continue
            s.rect(bx, by, bw, bh, .75, .7)
            t = 70 - (k - 1) * 34 / 13
            tx(s, f'{k}', bx + 5, by + 14, 6.4, .85)
            tx(s, f'{t:.0f} °C', bx + bw - 4, by + 14, 6.4, .7, align='r', color=GOLD if k == 1 else WHITE)
            nxt = shown[i + 1] if i + 1 < len(shown) else None
            if nxt:
                arrow(s, (bx + bw, by + bh / 2), (bx + 58, by + 16 + bh / 2 - 4), ARC)
        arrow(s, (x + 31, y - 12), (x + 31, y + 7), GOLD)
        tx(s, 'SUN HEAT', x + 38, y - 3, 6.4, .8, color=GOLD)
        tx(s, 'VAPOUR', x + 92, y + 3, 6.2, .7, color=ARC)
        tx(s, 'DISTILLATE', x + 8, y + 122, 6.4, .7)
        s.ln(x + 8, y + 110, x + 348, y + 110, .5, .6)
        for i in range(6):
            if shown[i] is None:
                continue
            bx = x + 8 + i * 58 + 23
            s.ln(bx, y + 8 + i * 16 + bh, bx, y + 110, .35, .5, dash=[2, 2])
        tx(s, 'GAINED OUTPUT RATIO 12', x + 348, y + 122, 6.4, .8, align='r')
    else:
        # Stacked bar: 500 t seawater -> fresh water / salts / moisture, salts expanded.
        bx = x + 8; bw = 400; scale = bw / 500.0
        by = y + 16
        s.rect(bx, by, bw, 14, .7, .7)
        tx(s, 'SEAWATER 500 t', bx, by - 6, 6.6, .85)
        by2 = y + 58
        parts = [('FRESH WATER', 480, ARC), ('SALTS', 17.5, GOLD), ('', 2.5, WHITE)]
        xx = bx
        for name, v, col in parts:
            ww = v * scale
            s.rect(xx, by2, ww, 14, .8, .7, color=col)
            xx += ww
        tx(s, 'FRESH WATER 480 t', bx, by2 - 6, 6.6, .85, color=ARC)
        arrow(s, (bx + bw / 2, by + 18), (bx + bw / 2, by2 - 12), WHITE)
        # Expanded salt breakdown (13.6 + 2.7 + 0.6 + 0.4 + 0.2 = 17.5 t).
        sx0 = bx + 480 * scale; ex0 = bx + 130; ew = 270
        s.ln(sx0, by2 + 14, ex0, y + 96, .35, .5, dash=[2, 2])
        s.ln(sx0 + 17.5 * scale, by2 + 14, ex0 + ew, y + 96, .35, .5, dash=[2, 2])
        salts = [('NaCl', 13.6), ('Mg', 2.7), ('GYPSUM', .6), ('K', .4), ('', .2)]
        xx = ex0
        for name, v in salts:
            ww = v / 17.5 * ew
            s.rect(xx, y + 96, ww, 12, .8, .65, color=GOLD)
            xx += ww
        tx(s, 'NaCl 13.6', ex0, y + 122, 6.4, .8)
        tx(s, 'Mg 2.7 / GYPSUM 0.6 / K 0.4 / OTHER 0.2', ex0 + ew, y + 122, 6.2, .7, align='r')
        tx(s, 'SALTS 17.5 t', ex0 - 8, y + 106, 6.6, .85, align='r', color=GOLD)
