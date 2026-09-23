"""Build weapon_ports_catalog.json (the tool's) from a balance table.

Values stay in the Assembly plugin's units, because the patcher writes them through the
same plugins the cards use. Animation multipliers are relative to what the BUILT map
carries (the port's original timing), so the patcher can scale them in place.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.sep
TABLE = os.path.join(HERE, 'balance_SAW_Halo4_to_Halo1.json')
OUT = os.path.join(TOOL, 'weapon_ports_catalog.json')
# donor tag -> the port's own tag (as cloned by the port build)
PORT_TAGS = {('weap', 'weapons' + B + 'assault rifle' + B + 'assault rifle'): 'weapons' + B + 'saw' + B + 'saw',
             ('proj', 'weapons' + B + 'assault rifle' + B + 'bullet'): 'weapons' + B + 'saw' + B + 'bullet',
             ('jpt!', 'weapons' + B + 'assault rifle' + B + 'bullet'): 'weapons' + B + 'saw' + B + 'bullet',
             ('jpt!', 'weapons' + B + 'assault rifle' + B + 'melee'): 'weapons' + B + 'saw' + B + 'melee'}
# frames in the built map (the port's own timing) -> balanced frames
ANIM = {'reload': (128, 164), 'swap': (35, 34)}


def main():
    t = json.load(open(TABLE, encoding='utf-8'))
    rows = []
    for r in t['rows']:
        key = (r.get('dst_class'), r.get('dst_tag'))
        if key not in PORT_TAGS or r.get('balanced') is None or not r.get('dst_field'):
            continue
        rows.append({'class': key[0], 'tag': PORT_TAGS[key], 'field': r['dst_field'],
                     'block': r.get('dst_block'), 'value': round(float(r['balanced']), 6),
                     'card': r['card'], 'original': r.get('original')})
    # Rounds per ammo pickup is not a card field (weap Magazines/Magazines), but it has
    # to follow the balanced magazine: as many magazines per pickup as the donor gives.
    bal_mag = next((r['balanced'] for r in t['rows']
                    if r.get('dst_field') == 'Rounds Loaded Maximum' and r.get('balanced')), None)
    if bal_mag:
        rows.append({'class': 'weap', 'tag': PORT_TAGS[('weap', 'weapons' + B + 'assault rifle'
                                                        + B + 'assault rifle')],
                     'field': 'Rounds', 'block': 'Magazines/Magazines',
                     'value': int(round(bal_mag * 4)), 'card': 'Ammo pickup',
                     'original': None})
    entry = {'weapon': t['ported'], 'source': t['source'], 'donor': t['donor'],
             'default_on': True,
             'desc': '%s carried from %s, built with its own numbers. The suggested '
                     'balance measures it against the %s, which both games have.'
                     % (t['ported'], t['source'], t['donor']),
             'fp_animations': 'weapons' + B + 'saw' + B + 'fp' + B + 'fp',
             'balance': rows,
             'anims': {k: round(new / float(old), 6) for k, (old, new) in ANIM.items()}}
    cat = {}
    if os.path.exists(OUT):
        cat = json.load(open(OUT, encoding='utf-8'))
    cat.setdefault(t['target'], [])
    cat[t['target']] = [e for e in cat[t['target']] if e.get('weapon') != entry['weapon']] + [entry]
    json.dump(cat, open(OUT, 'w', encoding='utf-8'), indent=1)
    print('wrote %s: %s -> %s, %d balance field(s), anims %s'
          % (OUT, entry['weapon'], t['target'], len(rows), entry['anims']))


if __name__ == '__main__':
    main()
