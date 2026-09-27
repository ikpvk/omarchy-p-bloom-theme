"""Release sets: download verification, offline fallback, real-matrix selection."""
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
    """entries: [(name, bytes or None for a directory)]"""
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


class Download(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for p in (patch.dict(wp.os.environ, {'XDG_DATA_HOME': str(self.root/'data')}),
                  patch.object(wp, 'setup_path', return_value=self.root/'state/setup.json'),
                  patch.object(wp, 'notify_selection')):
            p.start()
            self.addCleanup(p.stop)
        docs = self.root/'docs/collection'
        docs.mkdir(parents=True)
        (docs/'catalog.json').write_text(json.dumps({'finalized': [{'id': 'one'}, {'id': 'two'}]}))
        (self.root/'backgrounds').mkdir()
        self.images = {'one.webp': b'4k-one', 'two.webp': b'4k-two'}
        bundled = []
        for key in ('one', 'two'):
            data = f'1440-{key}'.encode()
            (self.root/'backgrounds'/f'{key}.webp').write_bytes(data)
            bundled.append(dict(id=key, name=f'{key}.webp', sha256=sha(data), bytes=len(data)))
        self.archive = tar_bytes([('4k', None)] + [(f'4k/{n}', d) for n, d in self.images.items()])
        self.manifest = {'default': '1440', 'profiles': [
            dict(id='1440', label='16:9 · 2560 × 1440', size=[2560, 1440], min_text_px=11, bundled=True,
                 archive=dict(name='p-bloom-1440.tar', bytes=1, sha256='0'*64), files=bundled),
            dict(id='4k', label='16:9 · 3840 × 2160', size=[3840, 2160], min_text_px=11,
                 archive=dict(name='p-bloom-4k.tar', bytes=len(self.archive), sha256=sha(self.archive)),
                 files=[dict(id=n.split('.')[0], name=n, sha256=sha(d), bytes=len(d)) for n, d in self.images.items()]),
        ]}
        self.save()
        self.urls = []

    def save(self):
        (self.root/'docs/collection/profiles.json').write_text(json.dumps(self.manifest))

    def opener(self, payload):
        def open_(request, timeout):
            self.urls.append(request.full_url)
            return Response(payload)
        return open_

    def test_url_uses_the_single_release_tag(self):
        self.assertEqual(wp.archive_url('p-bloom-4k.tar'),
                         f'https://github.com/ncr/omarchy-p-bloom-theme/releases/download/{wp.RELEASE_TAG}/p-bloom-4k.tar')

    def test_verified_download_installs_the_set(self):
        target = wp.fetch(self.root, '4k', opener=self.opener(self.archive))
        self.assertEqual(self.urls, [wp.archive_url('p-bloom-4k.tar')])
        self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, self.images)
        screen = dict(name='DP-1', width=3840, height=2160, scale=1)
        p = wp.plan(self.root, detected=[screen])
        self.assertEqual((p['profile'], p['local']), ('4k', True))
        self.assertEqual([Path(f).parent for f in p['files']], [target, target])
        self.assertEqual([p.name for p in wp.sets_dir().iterdir()], ['4k'])  # no temporary leftovers

    def test_archive_checksum_mismatch_installs_nothing(self):
        bad = self.archive[:-1] + b'x'
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            wp.fetch(self.root, '4k', opener=self.opener(bad))
        self.assertFalse((wp.sets_dir()/'4k').exists())

    def test_oversized_download_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'larger'):
            wp.fetch(self.root, '4k', opener=self.opener(self.archive + b'\0'*4096))

    def test_tampered_image_in_matching_archive_is_refused(self):
        tampered = tar_bytes([('4k/one.webp', b'evil'), ('4k/two.webp', self.images['two.webp'])])
        self.manifest['profiles'][1]['archive'].update(bytes=len(tampered), sha256=sha(tampered))
        self.save()
        with self.assertRaisesRegex(ValueError, 'one.webp failed'):
            wp.fetch(self.root, '4k', opener=self.opener(tampered))
        self.assertFalse((wp.sets_dir()/'4k').exists())

    def test_path_traversal_and_unknown_entries_are_refused(self):
        for name in ('../escape.webp', '4k/../../escape.webp', 'other/one.webp', '4k/extra.webp'):
            evil = tar_bytes([(name, b'x')])
            self.manifest['profiles'][1]['archive'].update(bytes=len(evil), sha256=sha(evil))
            self.save()
            with self.assertRaisesRegex(ValueError, 'Unexpected entry'):
                wp.fetch(self.root, '4k', opener=self.opener(evil))
        self.assertFalse((self.root/'escape.webp').exists())
        self.assertFalse((wp.sets_dir()/'4k').exists())

    def test_offline_keeps_the_bundled_set_and_backs_off(self):
        screen = dict(name='DP-1', width=3840, height=2160, scale=1)
        with patch.object(wp, 'fetch', side_effect=OSError('network is unreachable')) as fetch, \
             patch.object(wp, 'sync', return_value=False):
            p = wp.initialize(self.root, wp.plan(self.root, detected=[screen]))
            self.assertEqual((p['profile'], p['fallback']), ('1440', '4k'))
            self.assertIn('could not be downloaded', p['warnings'][0])
            self.assertIn('4k', wp.read_setup()['failed'])
            # Within the retry window the watcher does not try again.
            p = wp.initialize(self.root, wp.plan(self.root, detected=[screen]))
            self.assertEqual(p['profile'], '1440')
            self.assertEqual(fetch.call_count, 1)
            with patch.object(wp.time, 'time', return_value=wp.time.time()+wp.RETRY_SECONDS+1):
                wp.initialize(self.root, wp.plan(self.root, detected=[screen]))
            self.assertEqual(fetch.call_count, 2)

    def test_successful_download_is_used_for_the_desktop(self):
        screen = dict(name='DP-1', width=3840, height=2160, scale=1)
        real = wp.fetch
        with patch.object(wp, 'fetch', side_effect=lambda root, pid: real(root, pid, opener=self.opener(self.archive))), \
             patch.object(wp, 'sync', return_value=False) as sync:
            p = wp.initialize(self.root, wp.plan(self.root, detected=[screen]))
        self.assertEqual((p['profile'], p['local']), ('4k', True))
        self.assertEqual(sync.call_args.args[0]['profile'], '4k')
        self.assertNotIn('4k', wp.read_setup().get('failed', {}))

    def test_no_monitor_never_downloads(self):
        with patch.object(wp, 'fetch') as fetch, patch.object(wp, 'sync', return_value=False):
            p = wp.initialize(self.root, wp.plan(self.root, detected=[]))
        fetch.assert_not_called()
        self.assertEqual(p['profile'], '1440')

    def test_prune_keeps_recent_sets(self):
        for i, name in enumerate(('a', 'b', 'c', 'd')):
            (wp.sets_dir()/name).mkdir(parents=True)
            wp.os.utime(wp.sets_dir()/name, (1000+i, 1000+i))
        wp.prune('a')
        self.assertEqual(sorted(p.name for p in wp.sets_dir().iterdir()), ['a', 'c', 'd'])


class PublishedMatrix(unittest.TestCase):
    """Selection over the real manifest, using its declared (not downloaded) sizes."""

    def setUp(self):
        self.manifest = json.loads((ROOT/'docs/collection/profiles.json').read_text())
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        p = patch.dict(wp.os.environ, {'XDG_DATA_HOME': temp.name})
        p.start()
        self.addCleanup(p.stop)

    def choose(self, *screens):
        rows = [dict(name=f'M{i}', width=w, height=h, scale=1) for i, (w, h) in enumerate(screens)]
        return wp.plan(ROOT, detected=rows)

    def test_manifest_is_complete_and_bundles_one_default(self):
        self.assertEqual(self.manifest['version'], 2)
        bundled = [p for p in self.manifest['profiles'] if p.get('bundled')]
        self.assertEqual([p['id'] for p in bundled], [self.manifest['default']])
        for p in self.manifest['profiles']:
            self.assertEqual(len(p['files']), self.manifest['count'])
            self.assertRegex(p['archive']['name'], r'^p-bloom-[0-9a-z-]+\.tar$')
            self.assertRegex(p['archive']['sha256'], r'^[0-9a-f]{64}$')
            self.assertGreaterEqual(p['min_text_px'], 11)
        for f in bundled[0]['files']:
            self.assertEqual(sha((ROOT/'backgrounds'/f['name']).read_bytes()), f['sha256'])

    def test_every_common_screen_gets_its_own_set(self):
        expected = {
            (1920, 1080): '16x9-1080p', (2560, 1440): '16x9-1440p', (3840, 2160): '16x9-2160p',
            (5120, 2880): '16x9-2880p', (1366, 768): '16x9-1080p',
            (1920, 1200): '16x10-1200p', (2560, 1600): '16x10-1600p', (3840, 2400): '16x10-2400p',
            (2880, 1800): '16x10-2400p',
            (2256, 1504): '3x2-1504p', (2880, 1920): '3x2-1920p', (3000, 2000): '16x10-2400p',
            (1600, 1200): '4x3-1200p', (2048, 1536): '4x3-1536p', (1280, 1024): '4x3-1200p',
            (2560, 1080): '64x27-1080p', (5120, 2160): '64x27-2160p',
            (3440, 1440): '43x18-1440p', (3840, 1600): '12x5-1600p',
            (3840, 1080): '32x9-1080p', (5120, 1440): '32x9-1440p', (7680, 2160): '32x9-2160p',
        }
        for screen, profile in expected.items():
            with self.subTest(screen=screen):
                p = self.choose(screen)
                self.assertEqual(p['profile'], profile)
                self.assertFalse(next(o for o in p['options'] if o['profile'] == profile)['upscale'])

    def test_mixed_monitors_avoid_upscaling_everywhere(self):
        p = self.choose((2880, 1920), (3840, 2160))
        chosen = next(o for o in p['options'] if o['profile'] == p['profile'])
        self.assertFalse(chosen['upscale'])
        self.assertEqual(p['profile'], '16x10-2400p')
        p = self.choose((1920, 1080), (2560, 1440))
        self.assertEqual(p['profile'], '16x9-1440p')


if __name__ == '__main__':
    unittest.main()
