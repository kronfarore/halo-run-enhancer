"""One command for a SAW test build in Halo 1, start to finish (a10 by default):

  1. tool bitmaps weapons\\saw\\bitmaps          (TIF sources already in HCEEK data)
  2. saw_shaders.py                              (shader_model tags)
  3. saw_to_jms.py at --scale                    (fp + 3p JMS on the AR skeleton)
  4. tool model weapons\\saw\\fp and weapons\\saw  (gbxmodels)
  5. make_icon.py + add_msg_icon.py + saw_weapon.py  (prompt icon, HUD interface, weapon)
  6. saw_scenario.py --map <map>                 (SAW into that map's spawn profiles)
  7. tool build-cache-file levels\\<map>\\<map> classic none 1 (self-contained classic)
  8. saw_scenario.py --restore                   (always, even when the build fails)
  9. deploy HCEEK\\maps\\<map>.map to the game (original kept as <map>.map.before_saw)

    python saw_build.py [--map a10] --scale 1.0 [--skip-bitmaps] [--no-deploy]
"""
import argparse, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
HCEEK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK')
GAME_MAPS = os.path.join('C:' + os.sep, 'Program Files (x86)', 'Steam', 'steamapps',
                         'common', 'Halo The Master Chief Collection', 'halo1', 'maps')
XML = os.path.join(os.environ['TEMP'], 'lmg_rm.xml')
B = os.sep


def run(args, cwd=None, check_text=None):
    print('>', ' '.join(args), flush=True)
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, errors='replace')
    tail = (r.stdout or '').strip().splitlines()[-3:]
    for line in tail:
        print('   ', line)
    if r.returncode not in (0, None) or (check_text and check_text not in (r.stdout or '')):
        print((r.stdout or '')[-1500:], (r.stderr or '')[-800:])
        raise SystemExit('step failed: ' + ' '.join(args))
    return r.stdout


def py(script, *args):
    return run([sys.executable, os.path.join(HERE, script)] + list(args))


def tool(*args, check_text=None):
    return run([os.path.join(HCEEK, 'tool.exe')] + list(args), cwd=HCEEK, check_text=check_text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', default='a10',
                    help='the level to build the test on; saw_scenario.py must know '
                         'which of its starting profiles are spawns')
    ap.add_argument('--scale', type=float, default=1.0)
    ap.add_argument('--skip-bitmaps', action='store_true')
    ap.add_argument('--no-deploy', action='store_true')
    ap.add_argument('--anims', choices=('original', 'balanced'), default='original',
                    help='reload and swap timing: the port own timing, or scaled like the donor')
    a = ap.parse_args()
    if not a.skip_bitmaps:
        tool('bitmaps', 'weapons' + B + 'saw' + B + 'bitmaps')
    py('saw_shaders.py')
    py('saw_to_jms.py', XML, os.path.join(HCEEK, 'data'), str(a.scale))
    tool('model', 'weapons' + B + 'saw' + B + 'fp')
    tool('model', 'weapons' + B + 'saw')
    # pickup-prompt icon: rendered from the 3p JMS, added to hud_msg_icons as seq 25
    py('make_icon.py', os.path.join(HCEEK, 'data', 'weapons', 'saw', 'models', 'saw.jms'),
       os.path.join(HERE, 'h1mp', 'saw_icon.png'), '110')
    py('add_msg_icon.py', os.path.join(HERE, 'h1mp', 'saw_icon.png'), 'saw')
    # STEP 10, its own sounds (2026-10-05): BEFORE saw_anims, which only names the own
    # reload / melee / ready sounds when their tags exist; also writes the bank audio
    # (tool\port_sounds\halo1) that port_sounds.py installs after the deploy
    py('h1_saw_sounds.py', '--write')
    py('saw_anims.py', 'original')
    py('saw_anims.py', 'balanced')      # shipped too, for the patcher's balance option
    py('ammo_meter.py', '72', '135',
       'weapons' + B + 'saw' + B + 'bitmaps' + B + 'saw_ammo')
    py('saw_weapon.py')
    # AFTER saw_weapon, never before: saw_weapon builds the port's tag FROM the Assault
    # Rifle's, so it resets item_attrs.message_index to 4 -- the Assault Rifle's "Picked
    # up an assault rifle". Running this first would be silently undone, and the port
    # would announce itself as an Assault Rifle again.
    py('h1_port_messages.py', '--write')
    # --write, because it is a dry run by default: it verifies every path and unit
    # factor against the Assault Rifle first and refuses if one no longer holds.
    py('saw_port_values.py', '--write')  # the port's own H4 numbers into its H1 tags
    py('saw_scenario.py', '--map', a.map)
    try:
        tool('build-cache-file', 'levels' + B + a.map + B + a.map, 'classic', 'none', '1',
             check_text='successfully built')
    finally:
        py('saw_scenario.py', '--map', a.map, '--restore')
    if a.no_deploy:
        print('built, not deployed')
        return
    live = os.path.join(GAME_MAPS, a.map + '.map')
    bak = os.path.join(HERE, a.map + '.map.before_saw')
    if not os.path.exists(bak):
        shutil.copy2(live, bak)
    shutil.copy2(os.path.join(HCEEK, 'maps', a.map + '.map'), live)
    print('deployed %s (scale %.2f); original kept at %s' % (a.map, a.scale, bak))
    # MCC's Halo 1 plays its sounds from the FMOD bank, not the map (port_sounds.py)
    run([sys.executable, os.path.join(os.path.dirname(HERE), 'port_sounds.py'), '--write'])


if __name__ == '__main__':
    main()
