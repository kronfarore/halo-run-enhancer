r"""Make a Halo 2 port RESIDENT in every campaign level -- a weapons-PALETTE entry in each level's
`scenario_weapons_resource` -- and check residency on built maps (H2_PORT_PLAN.md 0.1).

WHY THE PALETTE ONLY (phase 0, 2026-10-20): Halo 2 splits placements out of the scenario into
resource tags that tool STOMPS the scenario with, so the weapons resource is the authority
(memory halo2-loose-tag-format). tool caps WEAPON PLACEMENTS at 128 a scenario
(MAXIMUM_WEAPON_DATUMS_PER_SCENARIO in tool.exe's block definition; palette max 256), and
01b_spacestation already ships 128 -- so Halo 1's "palette entry + one resident-only placement"
cannot give 20 more ports a placement there (06a has 121, 04a 109). A palette entry with NO
placement was proved to build the weapon in (h2_size_test_map.py, 07a, 21 stand-ins: see the
plan). The enhancer only needs the TAG resident: _h2_palette appends its own cache palette entry
for any resident weapon (halo_patch._h2_place_at_markers).

Weapons resource layout (decoded 2026-10-20 on all 13 levels): root 0x4C; names 0x00 (0x24),
0x18 (0x54), PALETTE 0x24 (elem 0x30 = weap tagref + 32 zero bytes), PLACEMENTS 0x30 (elem 0x54:
palette index @0, name @2, flags @4 -- 0x101 = not placed automatically + at rest).

    python h2_port_residency.py <key> [--levels all|03a,07a] [--write]   add the palette entry
    python h2_port_residency.py --show [--levels ...]                     palettes + placement counts
    python h2_port_residency.py --check <maps dir> [--keys k1,k2]         each port's weapon tag in
                                                                          each built <level>.map
Writes keep `<resource>.before_residency` (first write only). H2 kit lock held.
"""
import argparse
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import h2_loosetag as L  # noqa: E402
import ports_h2  # noqa: E402

H2EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
TAGS = os.path.join(H2EK, 'tags')
W_PALETTE, W_PES = 0x24, 0x30
W_PLACE, W_IES = 0x30, 0x54
PLACEMENT_CAP = 128           # tool.exe: MAXIMUM_WEAPON_DATUMS_PER_SCENARIO
PALETTE_CAP = 256


def resource(level):
    return os.path.join(TAGS, 'scenarios', 'solo', level, 'resources',
                        level + '.scenario_weapons_resource')


def levels_arg(s):
    if not s or s == 'all':
        return list(ports_h2.LEVELS)
    short = {l[:3]: l for l in ports_h2.LEVELS}
    return [short.get(x.strip(), x.strip()) for x in s.split(',') if x.strip()]


def scenario(level):
    return os.path.join(TAGS, 'scenarios', 'solo', level, level + '.scenario')


def weapon_palette(data, in_scenario=False):
    """(chunk offset, [paths]) of a weapons resource's palette -- or, `in_scenario`, of the
    SCENARIO's own copy of it. tool stomps that copy with the resource at build time, but it
    LOADS every tag the copy names first: a weapon left there is built in anyway (the old SAW
    port's entry put the reworked SAW into all 13 shipping builds, 2026-10-24). The scenario's
    copy is the one chunk of 0x30-byte elements that are all weap tagrefs (all 13 levels)."""
    if in_scenario:
        hits = [(c, cnt) for c, _v, cnt, es in L.chunks(data)
                if es == W_PES and cnt and all(bytes(data[c + 16 + i * W_PES:c + 20 + i * W_PES])
                                               == b'paew' for i in range(cnt))]
        if not hits:
            return None, []
    else:
        n = L.root_count(data, W_PALETTE)
        hits = [(c, cnt) for c, _v, cnt, es in L.chunks(data)
                if cnt == n and es == W_PES and bytes(data[c + 16:c + 20]) == b'paew']
    if len(hits) != 1:
        raise SystemExit('weapons palette: %d candidate chunks' % len(hits))
    c, n = hits[0]
    pool, out = c + 16 + n * W_PES, []
    for i in range(n):
        ln = struct.unpack_from('<I', data, c + 16 + i * W_PES + 8)[0]
        out.append(bytes(data[pool:pool + ln]).decode('latin-1') if ln else '')
        pool += ln + 1 if ln else 0
    return c, out


def placement_count(data):
    return L.root_count(data, W_PLACE)


def add_palette(data, path):
    """Append `path` to the palette (no placement). Returns its index (existing or new)."""
    c, have = weapon_palette(data)
    if path in have:
        return have.index(path), False
    if len(have) >= PALETTE_CAP:
        raise SystemExit('weapons palette at its cap (%d)' % PALETTE_CAP)
    idx = L.insert_element(data, W_PALETTE, W_PES, L.make_palette(path, b'weap'), paths=(path,),
                           tagref_offsets=(0x0,), chunk=c)
    return idx, True


def set_palette_path(data, index, new, in_scenario=False):
    """Rename palette entry `index` in place (its tagref length + its pooled string). Indices,
    placements and names are untouched -- used to NEUTRALISE a port's entry for a build."""
    c, have = weapon_palette(data, in_scenario)
    n = len(have)
    pool = c + 16 + n * W_PES
    for i in range(index):
        pool += len(have[i]) + 1 if have[i] else 0
    old = have[index]
    if not old:
        raise SystemExit('palette entry %d is empty' % index)
    struct.pack_into('<I', data, c + 16 + index * W_PES + 8, len(new))
    data[pool:pool + len(old) + 1] = new.encode('latin-1') + b'\0'
    _c, after = weapon_palette(data, in_scenario)
    assert after[index] == new and after[:index] == have[:index] and after[index + 1:] == have[index + 1:]


def neutralise(data, paths, stand_in=None, in_scenario=False):
    """Every palette entry naming one of `paths` renamed to `stand_in` (default: the palette's
    first entry, a stock weapon the level carries anyway) -> those weapons are not built in.
    `in_scenario`: the scenario tag's own copy of the palette -- neutralise BOTH, or the
    weapon is still built in (weapon_palette). Returns [(index, old path)] for a report."""
    _c, have = weapon_palette(data, in_scenario)
    if not have:
        return []
    stand_in = stand_in or next(p for p in have if p and p not in paths)
    done = []
    for i, p in enumerate(have):
        if p in paths:
            set_palette_path(data, i, stand_in, in_scenario)
            done.append((i, p))
    return done


# Stock Halo 2 weapons, for neutralise_refs' same-length stand-ins.
STOCK_WEAPONS = (
    'objects\\weapons\\rifle\\smg\\smg',
    'objects\\weapons\\rifle\\shotgun\\shotgun',
    'objects\\weapons\\rifle\\plasma_rifle\\plasma_rifle',
    'objects\\weapons\\rifle\\battle_rifle\\battle_rifle',
    'objects\\weapons\\rifle\\sniper_rifle\\sniper_rifle',
    'objects\\weapons\\rifle\\smg_silenced\\smg_silenced',
    'objects\\weapons\\rifle\\beam_rifle\\beam_rifle',
    'objects\\weapons\\rifle\\covenant_carbine\\covenant_carbine',
    'objects\\weapons\\rifle\\brute_plasma_rifle\\brute_plasma_rifle',
    'objects\\weapons\\pistol\\magnum\\magnum',
    'objects\\weapons\\pistol\\needler\\needler',
    'objects\\weapons\\pistol\\plasma_pistol\\plasma_pistol',
    'objects\\weapons\\support_high\\rocket_launcher\\rocket_launcher',
    'objects\\weapons\\support_low\\brute_shot\\brute_shot',
    'objects\\weapons\\support_high\\flak_cannon\\flak_cannon',
    'objects\\weapons\\melee\\energy_blade\\energy_blade',
)
_PATH_CHARS = set(b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_\\ -.')


def neutralise_refs(data, paths):
    """Any OTHER pooled reference to one of `paths` (a level's AI resource weapon list,
    ai\\generic.character's weapon properties -- tool builds in every tag a kit tag names)
    rewritten in place to a stock weapon path of the SAME length, so no tagref length field has
    to move. Returns ([renamed old paths], [paths with no same-length stand-in]): the caller
    must not ship a build that still names the latter (h2_rebuild_all's check fails it)."""
    done, stuck = [], []
    for p in paths:
        old = p.encode('latin-1') + b'\0'
        new = next((s for s in STOCK_WEAPONS if len(s) == len(p)), None)
        i, hit = data.find(old), False
        while i >= 0:
            if i == 0 or data[i - 1] not in _PATH_CHARS:      # a whole pooled string
                if new is None:
                    stuck.append(p)
                    break
                data[i:i + len(old)] = new.encode('latin-1') + b'\0'
                hit = True
            i = data.find(old, i + 1)
        if hit:
            done.append(p)
    return done, sorted(set(stuck))


def ai_resources(level):
    d = os.path.join(TAGS, 'scenarios', 'solo', level, 'ai_resources')
    return [os.path.join(d, f) for f in sorted(os.listdir(d))
            if f.endswith('.scenario_ai_resource')] if os.path.isdir(d) else []


GENERIC_CHARACTER = os.path.join(TAGS, 'ai', 'generic.character')


def weapon_path(p):
    """A config's weapon tag path (no extension)."""
    w = (p.get('weapon') or {}).get('weapon')
    if w:
        return os.path.splitext(w)[0]
    r = p['reservations']
    return r['weapon_dir'] + '\\' + os.path.basename(r['weapon_dir'])


def show(levels):
    for lvl in levels:
        d = bytearray(open(resource(lvl), 'rb').read())
        _c, pal = weapon_palette(d)
        ports = [k for k, p in ports_h2.all_ports() if weapon_path(p) in pal]
        print('%-20s palette %3d/%d  placements %3d/%d  ports: %s'
              % (lvl, len(pal), PALETTE_CAP, placement_count(d), PLACEMENT_CAP, ', '.join(ports) or '-'))


def write(key, levels, write):
    import kit_lock
    p = ports_h2.load(key)
    path = weapon_path(p)
    if not os.path.exists(os.path.join(TAGS, path + '.weapon')):
        print('NOTE: %s.weapon is not in the kit yet' % path)
    with kit_lock.held('h2_port_residency %s' % key, owner=key, kit='h2'):
        for lvl in levels:
            res = resource(lvl)
            d = bytearray(open(res, 'rb').read())
            idx, new = add_palette(d, path)
            if not new:
                print('   %-20s already in the palette (#%d)' % (lvl, idx))
                continue
            if write:
                if not os.path.exists(res + '.before_residency'):
                    shutil.copy2(res, res + '.before_residency')
                open(res, 'wb').write(bytes(d))
            print('   %-20s %s palette entry #%d' % (lvl, 'added' if write else 'would add', idx))
    if not write:
        print('(dry run -- pass --write)')


def check(maps_dir, keys=None):
    import halo_patch
    ports = [(k, p) for k, p in ports_h2.all_ports() if (not keys or k in keys)]
    missing = 0
    for lvl in ports_h2.LEVELS:
        mp = os.path.join(maps_dir, lvl + '.map')
        if not os.path.exists(mp):
            print('%-20s (no map)' % lvl)
            continue
        m = halo_patch.open_map(mp, 'Halo 2')
        weaps = {t.get('name') for t in m.tags if t.get('class') == 'weap'}
        miss = [k for k, p in ports if weapon_path(p) not in weaps]
        missing += len(miss)
        print('%-20s %d of %d resident%s' % (lvl, len(ports) - len(miss), len(ports),
                                              ('  MISSING: ' + ', '.join(miss)) if miss else ''))
    return missing


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key', nargs='?')
    ap.add_argument('--levels', default='all')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--show', action='store_true')
    ap.add_argument('--check')
    ap.add_argument('--keys', default='')
    a = ap.parse_args()
    if a.show:
        show(levels_arg(a.levels))
    elif a.check:
        sys.exit(1 if check(a.check, [k for k in a.keys.split(',') if k]) else 0)
    elif a.key:
        write(a.key, levels_arg(a.levels), a.write)
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
