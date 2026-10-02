from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools'))
try:
    import cairo
    import numpy as np
    import settings_ui
except (ImportError, ValueError) as exc:  # GTK 4 / python-gobject missing
    settings_ui = None
    REASON = str(exc)

PLAN = dict(profile='big', setting='auto', setting_level='default',
            options=[dict(profile='big', size=[3840, 2160], total_bytes=280_000_000, local=False),
                     dict(profile='small', size=[1920, 1080], total_bytes=80_000_000, local=True)])


@unittest.skipIf(settings_ui is None, 'GTK 4 not available')
class SettingsUI(unittest.TestCase):
    def test_rows_are_automatic_then_every_set_with_the_optimal_one_tagged(self):
        self.assertEqual(settings_ui.rows(PLAN),
                         [('auto', 'AUTOMATIC', None), ('big', '3840 × 2160', 'OPTIMAL'), ('small', '1920 × 1080', None)])
        self.assertEqual(settings_ui.optimal_size(PLAN), '3840 × 2160')

    def test_the_panel_fits_every_screen(self):
        many = {**PLAN, 'options': [dict(profile=f'p{i}', size=[1920 + i, 1080], total_bytes=1, local=False)
                                    for i in range(40)]}
        for plan in (PLAN, many):
            for W, H in ((1920, 1080), (5120, 2160), (1080, 1920), (1280, 720), (1024, 768)):
                surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
                settings_ui.draw_settings(cairo.Context(surface), W, H, plan, len(plan['options']))
                alpha = np.ndarray((H, W, 4), np.uint8, surface.get_data())[..., 3]
                ys, xs = np.nonzero(alpha > 230)              # the panel, not the dimmed screen around it
                self.assertTrue(xs.min() > 0 and ys.min() > 0 and xs.max() < W - 1 and ys.max() < H - 1, (W, H))

    def test_menu_keys_choose_the_resolution_and_keep_the_intensity(self):
        menu = settings_ui.Menu({**PLAN, 'setting_level': 'vivid'})
        self.assertEqual(menu.state(), 0)
        for name in ('Left', 'Right'):                          # the intensity is the gallery's, not the menu's
            self.assertIsNone(menu.key(name))
        self.assertIsNone(menu.key('Down'))
        self.assertEqual(menu.key('Return'), ('save', {'profile': 'big', 'level': 'vivid'}))
        self.assertIsNone(menu.key('Up'))
        self.assertIsNone(menu.key('Up'))                       # wraps to the last row
        self.assertEqual(menu.key('KP_Enter'), ('save', {'profile': 'small', 'level': 'vivid'}))
        for name in ('Escape', 's'):
            self.assertEqual(settings_ui.Menu(PLAN).key(name), ('cancel', None))

    def test_progress_stays_in_its_box(self):
        for info in (dict(phase='download', done=0, total=22_000_000, label='21:9 · 5120 × 2160', level='vivid'),
                     dict(phase='download', done=22_000_000, total=22_000_000, label='16:9 · 2560 × 1440'),
                     dict(phase='install', done=1, total=1, label='32:9 · 5120 × 1440', level='muted')):
            for u in (0.7, 1.0, 2.0):
                W, H = (round(v*u) for v in settings_ui.PROGRESS_SIZE)
                surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W + 2, H + 2)
                cr = cairo.Context(surface)
                cr.translate(1, 1)
                for t in (0.0, 0.37):
                    settings_ui.draw_progress(cr, u, t, info)
                alpha = np.ndarray((H + 2, W + 2, 4), np.uint8, surface.get_data())[..., 3]
                self.assertEqual(int(alpha[0].max()) + int(alpha[-1].max()) + int(alpha[:, 0].max())
                                 + int(alpha[:, -1].max()), 0, (info['phase'], u))


if __name__ == '__main__':
    unittest.main()
