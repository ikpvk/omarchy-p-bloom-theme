#!/usr/bin/env python3
"""Full-screen development gallery, using imv's native live image reload."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

ROOT = Path(os.environ.get('PBLOOM_THEME_ROOT', Path(__file__).resolve().parents[1])).resolve()
DEVELOPMENT = ROOT / 'concepts/development'
EXTENSIONS = {'.webp', '.png', '.jpg', '.jpeg'}


def collection(directory):
    """Only numbered wallpaper masters (01-, 001-, b01-), never crops or thumbnails."""
    return sorted(p for p in directory.iterdir()
                  if p.is_file() and p.suffix.lower() in EXTENSIONS
                  and re.match(r'^(\d{2,3}|b\d{2})-', p.name))


def finalized_collection():
    """Use the retained registry; a clean checkout shows the complete shipped set.

    The generated ranking gallery is optional and is not a runtime dependency.
    Rejected Century studies are never discovered by scanning render folders.
    """
    registry = ROOT / 'docs/collection/catalog.json'
    if not registry.exists():
        return collection(ROOT / 'backgrounds')
    files = []
    for entry in json.loads(registry.read_text())['finalized']:
        source = (ROOT / entry['source']).resolve()
        if not source.is_relative_to(ROOT):
            raise ValueError('Collection source must be inside the theme checkout')
        if not source.is_file():
            source = ROOT / 'backgrounds' / source.name
        if source.is_file():
            files.append(source)
    return files


def select(files, query):
    if query is None:
        return files[0]
    if query.isdecimal():
        matches = [p for p in files if p.name.split('-')[0].isdecimal() and int(p.name.split('-')[0]) == int(query)]
    else:
        matches = [p for p in files if query.casefold() in p.name.casefold()]
    if len(matches) != 1:
        raise ValueError(f'Expected one wallpaper for {query!r}; found {len(matches)}. Use --list.')
    return matches[0]


def display_name(path):
    """09-tether-climber.webp -> Tether Climber"""
    stem = Path(path).stem
    return stem.split('-', 1)[-1].replace('-', ' ').title()


def notify(title, body=''):
    sender = shutil.which('omarchy-notification-send') or shutil.which('notify-send')
    if sender:
        # a short confirmation: without -t Omarchy keeps a notification until it is dismissed
        args = ([sender, '--app-name', 'p(bloom) Wallpapers', '-t', '4000', title, body] if 'omarchy' in sender
                else [sender, '-t', '4000', title, body])
        subprocess.run(args, check=False, capture_output=True, timeout=5)


def set_desktop(path):
    """Show one wallpaper on the desktop, from p(bloom)'s staged backgrounds (so Omarchy's next-background keeps working)."""
    import wallpaper_profiles as wp
    current = wp.current_dir()
    if not wp.active_theme(current):
        notify('p(bloom) is not the active theme', 'Choose p(bloom) in Omarchy\'s theme menu, then press Enter again.')
        return
    target = current/'theme/backgrounds'/Path(path).name
    if not target.is_file():
        notify('This wallpaper is not on the desktop set yet', 'Its set is still downloading; try again in a moment.')
        return
    wp.refresh_desktop(target, current)
    notify(f'Desktop wallpaper: {display_name(path)}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('start', nargs='?', help='Wallpaper number or name, e.g. 9 or tether')
    ap.add_argument('--collection', choices=['development', 'finalized'], default='development',
                    help='Finalized reads the retained collection, with shipped backgrounds as fallback')
    ap.add_argument('--dir', type=Path, help='View a different render directory')
    ap.add_argument('--render', action='store_true', help='Regenerate the development set before opening')
    ap.add_argument('--list', action='store_true', help='List the selected collection and exit')
    ap.add_argument('--configure', action='store_true', help='Change wallpaper settings: background level and resolution')
    ap.add_argument('--monitor', help="Prefer this monitor's proportions; assess resolution on all monitors")
    ap.add_argument('--show-plan', action='store_true', help='Print automatic setup as JSON without changing anything')
    ap.add_argument('--sync-backgrounds', action='store_true', help='Automatically match the p(bloom) desktop to connected monitors without opening the viewer')
    ap.add_argument('--set-desktop', type=Path, metavar='FILE', help='Make this wallpaper the desktop background (the gallery\'s Enter key)')
    ap.add_argument('--replace', metavar='PID', help='With --configure: after saving, close this gallery and reopen it on the new set')
    args = ap.parse_args()
    if args.set_desktop:
        set_desktop(args.set_desktop)
        return
    directory = args.dir.expanduser().resolve() if args.dir else DEVELOPMENT
    if args.render and args.collection == 'finalized':
        ap.error('Render sources separately; --render only supports the development collection')
    if args.render:
        subprocess.run([sys.executable, str(ROOT/'tools/make_wallpapers.py'),
                        '--out', str(directory)], check=True)
    # A fresh checkout can still browse the shipped set without rendering.
    if args.dir is None and not directory.is_dir():
        directory = ROOT / 'backgrounds'
    try:
        retained = args.collection == 'finalized' and args.dir is None
        profile_plan = None
        if retained and (ROOT/'docs/collection/profiles.json').is_file():
            import wallpaper_profiles as wp
            previous = wp.read_setup()
            requested = previous.get('profile','auto') if previous.get('version')==6 and previous.get('root')==str(ROOT) else 'auto'
            level = wp.saved_level(previous, ROOT)
            if requested != 'auto':
                _, available = wp.profiles(ROOT)
                if requested not in {p['id'] for p in available}:
                    requested = 'auto'
            monitor = args.monitor or previous.get('monitor')
            detected = wp.monitors()
            # A remembered external screen may be unplugged; explicit CLI typos
            # remain errors, but normal launches fall back to a connected screen.
            if monitor and not args.monitor and monitor not in {m['name'] for m in detected}:
                monitor = None
            # --list is read-only: it shows installed files and downloads nothing.
            profile_plan = wp.plan(ROOT, requested, monitor, detected, local_only=args.list, level=level)
            if args.show_plan:
                print(json.dumps(profile_plan, indent=2))
                return
            if args.sync_backgrounds:
                wp.initialize(ROOT, profile_plan, requested, monitor)
                return
            files = [Path(p) for p in profile_plan['files']]
        else:
            if args.configure or args.monitor or args.show_plan or args.sync_backgrounds:
                ap.error('Monitor profiles require the packaged finalized collection')
            files = finalized_collection() if retained else collection(directory)
        if not files:
            raise ValueError(f'No numbered wallpapers in {directory}')
        if retained and args.start and args.start.isdecimal():
            index = int(args.start) - 1
            if not 0 <= index < len(files):
                raise ValueError(f'Wallpaper position must be between 1 and {len(files)}')
            first = files[index]
        else:
            first = select(files, args.start)
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
    if args.list:
        if profile_plan:
            # Status on stderr; stdout stays one path per line.
            shown = wp.LEVEL_LABELS[profile_plan.get('level', 'default')]
            wanted = wp.LEVEL_LABELS[profile_plan.get('requested_level', 'default')]
            note = '' if shown == wanted else f' ({wanted} not installed yet)'
            print(f"p(bloom): {profile_plan['label']}, {shown} background{note}, "
                  f"{'automatic' if requested == 'auto' else 'manual'} resolution", file=sys.stderr)
        print('\n'.join(str(p) for p in files))
        return
    viewer = shutil.which('imv')
    if not viewer:
        ap.error('imv is required. On Omarchy: omarchy pkg add imv')
    if profile_plan:
        try:
            chosen_plan = wp.initialize(ROOT, profile_plan, requested, monitor, args.configure)
            if not chosen_plan:
                return
            if args.replace:
                # settings opened from a gallery: that gallery shows the old set, so it gives way to this one
                subprocess.run(['imv-msg', args.replace, 'quit'], check=False, capture_output=True)
            # Preserve the selected sheet when an optimal format changes.
            files = [Path(p) for p in chosen_plan['files']]
            first = next(p for p in files if p.name == first.name)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            ap.error(str(exc))
    env = os.environ.copy()
    env['imv_config'] = str(Path(__file__).with_name('wallpaper-viewer.ini'))
    # the gallery's Enter and S keys call this program again
    env['PBLOOM_SELF'] = f'{shlex.quote(sys.executable)} {shlex.quote(str(Path(__file__).resolve()))} --collection finalized'
    env['PBLOOM_KEYS'] = '          ← →  browse      Enter  set as desktop      S  settings      I  hide this bar      Esc  close'
    os.execve(viewer, [viewer, '-f', '-s', 'full', '-b', '000000',
                      '-i', 'p-bloom-wallpapers', '-n', str(first),
                      *map(str, files)], env)


if __name__ == '__main__':
    main()
