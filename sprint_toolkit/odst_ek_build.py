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
import os
import shutil
import subprocess

EK = r"C:\Program Files (x86)\Steam\steamapps\common\H3ODSTEK"
GAME = (r"C:\Program Files (x86)\Steam\steamapps\common"
        r"\Halo The Master Chief Collection\halo3odst\maps")
SCENARIO = r"levels\atlas\%s\%s"
# Keep the pre-EK map under its own name. `.bak` belongs to the GUI patcher and must
# stay the shipped baseline, so it is never touched here.
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
    for label, path in (('game   ', os.path.join(GAME, name + '.map')),
                        ('saved  ', os.path.join(GAME, name + '.map' + SAVED)),
                        ('shipped', os.path.join(GAME, name + '.map.bak')),
                        ('EK     ', os.path.join(EK, 'maps', name + '.map'))):
        print('  %s %s' % (label, ('%d bytes' % os.path.getsize(path))
                           if os.path.exists(path) else '(absent)'))


def install(name):
    src = os.path.join(EK, 'maps', name + '.map')
    dst = os.path.join(GAME, name + '.map')
    if not os.path.exists(src):
        raise SystemExit('no EK build at %s' % src)
    saved = dst + SAVED
    if not os.path.exists(saved):
        shutil.copy2(dst, saved)
        print('  saved the current map as %s' % os.path.basename(saved))
    shutil.copy2(src, dst)
    print('  installed the EK build (%d bytes)' % os.path.getsize(dst))


def restore(name):
    dst = os.path.join(GAME, name + '.map')
    saved = dst + SAVED
    if not os.path.exists(saved):
        raise SystemExit('nothing saved at %s' % saved)
    shutil.copy2(saved, dst)
    print('  restored %d bytes from %s' % (os.path.getsize(dst),
                                           os.path.basename(saved)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--build')
    ap.add_argument('--install')
    ap.add_argument('--restore')
    ap.add_argument('--status')
    ap.add_argument('--platform', default='pc')
    a = ap.parse_args(argv)
    if a.build:
        build(a.build, a.platform)
    if a.install:
        install(a.install)
    if a.restore:
        restore(a.restore)
    if a.status:
        status(a.status)
    if not any((a.build, a.install, a.restore, a.status)):
        ap.print_help()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
