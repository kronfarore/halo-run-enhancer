r"""Build a Halo 3 map and REFUSE to believe it worked unless it says so.

`tool build-cache-file` exits 0 when it crashes. A run that dies in globals
postprocessing after twenty seconds and a run that writes a 549 MB cache file both come
back with status 0, and if the output is piped through `tail` the only difference is a
few lines of crash dump that look much like the warnings a healthy build also prints.

Two rebuilds were deployed and tested from a map that had never been rebuilt, because
the installer happily copied the previous one and every check it ran -- the port is
present, the clone owns its blocks, the frame counts are right -- was true of the OLD
map. The tell was a timestamp that had not moved.

So success is taken from the build's own words, "successfully built cache file", and
from the cache file's timestamp actually advancing. Anything else is a failure, and the
assertion is printed rather than buried.

    python h3_build_map.py                       # 010_jungle
    python h3_build_map.py --map 020_base
"""
import argparse, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

B = os.sep
import h3_kit                                              # noqa: E402
EK = h3_kit.EK
OK = 'successfully built cache file'


#: Which maps belong to which kit. ODST's kit SHIPS HALO 3'S SOLO LEVELS as well as its
#: own, so `build-cache-file levels\solo\010_jungle` succeeds there and produces a HYBRID
#: -- Halo 3's level against ODST's tag set, 514 MB of nothing anyone wants, dropped in
#: the ODST kit's maps folder. It happened: PORT_EK was left at `odst` in the shell from
#: an earlier command, and the build looked like a success for seven minutes.
MAPS = {
    'h3': ('005_intro', '010_jungle', '020_base', '030_outskirts', '040_voi',
           '050_floodvoi', '070_waste', '100_citadel', '110_hc', '120_halo'),
    'odst': ('c100', 'c200', 'h100', 'l200', 'l300', 'sc100', 'sc110', 'sc120',
             'sc130', 'sc140', 'sc150'),
    # Reach builds through reach_ek_build.py, which takes its list from halo.json and
    # so leaves out m05 and m70_a -- in the kit, not in the game.
    'reach': ('m10', 'm20', 'm30', 'm35', 'm45', 'm50', 'm52', 'm60', 'm70',
              'm70_bonus'),
}
#: names a kit carries that the game never runs, refused by name and with the reason
NOT_MISSIONS = {'reach': ('m05', 'm70_a')}
GAME_OF = {'h3': 'Halo 3', 'odst': 'Halo 3: ODST', 'reach': 'Halo Reach'}
KIT_OF = {name: short for short, names in MAPS.items() for name in names}


def check_kit(name):
    """Refuse a map that does not belong to the selected kit."""
    if name in MAPS[h3_kit.SHORT]:
        return
    if name in NOT_MISSIONS.get(h3_kit.SHORT, ()):
        raise SystemExit('%s ships in %s but the game never runs it -- building it is '
                         'an hour of nothing.' % (name, h3_kit.banner()))
    hint = ''
    owner = KIT_OF.get(name)
    if owner:
        hint = ('\n%s is a %s map. Set the kit first:\n    set PORT_EK=%s'
                % (name, GAME_OF[owner], owner))
    raise SystemExit('%s is not a map of %s.%s' % (name, h3_kit.banner(), hint))


def build(name, log=None):
    check_kit(name)
    # BACKSLASHES. tool derives the report directory from this string, and given forward
    # slashes it fails to open reports\<map>\cache_file_loaded_tags.txt and asserts
    # g_cache_file_loaded_tags_report_file_ready before it has built anything.
    # ODST's levels live under levels\atlas (2026-10-03: `levels\solo\sc150` failed to load
    # the scenario); Halo 3's under levels\solo.
    folder = 'atlas' if h3_kit.EK.rstrip(os.sep).lower().endswith('h3odstek') else 'solo'
    scenario = os.path.join('levels', folder, name, name)
    out = os.path.join(EK, 'maps', name + '.map')
    before = os.path.getmtime(out) if os.path.exists(out) else 0
    t0 = time.time()
    # TWO arguments and no more. The usage line advertises optional audio, language and
    # compression arguments, but passing "default" for them kills the build instantly:
    # it asserts g_cache_file_loaded_tags_report_file_ready in globals postprocessing
    # about twenty seconds in, and still exits 0.
    p = subprocess.run([os.path.join(EK, 'tool.exe'), 'build-cache-file', scenario, 'pc'],
                       cwd=EK, capture_output=True, text=True, errors='replace')
    text = (p.stdout or '') + (p.stderr or '')
    if log:
        open(log, 'w', encoding='utf-8').write(text)
    took = time.time() - t0
    after = os.path.getmtime(out) if os.path.exists(out) else 0

    said_ok = OK in text
    moved = after > before
    print('build %s: %.0f s, exit %d, said "%s": %s, cache file rewritten: %s'
          % (name, took, p.returncode, OK, said_ok, moved))
    if said_ok and moved:
        return out

    for line in text.splitlines():
        if ('ASSERTION' in line or '-FATAL-' in line or 'ERROR' in line
                or 'crash:' in line):
            print('   %s' % line.strip())
    raise SystemExit('BUILD FAILED -- do not install this map, it is the previous one')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', default='010_jungle')
    ap.add_argument('--log', default=os.path.join(os.environ.get('TEMP', '.'),
                                                  'h3_build.log'))
    a = ap.parse_args()
    out = build(a.map, a.log)
    print('ok -> %s' % out)


if __name__ == '__main__':
    main()
