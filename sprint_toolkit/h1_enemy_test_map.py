r"""A Halo 1 TEST map for enemy behaviour: every Grunt / Elite of a level replaced by one
chosen actor variant each, and the player given an unbreakable shield.

Memory rule (halo-test-enemy-placement): a character test replaces the level's enemies
with the one under test, so it shows up at once. Done on a COPY of the built map:

  1. KIT: the chosen actor variants are appended to the level's Actor Palette (scnr
     +0x420, 16-byte tagRef elements) when the level does not carry them -- a50 has the
     sword Elites but no fuel rod Grunt -- the level is built (`h1_rebuild_all --no-ship`),
     and the kit scenario is put back exactly as it was and the normal map rebuilt.
  2. MAP COPY: every palette entry naming a Grunt (or Elite) variant is repointed to the
     chosen one (class, name pointer and datum id copied from the tag index), so every
     squad spawns it; the enhancer's slots (`characters\enhancer\slot NN`) are left alone.
  3. GOD SHIELD: the player's collision model (`characters\cyborg\cyborg`): maximum shield
     and body vitality 1e6, no leak through a failing shield, no stun, instant recharge.

Output: HCEEK\maps\enemy_test\<level>.map -- copy it over the game's map to play it.

    python h1_enemy_test_map.py --level a50 ^
        --grunt "characters\grunt\grunt specops fuel rod" ^
        --elite "characters\elite\elite commander\elite commander energy sword"
"""
import argparse
import os
import shutil
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import paths                 # noqa: E402
import h1_loosetag as L      # noqa: E402
import halo_patch            # noqa: E402

HCEEK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK')
ACTOR_PALETTE = 0x420
COLL = 'characters\\cyborg\\cyborg'
# collision model fields (Assembly Halo1 coll.xml)
MAX_BODY, MAX_SHIELD, LEAK, STUN, RECHARGE = 0x8, 0xCC, 0xF4, 0x10C, 0x110


def scenario_path(level):
    return os.path.join(HCEEK, 'tags', 'levels', level, level + '.scenario')


def build(level):
    r = subprocess.run([sys.executable, os.path.join(HERE, 'h1_rebuild_all.py'), '--maps', level,
                        '--no-ship'], capture_output=True, text=True)
    if 'DONE: 1 ok' not in r.stdout:
        print(r.stdout[-1500:], r.stderr[-800:])
        raise SystemExit('build failed')


def tag_ids(m):
    """{(class, path): (datum id, name pointer)} from the tag index."""
    byoff = {v: k for k, v in m.tags.items()}
    out = {}
    i = 0
    while True:
        e = m.tag_array_off + i * 0x20
        if e + 0x20 > len(m.data):
            break
        tid, nptr, mptr = struct.unpack_from('<III', m.data, e + 0xC)
        meta = (mptr - m.magic) & 0xFFFFFFFF
        if meta in byoff:
            out[byoff[meta]] = (tid, nptr)
        elif i > len(m.tags) + 5:
            break
        i += 1
    return out


def swap_actors(m, want):
    """On an opened BUILT map: every Actor Palette entry naming a Grunt / Elite variant is
    repointed to want['grunt'] / want['elite'] (either may be missing: that kind is left
    alone). The enhancer's slots are not under characters\\grunt|elite, so they stay."""
    d = m.data
    ids = tag_ids(m)
    targets = {k: ids[('actv', p)] for k, p in want.items() if p}
    scnr = [v for k, v in m.tags.items() if k[0] == 'scnr'][0]
    cnt, ptr = struct.unpack_from('<II', d, scnr + ACTOR_PALETTE)
    arr = (ptr - m.magic) & 0xFFFFFFFF
    names = {v[0]: k[1] for k, v in ids.items()}
    swapped = []
    for i in range(cnt):
        e = arr + i * 16
        tid = struct.unpack_from('<I', d, e + 12)[0]
        name = names.get(tid, '')
        kind = ('grunt' if name.startswith('characters\\grunt\\') else
                'elite' if name.startswith('characters\\elite\\') else None)
        if kind in targets and name != want[kind]:
            new_id, new_ptr = targets[kind]
            struct.pack_into('<I', d, e + 4, new_ptr)
            struct.pack_into('<I', d, e + 12, new_id)
            swapped.append('%d %s' % (i, name.rsplit('\\', 1)[-1]))
    print('palette entries repointed: %d (%s)' % (len(swapped), ', '.join(swapped)))
    return swapped


def god_shield(m):
    """The player's collision model: shield and body 1e6, no leak, no stun, instant recharge."""
    d = m.data
    coll = m.tags[('coll', COLL)]
    for off, v in ((MAX_BODY, 1e6), (MAX_SHIELD, 1e6), (LEAK, 0.0), (STUN, 0.0), (RECHARGE, 0.1)):
        struct.pack_into('<f', d, coll + off, v)
    print('player shield: %s' % [round(struct.unpack_from('<f', d, coll + o)[0], 3)
                                 for o in (MAX_BODY, MAX_SHIELD, LEAK, STUN, RECHARGE)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--level', default='a50')
    ap.add_argument('--grunt', required=True)
    ap.add_argument('--elite', required=True)
    a = ap.parse_args()
    want = {'grunt': a.grunt, 'elite': a.elite}

    # 1. kit: the variants in the palette, build, put the scenario back, rebuild normal
    sp = scenario_path(a.level)
    keep = sp + '.before_enemytest'
    shutil.copy2(sp, keep)
    try:
        data = bytearray(open(sp, 'rb').read())
        have = L.read_block_paths(data, paths.SCNR_XML, ACTOR_PALETTE)
        added = []
        for p in want.values():
            if p not in have:
                L.insert_block_element(data, paths.SCNR_XML, ACTOR_PALETTE,
                                       L._tagref(b'actv', p), p)
                added.append(p)
        open(sp, 'wb').write(data)
        print('palette: %d entries, added %s' % (len(have) + len(added), added or 'nothing'))
        build(a.level)
        built = os.path.join(HCEEK, 'maps', a.level + '.map')
        out_dir = os.path.join(HCEEK, 'maps', 'enemy_test')
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, a.level + '.map')
        shutil.copy2(built, out)
    finally:
        shutil.copy2(keep, sp)
        os.remove(keep)
    print('kit scenario restored; rebuilding the normal %s' % a.level)
    build(a.level)

    # 2. + 3. on the copy
    m = halo_patch.open_map(out, 'Halo 1')
    swap_actors(m, want)
    god_shield(m)
    open(out, 'wb').write(bytes(m.data))
    print('wrote %s' % out)


if __name__ == '__main__':
    main()
