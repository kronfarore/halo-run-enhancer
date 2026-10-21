r"""The dry TEST MAP for a Halo 2 port: the level built with the port in the player's hands, staged
live for a boot and put back after -- one level per port at a time (H2_PORT_PLAN.md 0.6; the
Halo 2 counterpart of h1_port_test_map.py, replacing the SAW-only h2_saw_place.py).

    python h2_port_test_map.py <key> --level 03a [--profiles "starting profile,respawn profile"]
                                     [--rounds 72,216] [--stage] [--keep-kit-map]
                                     [--armed elite,grunt,jackal[,brute]] [--share 1]
    python h2_port_test_map.py <key> --restore <level>
    python h2_port_test_map.py --status

BUILD (H2 kit lock held; the kit is ALWAYS put back):
  * the level's SCENARIO: each named Player Starting Profile's PRIMARY weapon = the port
    (default: the level's first two profiles -- index 0 spawn, 1 respawn; memory
    halo2-h2-starting-profiles), rounds from --rounds / the config's test.rounds if given;
  * the level's WEAPONS RESOURCE: the port's palette entry if it is not resident yet, and every
    OTHER port that is not 'done' NEUTRALISED (its palette entry renamed to a stock weapon the
    level carries, h2_port_residency.neutralise) -- a parallel session's broken in-progress tags
    can never fail your build (Halo 1's lesson from pair 1);
  * tool build-cache-file (h2_batch.build_cache) -> H2EK\h2_maps_win64_dx11\port_test\<level>.map;
  * scenario + resource restored byte-identical, the kit's own <level>.map output put back.
STAGE (--stage): the LIVE map (halo2\h2_maps_win64_dx11\<level>.map) is backed up to
E:\HaloBackups\h2_port_test\<level>.map -- never over a backup of its own staged copy -- and the
test map copied live. OWNERSHIP: E:\HaloBackups\h2_port_test\stage.json records which port staged
each level; staging or restoring a level another port owns is refused (--force overrides).
--restore puts the live map back from that backup and frees the level.
ARMED (--armed SPECIES, 0.5b): after the build, every squad unit of those species in the TEST map
spawns with the port (h2_armed_test.arm: squad / starting-location weapon indices -> the port's
palette entry; vehicle-bound squads untouched); its firing data comes from the kit's ai\generic
(ai_firing_profile.py --h2-port <key>, which must have run).
Tests are in CLASSIC (a rebuilt H2 map is a classic-side build; memory halo2-loose-tag-format).
"""
import argparse
import json
import os
import shutil
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import h2_batch  # noqa: E402
import h2_loosetag as L  # noqa: E402
import h2_port_residency as R  # noqa: E402
import kit_lock  # noqa: E402
import ports_h2  # noqa: E402

H2EK = h2_batch.H2EK
MCC_MAPS = os.path.join(os.path.dirname(ROOT), 'halo2', 'h2_maps_win64_dx11')
TEST_DIR = os.path.join(h2_batch.MAPS_OUT, 'port_test')
STAGE_DIR = os.path.join('E:' + os.sep, 'HaloBackups', 'h2_port_test')
STAGE_JSON = os.path.join(STAGE_DIR, 'stage.json')
LOGDIR = os.path.join(HERE, 'out', 'h2logs_port_test')
PRIMARY, LOADED = 0x28, 0x38      # profile element: primary weapon tagref, rounds loaded/total


def level_name(s):
    return h2_batch.BY_SHORT.get(s, s)


def scenario(level):
    return os.path.join(H2EK, 'tags', 'scenarios', 'solo', level, level + '.scenario')


def profile_refs(data):
    """[(profile index, name, ref offset, field offset, pool offset, length)] for every profile
    weapon ref, in pool order."""
    c = L.locate(data, L.PROFILES, L.PRS)
    n = L.root_count(data, L.PROFILES)
    base = c + L.CHUNK
    cur = base + n * L.PRS
    out = []
    for i in range(n):
        nm = bytes(data[base + i * L.PRS:base + i * L.PRS + 0x20]).split(b'\0')[0].decode('latin-1')
        for off in (PRIMARY, 0x3C):
            at = base + i * L.PRS + off
            ln = struct.unpack_from('<I', data, at + 8)[0]
            out.append((i, nm, at, off, cur, ln))
            cur += ln + 1 if ln else 0
    return out


def arm_profiles(data, weapon, names, rounds=None):
    """Point each named profile's primary at `weapon` (pool + length, back to front)."""
    refs = profile_refs(data)
    targets = [r for r in refs if r[1] in names and r[3] == PRIMARY]
    if len(targets) != len(names):
        raise SystemExit('profiles %s not all found (have %s)' % (names, sorted({r[1] for r in refs})))
    # back to front by pool offset; an EMPTY ref pools nothing, so it shares its offset with
    # the next ref's string -- at equal offsets the LATER ref goes first (01b's profile 0 has
    # no primary: inserting it first shifted profile 1's string out from under it)
    order = sorted(enumerate(refs), key=lambda e: (-e[1][4], -e[0]))
    for _n, (i, nm, at, _off, pool, ln) in [e for e in order if e[1] in targets]:
        new = weapon.encode('latin-1')
        if ln:
            data[pool:pool + ln] = new
        else:
            data[pool:pool] = new + b'\0'
        struct.pack_into('<I', data, at + 8, len(new))
        if rounds:
            struct.pack_into('<hh', data, at - PRIMARY + LOADED, rounds[0], rounds[1])
    after = profile_refs(data)
    return [(nm, bytes(data[p:p + ln]).decode('latin-1')) for _i, nm, _a, off, p, ln in after
            if off == PRIMARY and nm in names]


def stage_info():
    try:
        return json.load(open(STAGE_JSON))
    except (OSError, ValueError):
        return {}


def save_stage(info):
    os.makedirs(STAGE_DIR, exist_ok=True)
    json.dump(info, open(STAGE_JSON, 'w'), indent=1)


def owner_check(info, level, key, force):
    cur = info.get(level, {}).get('owner')
    if cur and cur != key and not force:
        raise SystemExit('%s is staged by %s -- one test level per session (--force overrides)' % (level, cur))


def build(key, level, profiles, rounds, keep_kit_map=False, armed=None, share=1.0, god=True,
          replace=True):
    p = ports_h2.load(key)
    weapon = R.weapon_path(p)
    scn, res = scenario(level), R.resource(level)
    kit_map = os.path.join(h2_batch.MAPS_OUT, level + '.map')
    keep = {f: f + '.port_test_keep' for f in (scn, res, kit_map) if os.path.exists(f)}
    os.makedirs(LOGDIR, exist_ok=True)
    with kit_lock.held('h2_port_test_map %s %s' % (key, level), owner=key, kit='h2'):
        for f, k in keep.items():
            shutil.copy2(f, k)
        try:
            d = bytearray(open(scn, 'rb').read())
            if not profiles:
                names = [r[1] for r in profile_refs(d) if r[3] == PRIMARY][:2]
                profiles = [n for n in names if not n.startswith('ab_')]
            got = arm_profiles(d, weapon, profiles, rounds)
            open(scn, 'wb').write(bytes(d))
            print('%s: %s' % (level, ', '.join('%s -> %s' % (n, w.split('\\')[-1]) for n, w in got)))
            r = bytearray(open(res, 'rb').read())
            idx, new = R.add_palette(r, weapon)
            busy = [R.weapon_path(q) for k, q in ports_h2.all_ports()
                    if k != key and q.get('status') != 'done']
            gone = R.neutralise(r, busy)
            open(res, 'wb').write(bytes(r))
            print('   palette: the port #%d%s; neutralised %s' % (idx, ' (added)' if new else '',
                  ', '.join(x[1].split('\\')[-1] for x in gone) or 'nothing (no other port in progress)'))
            t0 = time.time()
            ok, msg = h2_batch.build_cache(level, LOGDIR)
            print('   build %s: %s (%.0f s)' % ('ok' if ok else 'FAILED', msg, time.time() - t0))
            if ok:
                os.makedirs(TEST_DIR, exist_ok=True)
                shutil.copy2(kit_map, os.path.join(TEST_DIR, level + '.map'))
                if armed or god:
                    import h2_armed_test
                    h2_armed_test.test_map(os.path.join(TEST_DIR, level + '.map'), weapon, armed,
                                           share, god=god, replace=replace)
                if armed:
                    print('   (Armed = BALANCED AI rows; shieldless Jackals, Grunt teach + half '
                          'rate, species skill)')
        finally:
            for f, k in keep.items():
                if f == kit_map and keep_kit_map:
                    os.remove(k)
                    continue
                shutil.copy2(k, f)
                os.remove(k)
            print('   kit restored (scenario, weapons resource%s)'
                  % ('' if keep_kit_map else ', the kit\'s own .map output'))
    if not ok:
        raise SystemExit(1)
    return os.path.join(TEST_DIR, level + '.map')


def stage(key, level, built, force):
    info = stage_info()
    owner_check(info, level, key, force)
    live = os.path.join(MCC_MAPS, level + '.map')
    bak = os.path.join(STAGE_DIR, level + '.map')
    if level not in info:                 # never back up a staged copy over the real one
        os.makedirs(STAGE_DIR, exist_ok=True)
        shutil.copy2(live, bak)
        print('   live map backed up -> %s' % bak)
    shutil.copy2(built, live)
    info[level] = {'owner': key, 'since': time.strftime('%Y-%m-%d %H:%M')}
    save_stage(info)
    print('   STAGED %s live (%.0f MiB) -- boot it in CLASSIC; restore with: '
          'python h2_port_test_map.py %s --restore %s' % (level, os.path.getsize(live) / 2**20, key, level))


def restore(key, level, force):
    info = stage_info()
    owner_check(info, level, key, force)
    bak = os.path.join(STAGE_DIR, level + '.map')
    if level not in info or not os.path.exists(bak):
        raise SystemExit('%s is not staged' % level)
    shutil.copy2(bak, os.path.join(MCC_MAPS, level + '.map'))
    os.remove(bak)
    del info[level]
    save_stage(info)
    print('restored the live %s' % level)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key', nargs='?')
    ap.add_argument('--level')
    ap.add_argument('--profiles', default='')
    ap.add_argument('--rounds', default='')
    ap.add_argument('--stage', action='store_true')
    ap.add_argument('--restore')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--keep-kit-map', action='store_true')
    ap.add_argument('--armed', default='', help='species whose squads spawn with the port')
    ap.add_argument('--share', type=float, default=1.0)
    ap.add_argument('--no-replace', action='store_true',
                    help='--armed: keep the level\'s own enemies (default: the squads nearest the '
                         'start become the tested types, 2 each)')
    ap.add_argument('--mortal', action='store_true',
                    help='NO god shield (every other port test has one: the Halo 1 rule)')
    a = ap.parse_args()
    if a.status:
        print(json.dumps(stage_info(), indent=1) or '{}')
        return
    if not a.key:
        raise SystemExit(__doc__)
    if a.restore:
        with kit_lock.held('h2_port_test_map %s --restore %s' % (a.key, a.restore), owner=a.key, kit='h2'):
            restore(a.key, level_name(a.restore), a.force)
        return
    cfg = ports_h2.load(a.key)
    level = level_name(a.level or (cfg.get('test') or {}).get('level') or
                       cfg['reservations'].get('test_level') or '')
    if not level:
        raise SystemExit('--level, please')
    rounds = tuple(int(x) for x in a.rounds.split(',')) if a.rounds else \
        tuple((cfg.get('test') or {}).get('rounds') or ()) or None
    profiles = [x.strip() for x in a.profiles.split(',') if x.strip()]
    armed = [x.strip() for x in a.armed.split(',') if x.strip()]
    built = build(a.key, level, profiles, rounds, a.keep_kit_map, armed, a.share, god=not a.mortal,
                  replace=not a.no_replace)
    print('test map: %s' % built)
    if a.stage:
        with kit_lock.held('h2_port_test_map %s --stage %s' % (a.key, level), owner=a.key, kit='h2'):
            stage(a.key, level, built, a.force)


if __name__ == '__main__':
    main()
