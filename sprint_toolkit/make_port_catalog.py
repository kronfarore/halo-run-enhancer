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
# the magazine sizes the SAW's tick sheets are drawn for, in sequence order (saw_build.py
# runs `ammo_meter.py 72 135`), and its HUD's low-ammo flash at the port's own 72
METER_SIZES = [72, 135]
LOADED_CUTOFF = 12


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
    # THE AMMO METER follows the balanced magazine (2026-10-04, user: "revisit the Ammo
    # meter for H1 in the balanced state"). A tick sheet only fits the magazine it was drawn
    # for, so ammo_meter.py builds one per size into the same tags (saw_build.py: 72 = the
    # port's own, sequence 0; the balanced 135 = sequence 1) -- but nothing switched to it,
    # and at 135 rounds the 72-tick art (multiplier 3) stayed FULL for the first 63 shots.
    # These rows point the loaded-ammo meter + its silhouettes at the balanced sheet, with
    # that sheet's multiplier, and scale the low-ammo flash.
    if bal_mag:
        import ammo_meter
        hud = 'weapons' + B + 'saw' + B + 'saw'
        seq = METER_SIZES.index(int(round(bal_mag)))
        per_tick, _ticks, _step, mult = ammo_meter.plan(int(round(bal_mag)))
        for field, block, value, original in (
                ('Sequence Index', 'Meter Elements', seq, 0),
                ('Alpha Multiplier', 'Meter Elements', mult, ammo_meter.step(METER_SIZES[0])),
                # a tick covers `per_tick` rounds and stays lit while ANY of them is left:
                # lit while threshold < rounds * mult + bias, thresholds per_tick apart ->
                # bias = per_tick (with bias 1 the 135 sheet showed 67 of 68 ticks full and
                # nothing on the last round -- simulated on the built map)
                ('Alpha Bias', 'Meter Elements', per_tick, 1),
                ('Sequence Index', 'Static Elements', seq, 0),
                ('Loaded Ammo Cutoff', None, int(round(LOADED_CUTOFF * bal_mag / METER_SIZES[0])),
                 LOADED_CUTOFF)):
            rows.append({'class': 'wphi', 'tag': hud, 'field': field, 'block': block,
                         'index': 0, 'value': value, 'card': 'Ammo display',
                         'original': original})
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
    # keep what other tools added to the entry (e.g. 'ammo', the pickup choices)
    old = next((e for e in cat[t['target']] if e.get('weapon') == entry['weapon']), {})
    entry = dict(old, **entry)
    cat[t['target']] = [e for e in cat[t['target']] if e.get('weapon') != entry['weapon']] + [entry]
    json.dump(cat, open(OUT, 'w', encoding='utf-8'), indent=1)
    print('wrote %s: %s -> %s, %d balance field(s), anims %s'
          % (OUT, entry['weapon'], t['target'], len(rows), entry['anims']))


if __name__ == '__main__':
    main()
