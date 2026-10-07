r"""weapon_ports_catalog.json entries for Halo 1's ports and restored weapons, from their
configs (ports_h1/<weapon>.py, section 'catalog') -- the restored writer generalized
(H1_PORT_PLAN.md phase 0, deliverable 5).

A config's catalog section:

    'catalog': {
        'renamed_from': ('Old Name',),      # optional: entries under an old name are dropped
        'entry': {                          # written as given, plus what is derived below
            'weapon': <halo.json name>, 'source': 'Halo 3', 'donor': <H1 card donor>,
            'default_on': False, 'desc': ..., 'balance_desc': ..., 'anims': {},
            'balance': [row(...), ...],     # ports_h1._common.row, Assembly Halo1 units
        }}

Derived for a PORT (source is not 'Halo 1') when the entry does not name them, from the
config's 'pickable' section:
    weap           the weapon tag (weap_path; the enhancer reads it)
    fp_animations  the FP animation tag
    requires       ['proj <own projectile>'] -- the port counts as present on a level only
                   when its weap AND these tags are in the map (the enhancer's rule, cb8413d)

THE MERGE keeps every key the enhancer session owns: an existing entry's keys survive and
keep their place (tag_map, card_map, skip_cards, ammo, anim_sounds, ...); the entry's own
keys overwrite theirs. Do not emit a key the enhancer owns.

Checks before writing: a non-empty 'balance' needs a 'balance_desc'; every row names a
field and an original; 'donor' names a weapon halo.json knows.

    python make_port_catalog_h1_ports.py                 # every configured weapon
    python make_port_catalog_h1_ports.py smg             # one (config key)
    python make_port_catalog_h1_ports.py --dry smg       # print, write nothing
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ports_h1  # noqa: E402

TOOL = os.path.dirname(HERE)
OUT = os.path.join(TOOL, 'weapon_ports_catalog.json')
HALO_JSON = os.path.join(TOOL, 'halo.json')


def own_projectile(p):
    """The projectile only the player build carries, from the 'pickable' section."""
    w = p.get('pickable') or {}
    for k in ('beam', 'bullet'):
        if k in w:
            return w[k]['projectile'][1]
    if 'own_projectile' in w:
        return w['own_projectile']['projectile'][1]
    if 'lunge' in w:
        return w['lunge']['strike']
    return w.get('projectile')


def entry_for(key, p):
    e = dict(p['catalog']['entry'])
    if e.get('weapon') != p['name']:
        raise SystemExit('%s: catalog weapon %r is not the config name %r'
                         % (key, e.get('weapon'), p['name']))
    w = p.get('pickable') or {}
    if p['source'] != 'Halo 1':
        if 'weap' not in e and w.get('weapon'):
            e['weap'] = w['weapon']
        if 'fp_animations' not in e and w.get('fp_anims'):
            e['fp_animations'] = w['fp_anims']
        if 'requires' not in e and own_projectile(p):
            e['requires'] = ['proj ' + own_projectile(p)]
    return e


def check(key, e, known):
    problems = []
    if e.get('balance') and not e.get('balance_desc'):
        problems.append('balance rows but no balance_desc')
    for r in e.get('balance', []):
        if not r.get('field') or r.get('original') is None:
            problems.append('row without field/original: %r' % (r,))
    if e.get('donor') and e['donor'] not in known:
        problems.append('donor %r is not a halo.json weapon' % e['donor'])
    if problems:
        raise SystemExit('%s: %s' % (key, '; '.join(problems)))


def main(only=None, dry=False):
    known = set(json.load(open(HALO_JSON, encoding='utf-8'))['Player Modifiers']
                ['Specific Weapon Modifier'])
    cat = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    h1 = cat.setdefault('Halo 1', [])
    for key, p in ports_h1.all_ports():
        if p.get('catalog') is None or (only and key not in only):
            continue
        entry = entry_for(key, p)
        check(key, entry, known)
        renamed = p['catalog'].get('renamed_from', ())
        h1[:] = [e for e in h1 if e.get('weapon') not in renamed]    # entries under an old name
        old = next((e for e in h1 if e.get('weapon') == entry['weapon']), {})
        merged = dict(old, **entry)              # keep what other tools added (e.g. 'ammo')
        h1[:] = [e for e in h1 if e.get('weapon') != entry['weapon']] + [merged]
        kept = sorted(set(old) - set(entry))
        print('Halo 1 / %-12s %d balance row(s), requires %s%s'
              % (entry['weapon'], len(entry.get('balance', [])), entry.get('requires'),
                 ('  (kept: %s)' % ', '.join(kept)) if kept and dry else ''))
        if dry:
            print(json.dumps(merged, indent=1)[:3000])
    if dry:
        print('(dry run: nothing written)')
        return
    json.dump(cat, open(OUT, 'w', encoding='utf-8'), indent=1)
    print('wrote %s' % OUT)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('weapons', nargs='*', help='config keys (default: every configured one)')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    main(a.weapons or None, a.dry)
