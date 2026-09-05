r"""Build an ODST map from the Editing Kit's tag source, and swap it in or out.

Borrowing raw pages from a donor map is dead: sc150 has no place to put one. All
three placements were rejected in-game (level loads, bounces to the main menu) --
outside the raw region aligned, and inside it unaligned, which are the only two kinds
of free space the file has. Rebuilding is the way to get a weapon's shaders, particles
and sounds in properly, and it should work for weapons with no donor map at all.

    python odst_ek_build.py --build sc150          # tool.exe build-cache-file
    python odst_ek_build.py --install sc150        # swap the built map into the game
    python odst_ek_build.py --restore sc150        # put the previous map back
    python odst_ek_build.py --status sc150

What is known about the toolchain (2026-08-12):
  * `tool.exe build-cache-file <scenario> <platform>` builds ONE map standalone, which
    avoids the full BuildMapsSharedOptimizedPlusSharedSounds.ps1 chain.
  * A vanilla sc150 built this way is 420,700,160 bytes against the shipped
    235,544,576, carries the same 14067 tags, and has an EMPTY `play` tag -- it inlines
    what the shipped map reaches for in shared.map / campaign.map. Whether MCC will
    load such a map is the first thing to establish, before any tag editing.
  * If it will not, the shared-aware verb is
    `build-cache-file-language-version-optimizable-use-sharing`, which still stops
    short of rebuilding the whole campaign.
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_patch as HP                                          # noqa: E402

EK = r"F:\SteamLibrary\steamapps\common\H3ODSTEK"
GAME = (r"C:\Program Files (x86)\Steam\steamapps\common"
        r"\Halo The Master Chief Collection\halo3odst\maps")
SCENARIO = r"levels\atlas\%s\%s"
MAP_SUBDIR = 'halo3odst/maps'


def baseline_root():
    """The enhancer's configured Baselines folder, or '' for the sibling .bak."""
    try:
        with io.open(os.path.join(os.path.dirname(HERE), 'settings.json'),
                     encoding='utf-8') as f:
            return json.load(f).get('baseline_root') or ''
    except Exception:
        return ''


def baseline_of(dst):
    """The patcher's baseline for this map, wherever it is configured to live.

    Resolved through halo_patch so this tool and apply_run can never disagree: with a
    Baselines folder set, writing a sibling `.bak` here would leave the patcher
    reading one file while this wrote another.
    """
    return HP.baseline_path(dst, baseline_root(), MAP_SUBDIR)
# The map that was in place before the first EK install, kept under its own name.
SAVED = '.working'


def build(name, platform='pc', extra=()):
    scen = SCENARIO % (name, name)
    cmd = [os.path.join(EK, 'tool.exe'), 'build-cache-file', scen, platform, *extra]
    print('  %s' % ' '.join(cmd))
    r = subprocess.run(cmd, cwd=EK, capture_output=True, text=True)
    out = (r.stdout or '') + (r.stderr or '')
    if out.strip():
        print(out[-2000:])
    built = os.path.join(EK, 'maps', name + '.map')
    print('  exit %d; %s' % (r.returncode,
                             ('built %d bytes' % os.path.getsize(built))
                             if os.path.exists(built) else 'NO MAP PRODUCED'))
    return r.returncode == 0 and os.path.exists(built)


def status(name):
    live = os.path.join(GAME, name + '.map')
    for label, path in (('game   ', live),
                        ('saved  ', live + SAVED),
                        ('baseline', baseline_of(live)),
                        ('shipped ', live + '.shipped'),
                        ('EK     ', os.path.join(EK, 'maps', name + '.map'))):
        print('  %s %-11s %s' % (label, ('%d bytes' % os.path.getsize(path))
                                 if os.path.exists(path) else '(absent)', path))


def install(name, baseline=True):
    """Install the EK build, and make it the patcher's baseline.

    halo_patch.apply_run patches FROM `<map>.bak` whenever that exists and saves the
    result over `<map>`. sc150's .bak is the shipped 235 MB map, so the first GUI patch
    after installing a rebuild would rebuild from the SHIPPED baseline and overwrite the
    421 MB rebuild -- silently destroying every restored weapon, with no error.

    Rather than teach apply_run about rebuilds, point .bak at the rebuild: it is the
    pristine state now, since nothing in a run should ever undo the rebuild. The
    shipped original is kept as `<map>.map.shipped`, a name apply_run never looks at,
    so nothing is lost and Steam verification is not needed to get it back.
    """
    dst = os.path.join(GAME, name + '.map')
    bak, shipped = baseline_of(dst), dst + '.shipped'
    src = os.path.join(EK, 'maps', name + '.map')
    if not os.path.exists(src):
        # The build output is pruned after a successful install, so reinstalling
        # sources from the baseline instead -- which holds the same rebuild.
        shipped_size = os.path.getsize(shipped) if os.path.exists(shipped) else -1
        if os.path.exists(bak) and os.path.getsize(bak) != shipped_size:
            src = bak
            print('  no EK build; reinstalling from the baseline')
        else:
            raise SystemExit('no EK build at %s, and the baseline is not a rebuild'
                             % src)
    if not os.path.exists(shipped) and os.path.exists(bak):
        # Only when the candidate can still plausibly BE the shipped map. Once a
        # rebuild has been installed the baseline IS that rebuild, and copying it
        # into .shipped would enshrine it as the vanilla original forever --
        # map_vault treats .shipped as pristine by construction. The same size as
        # the build being installed means it is already a rebuild.
        if os.path.getsize(bak) == os.path.getsize(src):
            print('  NOT preserving the baseline as the shipped map: it is the same '
                  'size as the build being installed, so it is already a rebuild. '
                  'The vanilla %s is not on this disk.' % name)
        else:
            shutil.copy2(bak, shipped)
            print('  preserved the shipped map as %s' % os.path.basename(shipped))
    if src != dst:
        shutil.copy2(src, dst)
    print('  installed the EK build (%d bytes)' % os.path.getsize(dst))
    if baseline and src != bak:
        publish_baseline(name)
    prune(name)


def publish_baseline(name):
    """Make the CURRENT live map the patcher's baseline.

    Publishing from the live map rather than from the build output is what lets this
    be re-run after anything that edits an installed map -- zone pools, dual-wield
    plumbing, prepare_map. apply_run rebuilds every run from the baseline and saves
    over the live map, so a baseline captured before those edits undoes them on the
    next patch, silently.
    """
    dst = os.path.join(GAME, name + '.map')
    if not os.path.exists(dst):
        print('  no installed map at %s' % dst)
        return False
    bak = baseline_of(dst)
    try:
        os.makedirs(os.path.dirname(bak), exist_ok=True)
        shutil.copy2(dst, bak)
    except OSError as ex:
        print('  could NOT publish the baseline (%s) -- the next patch would rebuild '
              'from a stale one and undo this map' % ex)
        return False
    print('  baseline published: %s' % bak)
    return True


# Scratch copies that duplicate something already kept. `.shipped` is the vanilla
# original and `.bak` is the rebuild, so anything else is a second copy of one of them.
PRUNABLE = ('.working', '.kikotest')


def prune(name):
    """Delete redundant per-map copies once .shipped and .bak both exist.

    A single ODST level was costing ~1.9 GB across five files -- live map, baseline,
    vanilla, a pre-EK copy and a test baseline -- plus the build output. Two of those
    are byte-for-byte duplicates of the vanilla original and one duplicates the
    rebuild, which matters on a disk with 16 GB free.
    """
    dst = os.path.join(GAME, name + '.map')
    if not (os.path.exists(dst + '.shipped') and os.path.exists(baseline_of(dst))):
        print('  not pruning: .shipped and the baseline must both exist first')
        return
    freed = 0
    for suffix in PRUNABLE:
        p = dst + suffix
        if os.path.exists(p):
            freed += os.path.getsize(p)
            os.remove(p)
            print('  pruned %s' % os.path.basename(p))
    # The build output is now held by both .map and .bak, and --install can source
    # from .bak, so keeping a third copy in the kit buys nothing.
    ek = os.path.join(EK, 'maps', name + '.map')
    if os.path.exists(ek):
        freed += os.path.getsize(ek)
        os.remove(ek)
        print('  pruned the EK build output')
    if freed:
        print('  freed %.1f MB' % (freed / 1048576.0))


def restore(name, stock=False):
    """Put back the pre-EK map, or the shipped original with --stock.

    `.working` is pruned once `.shipped` exists, so the vanilla original is the
    fallback -- and the honest one, since that IS what the map was before any of this.
    """
    dst = os.path.join(GAME, name + '.map')
    for src in ([dst + '.shipped'] if stock else [dst + SAVED, dst + '.shipped']):
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print('  restored %d bytes from %s'
                  % (os.path.getsize(dst), os.path.basename(src)))
            if src.endswith('.shipped'):
                print('  NOTE: the baseline still holds the rebuild (%s) -- delete it '
                      'too for a fully stock map, or the next GUI patch restores the '
                      'rebuild' % baseline_of(dst))
            return
    raise SystemExit('nothing to restore for %s' % name)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--build')
    ap.add_argument('--install')
    ap.add_argument('--restore')
    ap.add_argument('--stock', action='store_true',
                    help='--restore puts back the shipped original, not the pre-EK map')
    ap.add_argument('--status')
    ap.add_argument('--prune', help='delete the redundant copies for this map')
    ap.add_argument('--baseline', metavar='MAP',
                    help='republish the baseline from the CURRENT live map -- run '
                         'this after anything that edits an installed map')
    ap.add_argument('--platform', default='pc')
    ap.add_argument('--no-baseline', action='store_true',
                    help='install without repointing .bak at the rebuild')
    a = ap.parse_args(argv)
    if a.build:
        build(a.build, a.platform)
    if a.install:
        install(a.install, baseline=not a.no_baseline)
    if a.baseline:
        publish_baseline(a.baseline)
    if a.prune:
        prune(a.prune)
    if a.restore:
        restore(a.restore, stock=a.stock)
    if a.status:
        status(a.status)
    if not any((a.build, a.install, a.restore, a.status, a.prune, a.baseline)):
        ap.print_help()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
