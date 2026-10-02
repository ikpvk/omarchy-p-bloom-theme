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
    def test_rows_name_the_optimal_installed_and_downloads(self):
        self.assertEqual(settings_ui.rows(PLAN, 'default'),
                         [('auto', 'AUTOMATIC', None, None), ('big', '3840 × 2160', '280.0 MB', 'OPTIMAL'),
                          ('small', '1920 × 1080', '80.0 MB', 'INSTALLED')])
        self.assertEqual(settings_ui.optimal_size(PLAN, 'default'), '3840 × 2160')

    def test_the_panel_fits_every_screen(self):
        many = {**PLAN, 'options': [dict(profile=f'p{i}', size=[1920 + i, 1080], total_bytes=1, local=False)
                                    for i in range(40)]}
        for plan in (PLAN, many):
            for W, H in ((1920, 1080), (5120, 2160), (1080, 1920), (1280, 720), (1024, 768)):
                surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
                settings_ui.draw_settings(cairo.Context(surface), W, H, plan, 'vivid', len(plan['options']))
                alpha = np.ndarray((H, W, 4), np.uint8, surface.get_data())[..., 3]
                ys, xs = np.nonzero(alpha > 230)              # the panel, not the dimmed screen around it
                self.assertTrue(xs.min() > 0 and ys.min() > 0 and xs.max() < W - 1 and ys.max() < H - 1, (W, H))

    def test_menu_keys(self):
        menu = settings_ui.Menu(PLAN)
        self.assertEqual(menu.state(), ('default', 0))
        self.assertIsNone(menu.key('Right'))
        self.assertIsNone(menu.key('Down'))
        self.assertEqual(menu.key('Return'), ('save', {'profile': 'big', 'level': 'vivid'}))
        self.assertIsNone(menu.key('Up'))
        self.assertIsNone(menu.key('Up'))                       # wraps to the last row
        self.assertEqual(menu.key('KP_Enter'), ('save', {'profile': 'small', 'level': 'vivid'}))
        for name in ('Escape', 's'):
            self.assertEqual(settings_ui.Menu(PLAN).key(name), ('cancel', None))


if __name__ == '__main__':
    unittest.main()
