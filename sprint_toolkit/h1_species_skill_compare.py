r"""Halo 1's stock FIRING fields per species, beside a port's Armed profile and what THE SPECIES SKILL
RULE (h1_enemy_weapons.species_skill_rule, user 2026-10-14) makes of each slot (C1 Storm Rifle,
promoted from the scratchpad). Read-only.

Columns: the stock carrier variants (actv 0x74-0x15F, 0x1D8-0x1E3 + the Weapon Damage Modifier)
on a Halo 1 map, then the port's profile fields; below, per variant, the skill ratios the rule
applies against the donor (the profile's donor_variant, or --donor).

    python h1_species_skill_compare.py "weapons\storm rifle\storm rifle"
    python h1_species_skill_compare.py "weapons\smg\smg" --donor "characters\marine\marine assault rifle major" --map a30.map

Halo 3 / ODST / Reach / Halo 4 sources: ai_firing_profile reads ai\generic only -- the species
char tags there carry no weapon entries of their own (checked for the Storm Rifle on m020).
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai_firing_profile as af   # noqa: E402

B = '\\'
VARIANTS = ['characters\\grunt\\grunt minor plasma pistol', 'characters\\grunt\\grunt major plasma pistol',
            'characters\\grunt\\grunt minor needler',
            'characters\\jackal\\jackal minor plasma pistol', 'characters\\jackal\\jackal major plasma pistol',
            'characters\\elite\\elite minor\\elite minor plasma rifle',
            'characters\\elite\\elite major\\elite major plasma rifle',
            'characters\\elite\\elite minor\\elite minor needler']


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('weapon', help='the port weapon tag (ai_firing_profiles.json key)')
    ap.add_argument('--map', default='b30.map', help='a Halo 1 map under halo1\\maps')
    ap.add_argument('--donor', help='the donor variant (default: the profile donor_variant)')
    a = ap.parse_args()
    sys.path.insert(0, af.ROOT)
    import h1_enemy_weapons as ew
    m = af.hp.open_map(os.path.join(af.MCC, 'halo1', 'maps', a.map), 'Halo 1')
    pl = af._plugins()('Halo 1').get('actv')
    fields = sorted((f for f in pl.fields if not f['block_chain'] and f['type'] in af.FMT
                     and (0x74 <= f['offset'] < 0x160 or 0x1D8 <= f['offset'] < 0x1E4)),
                    key=lambda f: f['offset'])
    prof = json.load(open(af.PROFILE_FILE, encoding='utf-8'))['Halo 1'].get(a.weapon) or {}
    donor = a.donor or prof.get('donor_variant')
    cols = []
    for v in VARIANTS + ([donor] if donor and donor not in VARIANTS else []):
        hit = dict(m.find_tags('actv', v)).get(v)
        if hit is None:
            print('(not on %s: %s)' % (a.map, v))
        else:
            cols.append((v, hit))
    fv = lambda x: ('%.4g' % x) if isinstance(x, float) else str(x)
    print('%-34s' % 'field', ''.join('%-13s' % c[0].rsplit(B, 1)[-1][:12] for c in cols), 'PROFILE')
    for f in fields:
        fmt = af.FMT[f['type']]
        vals = [struct.unpack_from(fmt, m.data, base + f['offset'])[0] for _, base in cols]
        pv = (prof.get('fields') or {}).get('0x%X' % f['offset'], [None, ''])[1]
        if len({fv(x) for x in vals}) == 1 and pv == '':
            continue
        print('%-6s%-28s' % ('0x%X' % f['offset'], f['name'][:27]),
              ''.join('%-13s' % fv(x) for x in vals), fv(pv) if pv != '' else '')
    dbase = dict(cols).get(donor)
    if dbase is None:
        print('\nno donor variant (a per-slot similarity donor): pass --donor to see the ratios')
        return
    print('\nTHE SPECIES SKILL RULE against the donor %s (tracking / leading capped at 1):' % donor.rsplit(B, 1)[-1])
    for v, base in cols:
        if v == donor:
            continue
        parts = []
        for offs, label in ew.SPECIES_SKILL:
            s = sum(struct.unpack_from('<f', m.data, base + o)[0] for o in offs)
            d = sum(struct.unpack_from('<f', m.data, dbase + o)[0] for o in offs)
            if s > 0 and d > 0 and abs(s - d) > 1e-9:
                parts.append('%s x%.2f' % (label, s / d))
        print('  %-34s %s' % (v.rsplit(B, 1)[-1], ', '.join(parts) or 'unchanged'))


if __name__ == '__main__':
    main()
