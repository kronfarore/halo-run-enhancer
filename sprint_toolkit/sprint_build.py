"""One-command builder for bisecting the H1 sprint mod on a map.

Restores <map>.scenario from its pristine .presprint backup, inserts the
sprint_profile (always) plus whatever weapons/equipment you ask for, builds the
map with tool.exe, deploys it to the game's halo1\\maps, and tunes+enables sprint.
Run it repeatedly with different --weapons / --equipment to find what corrupts the
graphics, testing each build in-game.

Examples:
  python sprint_build.py d40                         # sprint ONLY, remastered (clean baseline)
  python sprint_build.py d40 --equipment all         # sprint + the 3 powerups
  python sprint_build.py d40 --weapons needler       # sprint + one weapon
  python sprint_build.py b40 --graphics classic --weapons all --equipment all
  python sprint_build.py d40 --weapons "pistol,shotgun"

  --graphics classic|remastered   (default remastered)
  --weapons  none|all|human|alien|"a,b"   (short names, default none)
  --equipment none|all|"a,b"       (default none)
  --speed <pct>                    (default 150)
  --build-only                     (don't deploy/tune; leaves the game map alone)
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths  # noqa: E402  (install paths — edit paths.py)
import h1_loosetag as L  # noqa: E402

HCEEK = paths.HCEEK
MCC = paths.MCC
SCNR_XML = paths.SCNR_XML
TOOL = paths.TOOL_EXE

# Short name -> tag path. ONLY the Enhancer's H1 pool (weapons with real H1 assets).
WEAPONS = {
    'assault rifle': 'weapons\\assault rifle\\assault rifle',
    'flamethrower': 'weapons\\flamethrower\\flamethrower',
    'pistol': 'weapons\\pistol\\pistol',
    'rocket launcher': 'weapons\\rocket launcher\\rocket launcher',
    'shotgun': 'weapons\\shotgun\\shotgun',
    'sniper rifle': 'weapons\\sniper rifle\\sniper rifle',
    'needler': 'weapons\\needler\\needler',
    'plasma pistol': 'weapons\\plasma pistol\\plasma pistol',
    'plasma rifle': 'weapons\\plasma rifle\\plasma rifle',
}
HUMAN = ['assault rifle', 'flamethrower', 'pistol', 'rocket launcher', 'shotgun', 'sniper rifle']
ALIEN = ['needler', 'plasma pistol', 'plasma rifle']
EQUIP = {
    'active camouflage': 'powerups\\active camouflage',
    'over shield': 'powerups\\over shield',
    'health pack': 'powerups\\health pack',
}


def _resolve(spec, table, groups):
    """spec: 'none'|'all'|a group name|'a,b'. Returns a list of tag paths."""
    spec = (spec or 'none').strip().lower()
    if spec == 'none':
        return []
    if spec == 'all':
        names = list(table)
    elif spec in groups:
        names = groups[spec]
    else:
        names = [s.strip().lower() for s in spec.split(',') if s.strip()]
    out = []
    for n in names:
        if n not in table:
            sys.exit('unknown name %r; valid: %s' % (n, ', '.join(table)))
        out.append(table[n])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('map')
    ap.add_argument('--graphics', choices=('classic', 'remastered'), default='remastered')
    ap.add_argument('--weapons', default='none')
    ap.add_argument('--equipment', default='none')
    ap.add_argument('--speed', type=int, default=150)
    ap.add_argument('--resources', choices=('none', 'read', 'read_write'), default=None,
                    help="shared resource-map usage. Default: 'none' for classic "
                         "(self-contained; avoids the remastered bitmaps.map that "
                         "corrupts classic graphics), 'read_write' for remastered.")
    ap.add_argument('--build-only', action='store_true')
    a = ap.parse_args()
    # Classic builds MUST NOT read the remastered shared bitmaps.map (corrupts the
    # map) — default them to self-contained. Remastered matches the shared maps.
    if a.resources is None:
        a.resources = 'none' if a.graphics == 'classic' else 'read_write'

    weapons = _resolve(a.weapons, WEAPONS, {'human': HUMAN, 'alien': ALIEN})
    equip = _resolve(a.equipment, EQUIP, {})

    scn = os.path.join(HCEEK, 'tags', 'levels', a.map, a.map + '.scenario')
    pre = scn + '.presprint'
    if not os.path.exists(pre):
        shutil.copy2(scn, pre)
        print('backed up pristine scenario ->', os.path.basename(pre))
    # Always start from pristine, so each build is exactly sprint + the chosen set.
    data = bytearray(open(pre, 'rb').read())
    L.add_sprint(data, SCNR_XML)
    aw = L.add_palette_entries(data, SCNR_XML, L.PALETTE_OFF, b'weap', weapons)
    ae = L.add_palette_entries(data, SCNR_XML, L.EQUIP_PALETTE_OFF, b'eqip', equip)
    open(scn, 'wb').write(data)
    short = lambda p: p.split('\\')[-1]
    print('scenario: sprint_profile + %d weapon(s) %s + %d equipment %s'
          % (len(aw), [short(w) for w in aw], len(ae), [short(e) for e in ae]))

    print('building %s (%s)...' % (a.map, a.graphics))
    r = subprocess.run([TOOL, 'build-cache-file', 'levels\\%s\\%s' % (a.map, a.map),
                        a.graphics, a.resources, '1'], cwd=HCEEK,
                       capture_output=True, text=True)
    tail = (r.stdout or '').strip().splitlines()[-1:] or ['(no output)']
    if r.returncode != 0 or 'successfully built' not in (r.stdout or ''):
        print('BUILD FAILED:', tail[0])
        print((r.stdout or '')[-800:])
        sys.exit(1)
    print('  built OK')

    if a.build_only:
        print('build-only: not deployed. Built map at HCEEK\\maps\\%s.map' % a.map)
        return

    gamemap = os.path.join(MCC, 'halo1', 'maps', a.map + '.map')
    gamebak = gamemap + '.presprint.bak'
    if os.path.exists(gamemap) and not os.path.exists(gamebak):
        shutil.copy2(gamemap, gamebak)
        print('backed up vanilla game map ->', os.path.basename(gamebak))
    shutil.copy2(os.path.join(HCEEK, 'maps', a.map + '.map'), gamemap)
    for stale in (gamemap + '.bak',):
        if os.path.exists(stale):
            os.remove(stale)
    print('deployed to halo1\\maps\\%s.map' % a.map)

    r = subprocess.run([sys.executable, os.path.join(HERE, 'sprint_tune.py'), gamemap,
                        '--mult', '%g' % (a.speed / 100.0), '--enable'],
                       capture_output=True, text=True)
    for line in (r.stdout or '').splitlines():
        if 'sprint_enabled' in line or 'wrote' in line:
            print(' ', line.strip())
    print('DONE - test %s in-game (%s, sprint %d%%).' % (a.map, a.graphics, a.speed))


if __name__ == '__main__':
    main()
