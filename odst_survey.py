r"""Report what each Halo 3: ODST map ACTUALLY places — characters, weapons and
equipment — so halo.json's per-mission lists can be derived instead of guessed.

Why this exists: the ODST mission entries were seeded by copying Halo 3's, which
gave every ODST level Flood, Sentinel Beams and Battle Rifles it never contains.
Correcting that from memory would just be a different guess.

Why the raw tag list is NOT the answer: an ODST map carries thousands of tags it
never places. sc100 (Tayari Plaza) ships Flood, Elite and Hunter character tags.
The scenario's PALETTES, and specifically the palette entries its squads point at,
are the real signal — the same distinction the project already relies on for
CHIEFTAIN_MISSIONS and EQUIPMENT_CARRIER_MISSIONS.

Why it does not reuse halo_patch's Halo 3 layout: ODST is a later build and the
scenario blocks moved (Squads 0x384 -> 0x3B8, Character Palette 0x3A8 -> 0x3E8),
and its squads hold Single Locations / Designer Cells / Templated Cells rather
than H3's Fire-Teams. Offsets are read from the Assembly ODSTMCC scnr plugin at
run time, so this stays correct if the plugin is updated.

    python odst_survey.py                 # every level
    python odst_survey.py sc100 h100      # named levels
    python odst_survey.py --json          # machine-readable, for halo.json edits
"""
import argparse
import collections
import json
import os
import struct
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MCC = (r"C:\Program Files (x86)\Steam\steamapps\common"
       r"\Halo The Master Chief Collection")
MAPS = os.path.join(MCC, 'halo3odst', 'maps')
PLUGIN = (r"C:\Program Files (x86)\Steam\steamapps\common\HCEEK"
          r"\Assembly-1-2023-11-29-1702446457\Plugins\ODSTMCC\scnr.xml")

# Story order. ODST mission ids do NOT sort into it — c200 (Coastal Highway, late)
# would land second — so the order is explicit here and in halo.json.
LEVELS = ['c100', 'h100', 'sc100', 'sc110', 'sc120', 'sc130', 'sc140', 'sc150',
          'l200', 'c200', 'l300']

BLOCKS = ('reflexive', 'tagblock', 'block', 'struct')


def _int(s):
    return int(s, 16) if isinstance(s, str) and s.lower().startswith('0x') else int(s)


def plugin_layout(path=PLUGIN):
    """Block offsets straight from the Assembly plugin, so nothing is hardcoded."""
    root = ET.parse(path).getroot()
    lay = {}
    for n in root:
        nm = (n.get('name') or '').strip()
        if n.tag.lower() in BLOCKS and nm:
            lay[nm] = (_int(n.get('offset')),
                       _int(n.get('entrySize') or n.get('elementSize') or 0))
    squads = next((n for n in root.iter()
                   if n.tag.lower() in BLOCKS
                   and (n.get('name') or '').strip().lower() == 'squads'), None)
    sub = {}
    if squads is not None:
        for c in squads:
            nm = (c.get('name') or '').strip()
            if c.tag.lower() in BLOCKS and nm:
                sub[nm] = (_int(c.get('offset')),
                           _int(c.get('entrySize') or c.get('elementSize') or 0))
    lay['_squad_sub'] = sub
    return lay


def palette_names(m, base, off, esize, id_at=0xC):
    import halo_patch as HP
    out = []
    for el in m.follow_all(base, [off], [esize], 'all'):
        ident = struct.unpack_from('<I', m.data, el + id_at)[0]
        out.append(HP._tag_name_by_id(m, ident) if ident != 0xFFFFFFFF else None)
    return out


def survey(level, lay):
    from halo3_map import Halo3Map
    import halo_patch as HP
    path = os.path.join(MAPS, level + '.map')
    if not os.path.exists(path):
        return None
    m = Halo3Map(path)
    scnr = HP._scnr_base(m)

    chars = palette_names(m, scnr, *lay['Character Palette'])
    weaps = palette_names(m, scnr, *lay['Weapon Palette'])
    equip = palette_names(m, scnr, *lay['Equipment Palette'])

    sq_off, sq_size = lay['Squads']
    sub = lay['_squad_sub']
    # COUNT placements, do not merely record presence. sc100 lists three
    # floodcombat characters -- 4 placements against 1400+ for the real enemies --
    # which are vestigial and would otherwise put Flood back into ODST, the exact
    # error the copied Halo 3 entries already made.
    used_c, used_w = collections.Counter(), collections.Counter()

    def note(pal, idx, sink):
        if 0 <= idx < len(pal) and pal[idx]:
            sink[pal[idx]] += 1

    for sq in m.follow_all(scnr, [sq_off], [sq_size], 'all'):
        # Single Locations: a plain index into the character palette
        if 'Single Locations' in sub:
            o, e = sub['Single Locations']
            for sl in m.follow_all(sq, [o], [e], 'all'):
                note(chars, struct.unpack_from('<h', m.data, sl + 0x32)[0], used_c)
                note(weaps, struct.unpack_from('<h', m.data, sl + 0x34)[0], used_w)
        # Designer / Templated Cells: a weighted list of character choices. Chance
        # is at 0xE; every entry observed so far has chance > 0, so the count is
        # what separates a real spawn from a leftover, not the chance.
        for cell in ('Designer Cells', 'Templated Cells'):
            if cell not in sub:
                continue
            o, e = sub[cell]
            for dc in m.follow_all(sq, [o], [e], 'all'):
                for ct in m.follow_all(dc, [0x14], [0x10], 'all'):
                    if struct.unpack_from('<h', m.data, ct + 0xE)[0] <= 0:
                        continue
                    note(chars, struct.unpack_from('<h', m.data, ct + 0xC)[0], used_c)
                for iw in m.follow_all(dc, [0x20], [0x10], 'all'):
                    note(weaps, struct.unpack_from('<h', m.data, iw + 0xC)[0], used_w)

    # Ground pickups come from the Weapons/Equipment PLACEMENT blocks, each entry
    # holding a palette index at +0. The palettes themselves are useless for this:
    # they are near-identical across all nine maps (every one stocks a golf club,
    # a flamethrower and a missile pod), so they describe the game, not the level.
    def placements(block, palette):
        off, esize = lay[block]
        c = collections.Counter()
        for el in m.follow_all(scnr, [off], [esize], 'all'):
            i = struct.unpack_from('<h', m.data, el)[0]
            if 0 <= i < len(palette) and palette[i]:
                c[palette[i]] += 1
        return c

    weap_ground = placements('Weapons', weaps)
    equip_ground = placements('Equipment', equip)

    fam_counts = collections.Counter()
    for tag, n in used_c.items():
        fam_counts[family(tag)] += n
    return {
        'weapons_on_ground': dict(weap_ground),
        'equipment_on_ground': dict(equip_ground),
        'level': level,
        'internal': m.internal_name,
        'family_counts': dict(fam_counts),
        'characters_placed': dict(used_c),
        'characters_in_palette': sorted(n for n in chars if n),
        'weapons_placed': dict(used_w),
        'weapons_in_palette': sorted(n for n in weaps if n),
        'equipment_in_palette': sorted(n for n in equip if n),
    }


def weapon_carriers(level, lay):
    """weapon tag -> the character families that spawn holding it.

    Needed because a weapon appearing in a loadout is only evidence the player can
    get it if the CARRIER really spawns. sentinel_gun is carried solely by
    floodcombat_elite and energy_blade solely by elite -- both leftovers -- so
    without this they would enter halo.json as ODST weapons.
    """
    from halo3_map import Halo3Map
    import halo_patch as HP
    m = Halo3Map(os.path.join(MAPS, level + '.map'))
    scnr = HP._scnr_base(m)
    chars = palette_names(m, scnr, *lay['Character Palette'])
    weaps = palette_names(m, scnr, *lay['Weapon Palette'])
    sq_off, sq_size = lay['Squads']
    sub = lay['_squad_sub']
    out = collections.defaultdict(set)

    def pair(wi, fams):
        if 0 <= wi < len(weaps) and weaps[wi]:
            out[weaps[wi]] |= fams

    for sq in m.follow_all(scnr, [sq_off], [sq_size], 'all'):
        for cell in ('Designer Cells', 'Templated Cells'):
            if cell not in sub:
                continue
            o, e = sub[cell]
            for dc in m.follow_all(sq, [o], [e], 'all'):
                fams = set()
                for ct in m.follow_all(dc, [0x14], [0x10], 'all'):
                    i = struct.unpack_from('<h', m.data, ct + 0xC)[0]
                    if 0 <= i < len(chars) and chars[i]:
                        fams.add(family(chars[i]))
                for iw in m.follow_all(dc, [0x20], [0x10], 'all'):
                    pair(struct.unpack_from('<h', m.data, iw + 0xC)[0], fams)
        if 'Single Locations' in sub:
            o, e = sub['Single Locations']
            for sl in m.follow_all(sq, [o], [e], 'all'):
                ci = struct.unpack_from('<h', m.data, sl + 0x32)[0]
                if 0 <= ci < len(chars) and chars[ci]:
                    pair(struct.unpack_from('<h', m.data, sl + 0x34)[0],
                         {family(chars[ci])})
    return out


def family(tag):
    """Group a character tag by its species folder, which is what halo.json names."""
    if tag and tag.startswith('objects\\characters\\'):
        return tag.split('\\')[2]
    return (tag or '').split('\\')[0]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('levels', nargs='*', default=None)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--min-placements', type=int, default=5,
                    help='families with fewer placements are reported as leftovers')
    ap.add_argument('--palette', action='store_true',
                    help='also show what the palette offers but nothing places')
    a = ap.parse_args(argv)

    lay = plugin_layout()
    out = []
    for lvl in (a.levels or LEVELS):
        r = survey(lvl, lay)
        if r is None:
            print('%-6s MISSING' % lvl)
            continue
        out.append(r)
        if a.json:
            continue
        fc = r['family_counts']
        keep = {f: n for f, n in fc.items() if n >= a.min_placements}
        drop = {f: n for f, n in fc.items() if n < a.min_placements}
        print('\n=== %-6s (%s) ===' % (lvl, r['internal']))
        print('  families placed (>= %d): %s' % (a.min_placements,
              ', '.join('%s %d' % (f, n)
                        for f, n in sorted(keep.items(), key=lambda kv: -kv[1]))))
        if drop:
            print('  BELOW THRESHOLD (treat as leftovers): %s'
                  % ', '.join('%s %d' % (f, n)
                              for f, n in sorted(drop.items(), key=lambda kv: -kv[1])))
        print('  placed weapons    : %s'
              % (', '.join(sorted({w.rsplit('\\', 1)[-1]
                                   for w in r['weapons_placed']})) or '(none)'))
        print('  equipment palette : %s'
              % (', '.join(sorted({e.rsplit('\\', 1)[-1]
                                   for e in r['equipment_in_palette']})) or '(none)'))
        if a.palette:
            unplaced = sorted({family(c) for c in r['characters_in_palette']}
                              - set(fc))
            print('  in palette but never placed: %s' % (', '.join(unplaced) or '(none)'))
    if a.json:
        print(json.dumps(out, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
