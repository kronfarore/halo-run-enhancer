r"""Halo 2 enemy count: scale how many actors each enemy squad spawns (2026-10-04).

Halo 2 places min(difficulty count, len(Starting Locations)) actors for `ai_place <squad>`
(see halo_patch._h2_duplicate_squad), so a squad grows by raising BOTH difficulty counts
and, where the new count outruns the locations, adding locations:

  scnr Squads  +0x160 elem 0x74   name ascii +0x0, Vehicle Type Index +0x34,
                                  Character Type Index +0x36,
                                  Normal / Insane Difficulty Count i16 +0x2C / +0x2E
    Starting Locations +0x48 elem 0x64   position xyz +0x0, Character Type Index +0x20
                                         (-1 = the squad's), Vehicle Type Index +0x28
  Character Palette +0x178 elem 0x8, tagRef ident +0x4

A squad mixes species ONLY through starting-location character overrides, so the copies
cycle through the existing locations: a mixed squad keeps its mix. New locations sit
`--spread` units around the location they copy.

Enemy squads only: a squad is an enemy squad when none of its characters is human (by
the character tag's species folder). A location that mans a turret or vehicle (its own
Vehicle Type Index) is never copied -- only on-foot locations are. Squads that ARE
vehicles (squad-level Vehicle Type Index: Ghosts, Phantoms, Spectres, Wraiths) and
squads with count 0 (placed only by script with an explicit count) are left alone and
listed. `--species grunt,elite` limits the scaling to squads FIELDING one of those
species -- a mixed squad counts for each species in it.

Scripts that place with an explicit count -- `(ai_place sq 2)` -- bypass the squad count;
this tool does not touch them (03a has ten such calls).

    python h2_squad_count.py --map <map> --show
    python h2_squad_count.py --map <in> --out <out> --mult 2 [--species grunt] [--shield-mult 3]
"""
import argparse
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import halo2_map as h2  # noqa: E402

SQUADS, SQ_SZ = 0x160, 0x74
NORMAL, INSANE, VEH, CHAR = 0x2C, 0x2E, 0x34, 0x36
LOCS, LOC_SZ, LOC_CHAR, LOC_VEH = 0x48, 0x64, 0x20, 0x28
PALETTE, PAL_SZ, PAL_ID = 0x178, 0x8, 0x4

HUMAN_SPECIES = ('marine', 'masterchief', 'dervish', 'miranda', 'johnson', 'cortana', 'monitor',
                 'odst', 'civilian', 'crewman', 'heretic_human', 'prophet')


def species(name):
    if not name:
        return None
    parts = name.lower().split('\\')
    if 'characters' in parts and parts.index('characters') + 1 < len(parts):
        return parts[parts.index('characters') + 1]
    return parts[-1]


def is_human(sp):
    return any(sp.startswith(h) for h in HUMAN_SPECIES)


def palette(m, s):
    byidx = {t['index']: t for t in m.tags}
    out = []
    for el in m.follow_all(s, [PALETTE], [PAL_SZ], 'all'):
        ident = m.u32(el + PAL_ID)
        t = byidx.get(ident & 0xFFFF) if ident != 0xFFFFFFFF else None
        out.append(t['name'] if t else None)
    return out


def i16(m, o):
    return struct.unpack_from('<h', m.data, o)[0]


def survey(m):
    """[{name, off, normal, insane, locs, species:set, vehicle:bool}] for every squad."""
    s = m.scenario_tag()['base']
    pal = palette(m, s)
    nm = lambda i: pal[i] if 0 <= i < len(pal) else None  # noqa: E731
    out = []
    for sq in m.follow_all(s, [SQUADS], [SQ_SZ], 'all'):
        base = nm(i16(m, sq + CHAR))
        locs = m.follow_all(sq, [LOCS], [LOC_SZ], 'all')
        chars = set()
        veh = i16(m, sq + VEH) >= 0
        foot = 0
        for loc in locs:
            c = i16(m, loc + LOC_CHAR)
            chars.add(nm(c) if c >= 0 else base)
            foot += i16(m, loc + LOC_VEH) < 0
        if not locs:
            chars.add(base)
        chars.discard(None)
        out.append({'name': m.data[sq:sq + 0x20].split(b'\0')[0].decode('ascii', 'replace'),
                    'off': sq, 'normal': i16(m, sq + NORMAL), 'insane': i16(m, sq + INSANE),
                    'locs': len(locs), 'chars': chars,
                    'species': {species(c) for c in chars}, 'vehicle': veh, 'foot': foot})
    return out


def grow(m, sq, mult, spread):
    """Scale one squad's counts by `mult` and add locations up to the new count."""
    off = sq['off']
    new_n = max(1, int(math.ceil(sq['normal'] * mult))) if sq['normal'] > 0 else 0
    new_i = max(1, int(math.ceil(sq['insane'] * mult))) if sq['insane'] > 0 else 0
    need = max(new_n, new_i) - sq['locs']
    added = 0
    if need > 0 and sq['foot'] > 0:
        # copy on-foot locations only: a location manning a turret or vehicle stays unique
        locs = [l for l in m.follow_all(off, [LOCS], [LOC_SZ], 'all') if i16(m, l + LOC_VEH) < 0]
        copies = []
        for k in range(need):
            src = locs[k % len(locs)]
            e = bytearray(m.data[src:src + LOC_SZ])
            x, y, z = struct.unpack_from('<fff', e, 0)
            ring = k // len(locs) + 1
            ang = 2.0 * math.pi * (k % len(locs)) / len(locs) + ring
            struct.pack_into('<fff', e, 0, x + spread * ring * math.cos(ang),
                             y + spread * ring * math.sin(ang), z)
            copies.append(bytes(e))
        m.grow_block(off, LOCS, LOC_SZ, copies)
        added = need
    struct.pack_into('<hh', m.data, off + NORMAL, new_n, new_i)
    return new_n, new_i, added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', required=True)
    ap.add_argument('--out')
    ap.add_argument('--mult', type=float, default=2.0)
    ap.add_argument('--species', help='comma list: only squads fielding one of these')
    ap.add_argument('--spread', type=float, default=0.6, help='world units between copies')
    ap.add_argument('--show', action='store_true')
    ap.add_argument('--shield-mult', type=float)
    a = ap.parse_args()
    m = h2.Halo2Map(a.map)
    want = {x.strip().lower() for x in a.species.split(',')} if a.species else None
    rows = survey(m)
    skipped = {'friendly': [], 'vehicle': [], 'count 0': [], 'no characters': [], 'other species': []}
    todo = []
    for sq in rows:
        if not sq['species']:
            skipped['no characters'].append(sq['name'])
        elif any(is_human(x) for x in sq['species']):
            skipped['friendly'].append(sq['name'])
        elif sq['vehicle']:
            skipped['vehicle'].append(sq['name'])
        elif sq['normal'] <= 0 and sq['insane'] <= 0:
            skipped['count 0'].append(sq['name'])
        elif want and not (sq['species'] & want):
            skipped['other species'].append(sq['name'])
        else:
            todo.append(sq)
    print('%d squads: %d to scale' % (len(rows), len(todo)))
    for k, v in skipped.items():
        if v:
            print('  left alone (%s): %d  %s' % (k, len(v), ', '.join(v[:8]) + (' ...' if len(v) > 8 else '')))
    before = sum(sq['normal'] for sq in todo), sum(sq['insane'] for sq in todo)
    after = [0, 0]
    for sq in todo:
        if a.show:
            print('  %-28s %-24s normal %2d insane %2d locs %2d' % (
                sq['name'], '+'.join(sorted(sq['species'])), sq['normal'], sq['insane'], sq['locs']))
            continue
        n, i, added = grow(m, sq, a.mult, a.spread)
        after[0] += n
        after[1] += i
        print('  %-28s %-24s normal %2d->%2d insane %2d->%2d locs %2d+%d' % (
            sq['name'], '+'.join(sorted(sq['species'])), sq['normal'], n, sq['insane'], i,
            sq['locs'], added))
    if a.show:
        return
    print('actors (scaled squads): normal %d -> %d, insane %d -> %d' % (before[0], after[0], before[1], after[1]))
    if a.shield_mult:
        import halo_map as hm
        import assembly_plugins as apl
        pl = hm.Plugin(os.path.join(apl.plugins_dir(), 'Halo2MCC', 'hlmt.xml'))
        for path in ('objects\\characters\\masterchief\\masterchief',
                     'objects\\characters\\dervish\\dervish'):
            for _p, base in m.find_tags('hlmt', path):
                old = m.read_tag_field(base, 'Maximum Shield Vitality', pl, 'New Damage Info')
                m.write_tag_field(base, 'Maximum Shield Vitality', old * a.shield_mult, pl,
                                  'New Damage Info')
                print('shield %s: %s -> %s' % (path, old,
                      m.read_tag_field(base, 'Maximum Shield Vitality', pl, 'New Damage Info')))
    if not a.out:
        sys.exit('--out is required to write')
    m.save(a.out)
    print('written:', a.out)


if __name__ == '__main__':
    main()
