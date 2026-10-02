"""Background levels (Muted / Default / Vivid): manifest, selection, download, fallback."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
import wallpaper_profiles as wp


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tar_bytes(entries):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w') as tar:
        for name, data in entries:
            info = tarfile.TarInfo(name)
            if data is None:
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
            else:
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


SCREEN = dict(name='DP-1', width=3840, height=2160, scale=1)


class Levels(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.real_notify = wp.notify_selection
        for p in (patch.dict(wp.os.environ, {'XDG_DATA_HOME': str(self.root/'data')}),
                  patch.object(wp, 'setup_path', return_value=self.root/'state/setup.json'),
                  patch.object(wp, 'notify_selection')):
            p.start()
            self.addCleanup(p.stop)
        docs = self.root/'docs/collection'
        docs.mkdir(parents=True)
        (docs/'catalog.json').write_text(json.dumps({'finalized': [{'id': 'one'}, {'id': 'two'}]}))
        (self.root/'backgrounds').mkdir()
        bundled = []
        for key in ('one', 'two'):
            data = f'1440-{key}'.encode()
            (self.root/'backgrounds'/f'{key}.webp').write_bytes(data)
            bundled.append(dict(id=key, name=f'{key}.webp', sha256=sha(data), bytes=len(data)))
        self.archives = {}
        files = {}
        for level in ('default', 'muted', 'vivid'):
            folder = wp.set_name('4k', level)
            images = {f'{k}.webp': f'4k-{level}-{k}'.encode() for k in ('one', 'two')}
            self.archives[level] = (tar_bytes([(folder, None)] + [(f'{folder}/{n}', d) for n, d in images.items()]), images)
            files[level] = [dict(id=n.split('.')[0], name=n, sha256=sha(d), bytes=len(d)) for n, d in images.items()]

        def archive(level):
            data = self.archives[level][0]
            return dict(name=f'p-bloom-{wp.set_name("4k", level)}.tar', bytes=len(data), sha256=sha(data))
        self.manifest = {'default': '1440', 'profiles': [
            dict(id='1440', label='16:9 · 2560 × 1440', size=[2560, 1440], min_text_px=11, bundled=True, files=bundled),
            dict(id='4k', label='16:9 · 3840 × 2160', size=[3840, 2160], min_text_px=11,
                 archive=archive('default'), files=files['default'],
                 levels={level: dict(archive=archive(level), files=files[level], min_text_px=11)
                         for level in ('muted', 'vivid')}),
        ]}
        self.save()
        self.urls = []

    def save(self):
        (self.root/'docs/collection/profiles.json').write_text(json.dumps(self.manifest))

    def opener(self, level):
        def open_(request, timeout):
            self.urls.append(request.full_url)
            return Response(self.archives[level][0])
        return open_

    def fake_fetch(self, fail=()):
        """fetch() with the test archives; levels in `fail` behave like a 404."""
        real = wp.fetch

        def fetch(root, pid, level='default'):
            if level in fail:
                raise OSError('HTTP Error 404: Not Found')
            return real(root, pid, opener=self.opener(level), level=level)
        return fetch

    # -- manifest ------------------------------------------------------------

    def test_manifest_levels_resolve_to_their_own_archive_and_folder(self):
        _, every = wp.profiles(self.root, 'vivid')
        four = next(p for p in every if p['id'] == '4k')
        self.assertEqual((four['level'], four['level_missing'], four['local']), ('vivid', False, False))
        self.assertEqual(four['archive']['name'], 'p-bloom-4k-vivid.tar')
        self.assertEqual({p.parent for p in four['paths']}, {wp.sets_dir()/'4k-vivid'})
        self.assertNotIn('levels', four)
        # The bundled set publishes no Vivid archive: offered at Default, marked.
        bundled = next(p for p in every if p['id'] == '1440')
        self.assertEqual((bundled['level'], bundled['level_missing'], bundled['local']), ('default', True, True))

    def test_unknown_level_means_default_and_broken_level_entry_is_refused(self):
        _, every = wp.profiles(self.root, 'neon')
        self.assertTrue(all(p['level'] == 'default' for p in every))
        self.manifest['profiles'][1]['levels']['muted'] = {'files': []}
        self.save()
        with self.assertRaisesRegex(ValueError, 'Invalid muted set'):
            wp.profiles(self.root, 'muted')

    def test_level_does_not_change_the_resolution_choice(self):
        for level in wp.LEVELS:
            p = wp.plan(self.root, detected=[SCREEN], level=level)
            self.assertEqual((p['profile'], p['level'], p['set']), ('4k', level, wp.set_name('4k', level)))
            self.assertEqual(p['warnings'], [])

    # -- download ------------------------------------------------------------

    def test_level_archive_downloads_into_its_own_set(self):
        target = wp.fetch(self.root, '4k', opener=self.opener('muted'), level='muted')
        self.assertEqual(target, wp.sets_dir()/'4k-muted')
        self.assertEqual(self.urls, [wp.archive_url('p-bloom-4k-muted.tar')])
        self.assertEqual({p.name: p.read_bytes() for p in target.iterdir() if p.name != wp.MARKER}, self.archives['muted'][1])
        p = wp.plan(self.root, detected=[SCREEN], level='muted')
        self.assertTrue(p['local'])
        # The Default set of the same profile is a different folder, still absent.
        self.assertFalse(wp.plan(self.root, detected=[SCREEN])['local'])

    def test_level_archive_must_contain_its_own_folder(self):
        wrong = tar_bytes([(f'4k/{n}', d) for n, d in self.archives['vivid'][1].items()])
        self.manifest['profiles'][1]['levels']['vivid']['archive'].update(bytes=len(wrong), sha256=sha(wrong))
        self.save()
        with self.assertRaisesRegex(ValueError, 'Unexpected entry'):
            wp.fetch(self.root, '4k', opener=lambda request, timeout: Response(wrong), level='vivid')
        self.assertFalse((wp.sets_dir()/'4k-vivid').exists())

    def test_unpublished_level_cannot_be_fetched(self):
        with self.assertRaisesRegex(ValueError, 'No Muted background'):
            wp.fetch(self.root, '1440', opener=self.opener('muted'), level='muted')

    # -- settings and fallback -----------------------------------------------

    def test_changing_the_level_downloads_that_set_and_is_remembered(self):
        with patch.object(wp, 'fetch', side_effect=self.fake_fetch()), \
             patch.object(wp, 'sync', return_value=True) as sync, \
             patch.object(wp, 'announce', return_value={'profile': 'auto', 'level': 'vivid'}):
            p = wp.initialize(self.root, wp.plan(self.root, detected=[SCREEN]), configure=True)
        self.assertEqual((p['profile'], p['level'], p['local']), ('4k', 'vivid', True))
        self.assertEqual(Path(sync.call_args.args[0]['files'][0]).parent, wp.sets_dir()/'4k-vivid')
        saved = wp.read_setup()
        self.assertEqual((saved['level'], saved['selected_level'], saved['profile']), ('vivid', 'vivid', 'auto'))
        self.assertEqual(wp.saved_level(saved, self.root), 'vivid')
        # Later launches and the desktop watcher keep the level without asking.
        with patch.object(wp, 'fetch', side_effect=AssertionError('already installed')), \
             patch.object(wp, 'sync', return_value=False):
            p = wp.initialize(self.root, wp.plan(self.root, detected=[SCREEN]))
        self.assertEqual(p['level'], 'vivid')

    def test_settings_screen_gets_every_levels_resolution_list(self):
        wp.fetch(self.root, '4k', opener=self.opener('muted'), level='muted')
        seen = {}
        def announce(p, desktop):
            seen.update(p)
            return None
        with patch.object(wp, 'fetch', side_effect=OSError('offline')), patch.object(wp, 'sync', return_value=False), \
             patch.object(wp, 'announce', side_effect=announce):
            wp.initialize(self.root, wp.plan(self.root, detected=[SCREEN]), configure=True)
        local = {lv: {o['profile']: o['local'] for o in opts} for lv, opts in seen['options_by_level'].items()}
        self.assertEqual(local['muted']['4k'], True)
        self.assertEqual(local['vivid']['4k'], False)
        self.assertEqual(set(local), set(wp.LEVELS))

    def test_old_string_setting_keeps_the_current_level(self):
        with patch.object(wp, 'fetch', side_effect=self.fake_fetch()), patch.object(wp, 'sync', return_value=False), \
             patch.object(wp, 'announce', return_value='1440'):
            p = wp.initialize(self.root, wp.plan(self.root, detected=[SCREEN]), configure=True, level='muted')
        # 1440 publishes no Muted set: the bundled Default is used, with a warning.
        self.assertEqual((p['profile'], p['level']), ('1440', 'default'))
        self.assertIn('Muted background is not published', ' '.join(p['warnings']))
        self.assertEqual(wp.read_setup()['level'], 'muted')

    def test_invalid_level_setting_is_refused(self):
        with patch.object(wp, 'fetch', side_effect=self.fake_fetch()), patch.object(wp, 'sync', return_value=False), \
             patch.object(wp, 'announce', return_value={'profile': 'auto', 'level': 'neon'}):
            with self.assertRaisesRegex(ValueError, 'Invalid wallpaper setting'):
                wp.initialize(self.root, wp.plan(self.root, detected=[SCREEN]), configure=True)

    def test_missing_level_archive_keeps_the_current_set_and_retries(self):
        with patch.object(wp, 'fetch', side_effect=self.fake_fetch()), patch.object(wp, 'sync', return_value=False):
            p = wp.initialize(self.root, wp.plan(self.root, detected=[SCREEN]))
        self.assertEqual((p['profile'], p['level']), ('4k', 'default'))
        fetch = self.fake_fetch(fail=('vivid',))
        with patch.object(wp, 'fetch', side_effect=fetch) as calls, patch.object(wp, 'sync', return_value=False) as sync:
            p = wp.initialize(self.root, wp.plan(self.root, detected=[SCREEN]), level='vivid')
            # The 4k Default set already on the desktop stays; nothing else is fetched.
            self.assertEqual((p['profile'], p['level'], p['fallback']), ('4k', 'default', '4k-vivid'))
            self.assertIn('Vivid background, set could not be downloaded', p['warnings'][0])
            self.assertEqual(Path(sync.call_args.args[0]['files'][0]).parent, wp.sets_dir()/'4k')
            self.assertIn('4k-vivid', wp.read_setup()['failed'])
            self.assertEqual(wp.read_setup()['level'], 'vivid')
            wp.initialize(self.root, wp.plan(self.root, detected=[SCREEN]))
            self.assertEqual(calls.call_count, 1)  # within the retry window
            with patch.object(wp.time, 'time', return_value=wp.time.time()+wp.RETRY_SECONDS+1):
                wp.initialize(self.root, wp.plan(self.root, detected=[SCREEN]))
            self.assertEqual(calls.call_count, 2)

    def test_offline_first_choice_falls_back_to_the_bundled_default(self):
        with patch.object(wp, 'fetch', side_effect=OSError('network is unreachable')), \
             patch.object(wp, 'sync', return_value=False):
            p = wp.initialize(self.root, wp.plan(self.root, detected=[SCREEN]), level='muted')
        self.assertEqual((p['profile'], p['level'], p['requested_level']), ('1440', 'default', 'muted'))
        self.assertIn('could not be downloaded', p['warnings'][0])

    def test_notification_names_the_level(self):
        with patch.object(wp.shutil, 'which', side_effect=lambda name: '/usr/bin/'+name), \
             patch.object(wp.subprocess, 'run') as run:
            self.real_notify(dict(size=[3840, 2160], profile='4k', recommended='4k', level='vivid'), True)
        self.assertTrue(any('Vivid background' in x for x in run.call_args.args[0]))

if __name__ == '__main__':
    unittest.main()
