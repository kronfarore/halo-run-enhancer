r"""AI firing profiles for PORTED weapons (2026-10-02).

A Halo 1 actor variant's firing behaviour (actv 0x74-0x15F, 0x1D8-0x1E3) is copied
from the most similar character that already carries the weapon (h1_enemy_weapons).
A PORTED weapon has no such character in Halo 1, so its values come from the game it
was ported FROM: there the shared AI base ai\generic usually lists every weapon's
firing data (Halo 4: Weapons Properties +0x204/0xCC, Weapon ref +0x4; Firing Pattern
Properties +0x210/0x1C, Weapon ref +0x0, Firing Patterns +0x10/0x40 -- two patterns,
the start and the end of a burst series, AVERAGED here because Halo 1 has one).

Fields are matched by NAME between the source char plugin and the Halo 1 actv plugin
(23 of them line up), plus two renames (Maximum Firing Range -> Maximum Firing
Distance, Normal Combat Range -> Desired Combat Range). Raw values are copied: both
engines store floats and radians alike. Halo 1-only fields (new-target / moving /
berserk modifiers, damage per second) and every field the source leaves at 0 are left to
the base donor h1_enemy_weapons picks by animation label.

Output: ai_firing_profiles.json (tool dir): {game: {weapon path: {'source': ...,
'fields': {hex offset: [struct fmt, value]}}}}.

    python ai_firing_profile.py --from-map ..\..\halo4\maps\m020.map --from-game "Halo 4" ^
        --from-weapon "objects\weapons\rifle\storm_lmg\storm_lmg" --to-weapon "weapons\saw\saw"
"""
import argparse
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_patch as hp  # noqa: E402

PROFILE_FILE = os.path.join(ROOT, 'ai_firing_profiles.json')
FMT = {'float32': '<f', 'degree': '<f', 'int16': '<h', 'enum16': '<H'}
RENAMES = {'Maximum Firing Range': 'Maximum Firing Distance',
           'Normal Combat Range': 'Desired Combat Range',
           'Normal Combat Range Max': 'Desired Combat Range Max'}
# source layouts: (props block, elem, weapon ref) and (patterns block, elem, weapon ref,
# inner Firing Patterns block, elem)
SOURCES = {'Halo 4': {'props': (0x204, 0xCC, 0x4), 'pattern': (0x210, 0x1C, 0x0, 0x10, 0x40)}}


def _plugins():
    import halo_enhancer as he
    c = he.CONFIG
    reg = lambda g: hp.PluginRegistry(c.get('assembly_plugins_dir'), c.get('plugin_subdirs_by_game', {}).get(g))
    return reg


def build(from_map, from_game, from_weapon, to_weapon, to_game='Halo 1', char='ai\\generic'):
    reg = _plugins()
    src_pl, dst_pl = reg(from_game).get('char'), reg(to_game).get('actv')
    lay = SOURCES[from_game]
    m = hp.open_map(from_map, from_game)
    base = dict(m.find_tags('char', char)).get(char)
    if base is None:
        raise SystemExit('no %s in %s' % (char, from_map))

    def elem(off, esz, ref):
        n = m.i32(base + off)
        b = hp._block_base(m, base + off) if n > 0 else None
        for i in range(max(0, n)):
            if hp._tag_name_by_id(m, m.u32(b + i * esz + ref + 0xC)) == from_weapon:
                return b + i * esz, i
        return None, None

    pe, pi = elem(*lay['props'])
    fe, fi = elem(*lay['pattern'][:3])
    if pe is None and fe is None:
        raise SystemExit('%s has no entry for %s' % (char, from_weapon))
    values = {}                                      # source field name -> value
    for f in src_pl.fields:
        fmt = FMT.get(f['type'])
        if not fmt:
            continue
        chain = f['block_chain']
        if chain == ['Weapons Properties'] and pe is not None:
            values[f['name']] = struct.unpack_from(fmt, m.data, pe + f['offset'])[0]
        elif chain == ['Firing Pattern Properties', 'Firing Patterns'] and fe is not None:
            ioff, iesz = lay['pattern'][3:]
            n = m.i32(fe + ioff)
            ib = hp._block_base(m, fe + ioff) if n > 0 else None
            vals = [struct.unpack_from(fmt, m.data, ib + k * iesz + f['offset'])[0] for k in range(max(0, n))]
            if vals:
                values[f['name']] = sum(vals) / len(vals)
    fields = {}
    for f in dst_pl.fields:
        if f['block_chain'] or not (0x74 <= f['offset'] < 0x160 or 0x1D8 <= f['offset'] < 0x1E4):
            continue
        src = next((s for s, d in RENAMES.items() if d == f['name']), f['name'])
        if src in values and f['type'] in FMT:
            v = values[src]
            # Halo 4 writes 0 for 'not set -- use the weapon's own value' (its SAW's Rate
            # Of Fire is 0); in Halo 1 a 0 rate never fires. The base donor keeps those.
            if not v:
                continue
            if FMT[f['type']] in ('<h', '<H'):
                v = int(round(v))
            fields['0x%X' % f['offset']] = [FMT[f['type']], v, f['name']]
    try:
        with open(PROFILE_FILE, encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception:
        data = {}
    data.setdefault(to_game, {})[to_weapon] = {
        'source': '%s %s %s (weapon properties #%s, firing pattern #%s)' % (
            from_game, char, from_weapon, pi, fi),
        'fields': fields}
    with open(PROFILE_FILE, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1)
    return data[to_game][to_weapon]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from-map', required=True)
    ap.add_argument('--from-game', default='Halo 4')
    ap.add_argument('--from-weapon', required=True)
    ap.add_argument('--to-weapon', required=True)
    ap.add_argument('--to-game', default='Halo 1')
    ap.add_argument('--char', default='ai\\generic')
    a = ap.parse_args()
    prof = build(a.from_map, a.from_game, a.from_weapon, a.to_weapon, a.to_game, a.char)
    print(prof['source'])
    for off, (fmt, v, name) in sorted(prof['fields'].items(), key=lambda kv: int(kv[0], 16)):
        print('  %-6s %-32s %s' % (off, name, round(v, 4) if isinstance(v, float) else v))
    print('written', PROFILE_FILE)


if __name__ == '__main__':
    main()
