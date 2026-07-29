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
import install_script  # noqa: E402  (keeps global_scripts.hsc in sync with sprint.hsc)

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
    ap.add_argument('--ability', choices=('none', 'sprint', 'overshield', 'camo',
                                          'regeneration', 'medikit'),
                    default='sprint',
                    help="flashlight-key ability to enable on the built map for BOTH "
                         "players (default sprint).")
    # Optional powerup tuning, passed straight through to sprint_tune so ONE command
    # builds + enables + tunes (durations/cooldowns in ticks, 30/sec).
    ap.add_argument('--os-mult', type=float, help="overshield strength as a clean multiplier "
                    "(x2, x3, ...); converted to the raw object_set_shield value internally")
    ap.add_argument('--os-shield', type=float, help="RAW object_set_shield value (advanced; "
                    "use --os-mult). ~0.0267 = x2")
    ap.add_argument('--os-duration', type=int, help="overshield active window, ticks")
    ap.add_argument('--os-cooldown', type=int, help="overshield cooldown, ticks")
    ap.add_argument('--camo-duration', type=int, help="camo window, ticks")
    ap.add_argument('--camo-cooldown', type=int, help="camo cooldown, ticks")
    ap.add_argument('--medi-percent', type=float, help="Regeneration total heal as a percent of "
                    "max health (100 = full heal), spread over --medi-duration")
    ap.add_argument('--medi-heal', type=float, help="Regeneration total heal in raw vitality "
                    "units (75 = full), spread over --medi-duration")
    ap.add_argument('--medi-duration', type=int, help="Regeneration window, ticks (1 = instant)")
    ap.add_argument('--medi-rate', type=float, help="Regeneration per-tick heal, set outright "
                    "(overrides --medi-heal/--medi-duration)")
    ap.add_argument('--vit-max', type=float, help="absolute vitality scale (default 75); must "
                    "match the unit's true max or regeneration ratchets to full")
    ap.add_argument('--spawn-shield', type=float, help="Starting Shield Modifier on the player "
                    "profiles (1 = normal, 3 = vanilla 3x overshield on every spawn)")
    ap.add_argument('--spawn-health', type=float, help="Starting Health Modifier on the player "
                    "profiles (1 = normal)")
    ap.add_argument('--medi-cooldown', type=int, help="Regeneration cooldown, ticks")
    ap.add_argument('--resources', choices=('none', 'read', 'read_write'), default=None,
                    help="shared resource-map usage. Default 'none' (self-contained) for "
                         "both graphics modes — a read_write build references the shared "
                         "bitmaps.map and corrupts the UI/classic view.")
    ap.add_argument('--build-only', action='store_true')
    a = ap.parse_args()
    # Build SELF-CONTAINED by default, for BOTH graphics modes (matches batch_build).
    # A read_write build references the shared bitmaps.map by index, which corrupts the
    # UI and the classic view; a self-contained ('none') build renders correctly in
    # both the remastered and classic in-game views. Overridable via --resources.
    if a.resources is None:
        a.resources = 'none'

    # Sync the sprint script into global_scripts.hsc so the build carries the
    # current sprint.hsc (idempotent — a no-op once it's already current).
    try:
        install_script.install(paths.GLOBAL_SCRIPTS)
    except RuntimeError as e:
        sys.exit('script install: %s' % e)

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

    # Powerups don't use the sprint speed mechanic, so leave run speed vanilla for
    # them (mult 1.0); only the sprint ability raises it.
    mult = a.speed / 100.0 if a.ability == 'sprint' else 1.0
    extra = []
    for flag, val in (('--os-mult', a.os_mult), ('--os-shield', a.os_shield),
                      ('--os-duration', a.os_duration),
                      ('--os-cooldown', a.os_cooldown), ('--camo-duration', a.camo_duration),
                      ('--camo-cooldown', a.camo_cooldown), ('--medi-percent', a.medi_percent),
                      ('--medi-heal', a.medi_heal),
                      ('--medi-duration', a.medi_duration), ('--medi-rate', a.medi_rate),
                      ('--vit-max', a.vit_max), ('--spawn-shield', a.spawn_shield),
                      ('--spawn-health', a.spawn_health),
                      ('--medi-cooldown', a.medi_cooldown)):
        if val is not None:
            extra += [flag, '%g' % val]
    r = subprocess.run([sys.executable, os.path.join(HERE, 'sprint_tune.py'), gamemap,
                        '--mult', '%g' % mult, '--ability', a.ability] + extra,
                       capture_output=True, text=True)
    for line in (r.stdout or '').splitlines():
        if 'ability' in line or 'enabled' in line or 'wrote' in line or '!!' in line:
            print(' ', line.strip())
    how = 'vanilla (no ability)' if a.ability == 'none' else \
        ('sprint %d%% — hold movement + flashlight key' % a.speed if a.ability == 'sprint'
         else '%s — press the flashlight key to use it' % a.ability)
    print('DONE - test %s in-game (%s). Ability: %s.' % (a.map, a.graphics, how))


if __name__ == '__main__':
    main()
