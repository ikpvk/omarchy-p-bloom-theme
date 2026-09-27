#!/usr/bin/env python3
"""Package rendered wallpaper sets as release archives and write the manifest.

    python3 tools/render_wallpaper_sets.py            # renders dist/wallpaper-sets/<profile>/
    python3 tools/package_wallpaper_profiles.py       # archives + docs/collection/profiles.json

Rendering keeps lossless, audited intermediates in dist/wallpaper-sets/. The
shipped files are re-encoded as lossy WebP (quality 90, method 6; owner's
decision for fast installs: text and thin lines are unchanged at close zoom,
only the finest grain is smoother) into dist/wallpaper-release/<profile>/.
Every profile becomes one uncompressed tar named p-bloom-<profile>.tar, with a
.sha256 file, in dist/wallpaper-release/. These are
GitHub Release assets for tools/wallpaper_profiles.RELEASE_TAG; this tool does
not upload anything. The default profile is also copied into backgrounds/, so
the theme works immediately after `omarchy theme install` without the
companion app. Archives are byte-reproducible (sorted, zero mtimes/owners).
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
DEFAULT = '16x9-2880p'
QUALITY = dict(quality=90, method=6)


def encode(task):
    src, dst = task
    from PIL import Image
    tmp = dst.with_name('.'+dst.name+'.tmp')
    with Image.open(src) as im:
        im.convert('RGB').save(tmp, format='WEBP', **QUALITY)
    tmp.replace(dst)
    return dst


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    import aspect_layout as A
    from wallpaper_profiles import RELEASE_TAG, archive_url
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--sets', type=Path, default=ROOT/'dist/wallpaper-sets')
    ap.add_argument('--release', type=Path, default=ROOT/'dist/wallpaper-release')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--default', default=DEFAULT)
    ap.add_argument('--allow-issues', action='store_true', help='package despite audit findings (not for release)')
    args = ap.parse_args()
    cat = json.loads((ROOT/'docs/collection/catalog.json').read_text())
    ids = [e['id'] for e in cat['finalized']]
    names = {e['id']: Path(e['source']).name for e in cat['finalized']}
    rows = [(pid, fam, size, tpl) for pid, fam, size, tpl, _ in A.MATRIX] + \
           [(pid, fam, size, 'native-master') for pid, fam, size in A.MASTERS]
    rows.sort(key=lambda r: (['16:9', '16:10', '3:2', '4:3', '21:9', '32:9'].index(r[1]), r[2][0]*r[2][1]))
    profiles = []
    total = 0
    # Lossy shipping copies, re-encoded only when the lossless source is newer.
    from concurrent.futures import ProcessPoolExecutor
    tasks = []
    for pid, *_ in rows:
        (args.release/pid).mkdir(parents=True, exist_ok=True)
        for i in ids:
            src, dst = args.sets/pid/names[i], args.release/pid/names[i]
            if not dst.is_file() or dst.stat().st_mtime < src.stat().st_mtime:
                tasks.append((src, dst))
    with ProcessPoolExecutor(args.jobs) as pool:
        for n, _ in enumerate(pool.map(encode, tasks), 1):
            if n % 42 == 0:
                print(f'encoded {n}/{len(tasks)}', flush=True)
    for pid, family, size, template in rows:
        folder = args.sets/pid
        audit = json.loads((folder/'audit.json').read_text())
        sheets = {r['id']: r for r in audit['sheets']}
        if [i for i in ids if i in sheets] != ids:
            sys.exit(f'{pid}: incomplete render ({len(sheets)} of {len(ids)})')
        if audit['issues'] and not args.allow_issues:
            sys.exit(f'{pid}: {audit["issues"]} audit findings; see {folder/"audit.json"}')
        files = []
        lossless = 0
        for i in ids:
            if sha(folder/names[i]) != sheets[i]['sha256']:
                sys.exit(f'{pid}/{names[i]}: changed since its audit')
            lossless += (folder/names[i]).stat().st_size
            path = args.release/pid/names[i]
            files.append(dict(id=i, name=path.name, sha256=sha(path), bytes=path.stat().st_size))
        archive = args.release/f'p-bloom-{pid}.tar'
        with tarfile.open(archive, 'w', format=tarfile.PAX_FORMAT) as tar:
            def add(name, data=None, path=None):
                info = tarfile.TarInfo(name)
                info.mtime = 0
                info.uid = info.gid = 0
                info.uname = info.gname = ''
                if path is None:
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    tar.addfile(info)
                else:
                    info.mode = 0o644
                    info.size = path.stat().st_size
                    with open(path, 'rb') as f:
                        tar.addfile(info, f)
            add(pid)
            for f in files:
                add(f'{pid}/{f["name"]}', path=args.release/pid/f['name'])
        digest = sha(archive)
        (archive.parent/(archive.name+'.sha256')).write_text(f'{digest}  {archive.name}\n')
        size_bytes = archive.stat().st_size
        total += size_bytes
        profiles.append(dict(
            id=pid, label=f'{family} · {size[0]} × {size[1]}', aspect=family, size=list(size),
            layout=template, floor_px=A.floor_px(*size) if template != 'native-master' else 14.0,
            min_text_px=audit['min_text_px'], bundled=pid == args.default,
            archive=dict(name=archive.name, bytes=size_bytes, sha256=digest),
            files=files))
        print(f'{pid:13} {size[0]:>5}×{size[1]:<5} {size_bytes/1e6:7.1f} MB (lossless {lossless/1e6:6.1f} MB)'
              f'  min text {audit["min_text_px"]:.1f} px  {digest[:12]}')
    default = next(p for p in profiles if p['id'] == args.default)
    # backgrounds/ holds exactly the default set.
    out = ROOT/'backgrounds'
    out.mkdir(exist_ok=True)
    wanted = {f['name'] for f in default['files']}
    for old in out.glob('*.webp'):
        if old.name not in wanted:
            sys.exit(f'Unexpected file in backgrounds/: {old.name}; resolve explicitly')
    for f in default['files']:
        dst = out/f['name']
        if not dst.is_file() or sha(dst) != f['sha256']:
            shutil.copyfile(args.release/default['id']/f['name'], dst)
    manifest = dict(
        version=2, count=len(ids), default=args.default,
        release=dict(note='Archives are GitHub Release assets of the tag named in '
                          'tools/wallpaper_profiles.py (RELEASE_TAG); the URL pattern is '
                          + archive_url('<archive>').replace(RELEASE_TAG, '<tag>')),
        readability=dict(rule='floor_px = max(11, 14 * height / 2880)',
                         note='Smallest type on the native file after every transform. Lower resolutions '
                              'are composed more compactly and drop secondary blocks; type is never shrunk.'),
        encoding=dict(format='webp', lossless=False, **QUALITY,
                      note='Lossless intermediates are audited; shipped files are re-encoded.'),
        profiles=profiles)
    (ROOT/'docs/collection/profiles.json').write_text(json.dumps(manifest, indent=1)+'\n')
    print(f'{len(profiles)} profiles, archives {total/1e9:.2f} GB total; default {args.default} copied to backgrounds/')


if __name__ == '__main__':
    main()
