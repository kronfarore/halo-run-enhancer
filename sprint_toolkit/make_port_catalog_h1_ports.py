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
keep their place (tag_map, card_map, skip_cards, ammo, ...); the entry's own
keys overwrite theirs. Do not emit a key the enhancer owns. `anim_sounds` is PORT data (the
stretched sound a balanced retime swaps in; the SAW's came from make_port_catalog.py, the
SMG's from its config) -- the patcher only reads it.

Checks before writing: a non-empty 'balance' needs a 'balance_desc'; every row names a
field and an original; 'donor' names a weapon halo.json knows.

    python make_port_catalog_h1_ports.py                 # every DONE port
    python make_port_catalog_h1_ports.py smg             # one (config key), any status
    python make_port_catalog_h1_ports.py --dry smg       # print, write nothing
    python make_port_catalog_h1_ports.py smg --commit "msg" [--commit "paragraph"]

PARALLEL SESSIONS (2026-10-13): the file is read under the kit lock and ONLY the named
entries change; every other entry that differs from HEAD (the other session's uncommitted
entry, the enhancer's keys) is printed FOREIGN and kept as read. `--commit` commits just this
run's entries (kit_commit.commit_json: applied to HEAD's JSON) inside the same lock hold -- no
write->commit window, and the foreign edits stay uncommitted.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ports_h1  # noqa: E402
import port_env  # noqa: E402,F401  (Reclaimer, for ammo_block)

B = chr(92)
TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
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


def ammo_block(p, template):
    """The enhancer's AMMO PICKUP dropdown for a port (user, 2026-10-12: 'all of the H1 ports that
    use ammo pickups, apart from the SAW, don't have the ammo pickup swap wired into the
    enhancer'): the SAW's `ammo` block (the Halo 1 pickup choices with the missions that carry
    each, read from the shipped maps) with the port's weapon tag and its BUILT magazine item as
    the default; that item joins the choices when it is no stock ammo powerup (the Grenade
    Launcher's frag grenade). None for a port with no magazine item (battery / melee weapons)."""
    import copy
    from reclaimer.hek.defs.weap import weap_def
    w = (p.get('pickable') or {}).get('weapon')
    if not w or not template:
        return None
    path = os.path.join(TAGS, w + '.weapon')
    if not os.path.exists(path):
        return None
    mags = weap_def.build(filepath=path).data.tagdata.weap_attrs.magazines.STEPTREE
    items = mags[0].magazine_items.STEPTREE if len(mags) else []
    item = items[0].equipment.filepath if len(items) else ''
    if not item:
        return None
    b = copy.deepcopy(template)
    b['tag'], b['default'] = w, item
    if not any(c['tag'].lower() == item.lower() for c in b['choices']):
        b['choices'].append({'tag': item, 'label': item.rsplit(B, 1)[-1].title()})
    return b


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


def merge_into(cat, built):
    """Merge the built entries [(key, p, entry)] into `cat` (the file's JSON) in place and touch
    nothing else: run on the working copy as read under the kit lock, and on HEAD's JSON for a
    --commit. Returns {weapon: names kept from the old entry}."""
    h1 = cat.setdefault('Halo 1', [])
    kept = {}
    for key, p, entry in built:
        renamed = p['catalog'].get('renamed_from', ())
        h1[:] = [e for e in h1 if e.get('weapon') not in renamed]    # entries under an old name
        old = next((e for e in h1 if e.get('weapon') == entry['weapon']), {})
        merged = dict(old, **entry)              # keep what other tools added (e.g. 'ammo')
        if 'ammo' not in merged:                 # the pickup dropdown (ammo_block)
            saw = next((e for e in h1 if e.get('weapon') == 'SAW'), {}).get('ammo')
            blk = ammo_block(p, saw)
            if blk:
                merged['ammo'] = blk
        at = next((i for i, e in enumerate(h1) if e.get('weapon') == entry['weapon']), None)
        if at is None:                           # a new entry goes last; an old one keeps its
            h1.append(merged)                    # place (no reorder churn in the file)
        else:
            h1[at] = merged
        kept[entry['weapon']] = sorted(set(old) - set(entry))
    return kept


def main(only=None, dry=False, commit=None):
    """`only`: config keys; None = every DONE port (2026-10-13: a port in progress is the other
    parallel session's -- name it to write it). `commit`: message paragraphs -> commit THIS run's
    entries only (kit_commit.commit_json), inside the same kit-lock hold as the write."""
    import kit_commit
    known = set(json.load(open(HALO_JSON, encoding='utf-8'))['Player Modifiers']
                ['Specific Weapon Modifier'])
    built, skipped = [], []
    for key, p in ports_h1.all_ports():
        if p.get('catalog') is None or (only and key not in only):
            continue
        if not only and p.get('status') != 'done':
            skipped.append(key)
            continue
        entry = entry_for(key, p)
        check(key, entry, known)
        built.append((key, p, entry))
    if only and len(built) != len(set(only)):
        raise SystemExit('no catalog section for: %s' % ', '.join(
            sorted(set(only) - {k for k, _p, _e in built})))
    if skipped:
        print('not done, left as they are (name one to write it): %s' % ', '.join(skipped))
    # read UNDER THE LOCK (main runs inside kit_lock.script): only the built entries change
    cat = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    as_read = json.loads(json.dumps(cat))
    kept = merge_into(cat, built)
    for key, p, entry in built:
        print('Halo 1 / %-12s %d balance row(s), requires %s%s'
              % (entry['weapon'], len(entry.get('balance', [])), entry.get('requires'),
                 ('  (kept: %s)' % ', '.join(kept[entry['weapon']]))
                 if kept[entry['weapon']] and dry else ''))
        if dry:
            print(json.dumps(next(e for e in cat['Halo 1'] if e.get('weapon') == entry['weapon']),
                             indent=1)[:3000])
    mine = {}
    for key, p, entry in built:
        for name in (entry['weapon'],) + tuple(p['catalog'].get('renamed_from', ())):
            mine[('Halo 1', name)] = None
    kit_commit.report_foreign('catalog', kit_commit.head_json(OUT), as_read, mine)
    if dry:
        print('(dry run: nothing written)')
        return
    json.dump(cat, open(OUT, 'w', encoding='utf-8'), indent=1)
    print('wrote %s' % OUT)
    if commit:
        kit_commit.commit_json(OUT, lambda d: merge_into(d, built), commit)


if __name__ == '__main__':
    import kit_lock   # the shared-kit lock: two port sessions in parallel (H1_PORT_PLAN.md)
    with kit_lock.script('make_port_catalog_h1_ports'):
        ap = argparse.ArgumentParser()
        ap.add_argument('weapons', nargs='*', help='config keys (default: every DONE one)')
        ap.add_argument('--dry', action='store_true')
        ap.add_argument('--commit', action='append', metavar='MSG',
                        help='commit THESE entries only, under the same lock hold (repeatable: '
                             'one message paragraph each)')
        a = ap.parse_args()
        main(a.weapons or None, a.dry, a.commit)
