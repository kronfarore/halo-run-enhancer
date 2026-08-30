r"""zero_then_live.py -- fields a weapon leaves at 0 in one game and USES in the next.

plugin_diff answers "what did this game ADD", which is the wrong question for a whole
class of gap: a field that existed all along, shipped 0 where the card was written, and
became live in a later game. Nothing is new, so the diff never mentions it, and the
card silently does not claim the game where the field finally matters. The Plasma
Pistol's Error Angle is exactly that -- present since Halo 2, zero there, live in Reach,
and its only spread card claims Halo 2/3/ODST.

The field list is taken from halo.json itself: every field any weapon card names. Those
are the fields already understood to be worth tuning, so the question this asks is
"which OTHER weapons should have had this card, in which game" -- a transitional sweep
to close the back catalogue, not a permanent check.

    python sprint_toolkit/zero_then_live.py
    python sprint_toolkit/zero_then_live.py --weapon "Plasma Pistol"
    python sprint_toolkit/zero_then_live.py --field "Error Angle" --all-transitions

Reported by default are only the transitions where the weapon has NO card offering that
field in the later game, i.e. the actionable ones.
"""
import argparse
import collections
import json
import io
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import halo_enhancer as he                                       # noqa: E402
import halo_patch                                                # noqa: E402
import map_vault as V                                            # noqa: E402

S = chr(92)
SUBS = {'Halo 1': ['Halo1MCC', 'Halo1'], 'Halo 2': ['Halo2MCC', 'Halo2'],
        'Halo 3': ['Halo3MCC', 'Halo3'], 'Halo 3: ODST': ['ODSTMCC', 'ODST'],
        'Halo Reach': ['ReachMCC', 'Reach']}
MIDS = {'Halo 1': ['a10', 'a30', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40'],
        'Halo 2': ['01a', '03a', '05a', '06a', '08a', '08b'],
        'Halo 3': ['010', '020', '030', '040', '050', '070', '100', '110', '120'],
        'Halo 3: ODST': ['sc100', 'sc110', 'sc130', 'sc140', 'l300', 'h100'],
        'Halo Reach': ['m10', 'm20', 'm30', 'm35', 'm45', 'm50', 'm52', 'm60', 'm70']}
# Pseudo-fields with no plugin entry, and enum/choice rows where "0" is a real option
# rather than an unset value.
SKIP_FIELDS = {'Ready / Put Away Animation', 'Reload Animation', 'Map replacement %',
               'Relative Drop Chance', 'Firing Noise', 'Impact Noise',
               'Detonation Noise', 'Movement Penalized', 'Distribution Function'}


def load_db():
    return json.loads(io.open(os.path.join(TOOL, 'halo.json'),
                              encoding='utf-8').read())


def weapon_fields(doc):
    """{field name: set(weapons that card it)} over every weapon card."""
    out = collections.defaultdict(set)
    sw = doc['Player Modifiers']['Specific Weapon Modifier']
    for weapon, cards in sw.items():
        if not isinstance(cards, dict):
            continue
        for card in cards.values():
            if not isinstance(card, dict):
                continue
            for t in card.get('targets') or []:
                if not isinstance(t, dict) or t.get('tag'):
                    continue          # a redirected target is not a weap field
                f = t.get('field')
                for name in ([f] if isinstance(f, str)
                             else (list(f.values()) if isinstance(f, dict) else [])):
                    if isinstance(name, str) and name not in SKIP_FIELDS:
                        out[name].add(weapon)
    return out


def offered_fields(doc, order):
    """{(weapon, game): set(field names its cards actually write there)}."""
    out = collections.defaultdict(set)
    sw = doc['Player Modifiers']['Specific Weapon Modifier']
    for weapon, cards in sw.items():
        if not isinstance(cards, dict):
            continue
        for card in cards.values():
            if not isinstance(card, dict) or card.get('ignore'):
                continue
            g = card.get('game')
            games = [g] if isinstance(g, str) else list(g or order)
            games = [x for x in games if x in SUBS]
            # ODST inherits every Halo 3 card
            if 'Halo 3' in games and 'Halo 3: ODST' not in games:
                games.append('Halo 3: ODST')
            skip = card.get('skip_games') or []
            for game in games:
                if game in skip:
                    continue
                for t in card.get('targets') or []:
                    if not isinstance(t, dict):
                        continue
                    if t.get('games') and game not in t['games']:
                        continue
                    if t.get('skip_games') and game in t['skip_games']:
                        continue
                    f = he.resolve_gamed(t.get('field'), game, order) \
                        if isinstance(t.get('field'), dict) else t.get('field')
                    if isinstance(f, str):
                        out[(weapon, game)].add(f)
    return out


def weapon_tag(doc, weapon, game, order):
    """The weap path this weapon uses in this game, from its own cards."""
    sw = doc['Player Modifiers']['Specific Weapon Modifier']
    for card in (sw.get(weapon) or {}).values():
        if not isinstance(card, dict):
            continue
        t = card.get('tag')
        t = he.resolve_gamed(t, game, order) if isinstance(t, dict) else t
        if isinstance(t, str) and t.startswith('weap '):
            return t.split(' ', 1)[1].split(' & ')[0]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--weapon', help='only this weapon')
    ap.add_argument('--field', help='only this field')
    ap.add_argument('--all-transitions', action='store_true',
                    help='include transitions the weapon already cards')
    o = ap.parse_args()

    he.load_settings()
    P = he.CONFIG['assembly_plugins_dir']
    doc = load_db()
    order = [g for g in doc['Missions'] if g in SUBS]
    fields = weapon_fields(doc)
    offered = offered_fields(doc, order)
    if o.field:
        fields = {k: v for k, v in fields.items() if k.lower() == o.field.lower()}
    sw = doc['Player Modifiers']['Specific Weapon Modifier']
    weapons = sorted(w for w in sw if isinstance(sw[w], dict)
                     and (not o.weapon or w == o.weapon))
    print('%d fields named by weapon cards; %d weapons; %d games'
          % (len(fields), len(weapons), len(order)))

    maps = {g: [halo_patch.open_map(p, g)
                for p in (V.resolve(g, m) for m in MIDS[g]) if p] for g in order}
    plugs = {g: halo_patch.PluginRegistry(P, SUBS[g]).get('weap') for g in order}

    # value of every carded field, per weapon per game
    val = {}
    for weapon in weapons:
        for game in order:
            path = weapon_tag(doc, weapon, game, order)
            if not path:
                continue
            m = next((mm for mm in maps[game] if mm.find_tags('weap', path)), None)
            if m is None:
                continue
            pl = plugs[game]
            for field in fields:
                fld = pl.find(field)
                if not fld:
                    continue
                blk = fld['block_chain'][-1] if fld['block_chain'] else None
                try:
                    v = m.read_first('weap', path, field, pl, blk, 'all')
                except Exception:
                    continue
                if v is not None:
                    val[(weapon, game, field)] = v

    # Two things that look like a transition but are not a gap:
    #  * a PLACEHOLDER zero -- halo.json already declares `zero_is` for the field, so
    #    the earlier game's 0 MEANS the later game's number and nothing changed.
    #  * a weapon no mission list offers in the later game, which no card can reach.
    zero_is = collections.defaultdict(set)
    for cards in sw.values():
        if not isinstance(cards, dict):
            continue
        for card in cards.values():
            if not isinstance(card, dict):
                continue
            for t in card.get('targets') or []:
                if isinstance(t, dict) and t.get('zero_is') and isinstance(
                        t.get('field'), str):
                    zero_is[t['field']].add(float(t['zero_is']))
    listed = collections.defaultdict(set)
    for game, missions in doc['Missions'].items():
        for mission in missions.values():
            for w in (mission.get('weapons') or []):
                listed[w].add(game)

    rows = []
    for weapon in weapons:
        for field in fields:
            seq = [(g, val.get((weapon, g, field))) for g in order]
            seq = [(g, v) for g, v in seq if v is not None]
            for (g0, v0), (g1, v1) in zip(seq, seq[1:]):
                if v0 or not v1:                       # want 0 -> non-zero
                    continue
                has = field in offered.get((weapon, g1), set())
                why = ''
                if float(v1) in zero_is.get(field, ()):
                    why = 'placeholder zero (zero_is %g)' % float(v1)
                elif weapon in listed and g1 not in listed[weapon]:
                    why = 'weapon not in %s mission lists' % g1
                if (has or why) and not o.all_transitions:
                    continue
                rows.append((weapon, field, g0, g1, v1, has, why))

    print('\n%-19s %-32s %-13s -> %-13s %-10s %s'
          % ('weapon', 'field', 'zero in', 'live in', 'value', 'status'))
    print('-' * 110)
    for r in sorted(rows):
        print('%-19s %-32s %-13s -> %-13s %-9s %s'
              % (r[0], r[1], r[2], r[3], round(r[4], 3),
                 'carded' if r[5] else (r[6] or 'GAP')))
    gaps = [r for r in rows if not r[5] and not r[6]]
    print('\n%d transitions shown, %d real gaps'
          % (len(rows), len(gaps)))
    by_w = collections.Counter(r[0] for r in gaps)
    if by_w:
        print('weapons with gaps:', ', '.join('%s(%d)' % kv
                                              for kv in by_w.most_common()))


if __name__ == '__main__':
    main()
