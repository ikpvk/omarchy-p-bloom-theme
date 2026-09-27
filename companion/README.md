# p(bloom) Wallpapers — companion app

Automatic desktop wallpaper resolution, with an optional fullscreen gallery.
The theme installed through Omarchy's menu is data only: it cannot install or
launch this app by itself. Explicitly run the companion installer once:

```sh
omarchy pkg add imv              # only if missing
python3 companion/install.py
```

The installer announces what it installs, adds **p(bloom) Wallpapers** to the
application menu, and opens it automatically in a graphical session. Use
`--no-launch` to install without opening it. A user service keeps desktop renders matched to your monitors. No sudo or
compositor configuration changes are involved.

## Automatic setup

The desktop service automatically selects and applies the optimal wallpaper
set on installation, login and monitor changes, without opening the gallery.
It checks for changes every 10 seconds. Opening the app also opens the gallery. There is no first-run dialog. Selection considers all connected
monitors: avoid enlargement, minimize cropping, then prefer smaller files.

A short notification appears on the first selection or when the chosen set
changes. It states the resolution; clicking it opens settings. Notifications confirm desktop updates only. With another theme active,
the service waits for p(bloom) and leaves that theme unchanged.
Unchanged launches do not repeat the notification.

Settings are available through **Wallpaper settings** in the application's
context menu, or `p-bloom-wallpapers --configure`. This optional TUI offers
**Automatic · Optimal set** and the installed resolutions. A manual override
is remembered; selecting Automatic restores monitor-based selection.
Escape cancels without changing anything. The settings window uses a large
font in Foot, without modifying terminal configuration.

`--show-plan` provides detailed read-only diagnostics. Earlier setup policies
migrate to automatic selection. No monitor detection means no desktop change;
the desktop service keeps watching until real monitors are available.

## Wallpaper sets

Every sheet is composed separately for each common landscape screen, not just
scaled: 16:9, 16:10, 3:2, 4:3, both 21:9 families (64:27 and 43:18/12:5) and
32:9, from 1080p-class to 5K/8K-class (the list and per-set sizes are in
`docs/collection/profiles.json`). Type on every set is at least 11 native
pixels (14 px on 5K 16:9); smaller screens show fewer secondary panels instead
of smaller type.

The theme itself ships one set in `backgrounds/`: the accepted 16:9
5120 × 2880 masters, so it works right after `omarchy theme install` and
only ever downscales on 16:9 screens. Shipped files are WebP quality 90
(the render pipeline keeps and audits lossless originals), which keeps the
theme checkout and every download small. The companion downloads the set
that best matches your monitors from the GitHub Release named in
`tools/wallpaper_profiles.py` (`RELEASE_TAG`), one archive per set:
`https://github.com/ncr/omarchy-p-bloom-theme/releases/download/<tag>/p-bloom-<set>.tar`.
Only the Python standard library is used. The archive's SHA-256 must match the
manifest before anything is unpacked, and every image is checked again; only
the 42 named files are extracted. Sets are stored in
`$XDG_DATA_HOME/p-bloom-wallpapers/sets/` (default `~/.local/share/`); the
three most recently used are kept, so docking back and forth does not
download again.

Offline, or if a download or a checksum fails, the desktop keeps the installed
set (normally the bundled one) and the companion retries after 15 minutes.
With no monitors detected nothing is downloaded. `--list` never downloads.

Selection is unchanged: all connected monitors are considered, enlargement is
avoided on every one of them, then cropping is minimised, then the smaller
download wins. A set counts as a download in the settings list until it is
installed.

Hyprland's synthetic FALLBACK output is not treated as a physical monitor.
Without monitor detection, the app can browse the default but leaves the
desktop unchanged and retries setup when detection works.

If p(bloom) is active, the app copies the chosen set into Omarchy's staged
backgrounds while preserving custom files and the currently selected sheet.
A user-local `theme-set` hook repeats this selection when p(bloom) is reapplied,
including after an update. The hook can initialize the desktop directly; no prior gallery launch is needed.
Other themes are never activated or modified. The background service tracks monitor changes even when the gallery is closed.

Omarchy currently displays one shared wallpaper on all monitors. Selection
considers the whole monitor arrangement, not a separate profile per output. Other aspect
ratios may crop on the desktop; the viewer always fits the complete sheet.

## Controls

| Key | Action |
|---|---|
| Left / Right | Previous / next, wrapping |
| Esc / Q | Close |
| F | Toggle fullscreen |
| I | Show filename and position |
| Home / End | First / last |

The local Super+O integration recognizes the unchanged `p-bloom-wallpapers`
window class. This app does not install a global keybinding.

```sh
p-bloom-wallpapers truth-lamp
p-bloom-wallpapers 3                  # Collection position, not filename number
p-bloom-wallpapers --configure        # Change resolution settings
p-bloom-wallpapers --show-plan        # JSON; no changes or setup dialog
p-bloom-wallpapers --list             # All 42 chosen files; read-only
p-bloom-wallpapers --monitor DP-1     # Prefer its proportions; still avoid upscaling on all screens
p-bloom-wallpapers --dir /path/to/numbered-images
python3 companion/install.py --uninstall
```

Installation is user-local: `~/.local/bin/p-bloom-wallpapers`,
`~/.local/share/p-bloom-wallpapers/`, the application-menu entry and
`~/.config/omarchy/hooks/theme-set.d/p-bloom-wallpapers`. The `p-bloom-wallpapers-desktop.service` user service also runs locally.
Preferences
live under `$XDG_STATE_HOME/p-bloom-wallpapers/setup.json` (default
`~/.local/state/`). Omarchy's own staged files follow its fixed state path.

Keep the checkout in place: the bundled set and the manifest are read from
it. Rerun the installer after moving it or updating app code. New sets are
rendered with `tools/render_wallpaper_sets.py` and packaged with
`tools/package_wallpaper_profiles.py`, which refreshes the verified hashes;
the archives must then be uploaded to the release named by `RELEASE_TAG`. Development viewers `./wallpapers` and `./century` continue to read
live renders independently of the packaged release.

Uninstall stops and removes the desktop service, launcher, owned hook and runtime files. It retains the
theme, downloaded sets and setup preferences (delete
`~/.local/share/p-bloom-wallpapers/sets/` to reclaim the space). A custom `--prefix /some/path`
is a staging installation: it installs no hooks or service and launches nothing.
