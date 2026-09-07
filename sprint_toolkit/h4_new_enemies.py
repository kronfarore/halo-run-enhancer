r"""h4_new_enemies.py -- author halo.json cards for Halo 4's three Promethean species.

Knight, Crawler and Watcher have no card anywhere, because nothing before Halo 4 had
them. Each is MODELLED on an existing species and gets a copy of that card set
retargeted at its own Halo 4 char family, exactly as `h4_new_weapons` does for weapons.

THE MODELS WERE SCORED, NOT GUESSED. Method: resolve each candidate's card targets PER
GAME (a card's `targets` can itself be a per-game dict, and tallying it as a list scores
those cards as zero -- that mistake made the Grunt look as though it targeted no Retreat
Properties), then check each block against what the Halo 4 species actually DEFINES
across all its variants. Eight candidates were scored against each:

    Knight   <- Elite      89% (59/66 field-targets land) -- best of eight.
    Crawler  <- Grunt      70% (45/64). The misses are Grenades x8 and Weapons x7,
                           blocks the Crawler does not define, so those cards are
                           refused here rather than shipped dead. Skirmisher scores
                           100% but on a much smaller set (24 targets), so the Grunt
                           still yields more landing cards.
    Watcher  <- Sentinel   84% (38/45), missing only Cover x4 and Triggers x3.
                           The Engineer -- the intuitive pick, since both hover and
                           support -- scores 36% and is second-WORST: its cards are
                           Cover Properties x7 and Engineer Properties x7, and the
                           Watcher defines neither. The Sentinel is also the Watcher's
                           mechanical sibling: `Bishop Properties` is defined by
                           `storm_bishop` AND `storm_sentinel` and by nothing else.

Measured vitality, which is what settled the shield question: Crawler 40/100 body with
shield 0; Knight 70/120 body, shield 80/200; Watcher 20/50 body, shield 35/35.

The Watcher's own `Bishop Properties`, and its unique Guardian / Combotron Child /
Vehicle Properties, are NOT carded here -- that is new-mechanic authoring rather than
modelling, and the user has it queued separately.

    python sprint_toolkit/h4_new_enemies.py            # report
    python sprint_toolkit/h4_new_enemies.py --show
    python sprint_toolkit/h4_new_enemies.py --apply
"""

import argparse
import collections
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h4_new_weapons as NW                            # noqa: E402
import h4_wire_enemies as E                            # noqa: E402
import h4_wire_weapons as W                            # noqa: E402

HALO_JSON = W.HALO_JSON
GAME = W.GAME

MODELS = [('Knight', 'Elite'), ('Crawler', 'Grunt'), ('Watcher', 'Sentinel')]

# A few of the model's card names carry the MODEL's identity, which reads as a mistake
# on the new species even when the tag underneath is right. Renamed with a corrected
# `desc`, keyed (new species, model's card name) -> (name, desc).
#
# The Crawler pair is the one that needed looking at rather than renaming blind: the
# Grunt's "Grunt Damage"/"Grunt Radius" are its methane-tank explosion, and a Crawler
# has no tank -- but the tag resolves to `storm_pawn_melee`, the Crawler's MELEE
# damage, which is worth a card and which the Grunt model otherwise gives it nowhere.
RENAME = {
    ('Crawler', 'Grunt Damage'): (
        'Melee Damage', 'How hard a Crawler hits you in melee.'),
    ('Crawler', 'Grunt Radius'): (
        'Melee Radius', "How far a Crawler's melee reaches."),
    ('Watcher', 'Projectile Range Sentinel Beam'): (
        'Projectile Range', "How far the Watcher's beam carries."),
}


def build(new, model, se, have, reg, order, families):
    cards, skipped = {}, []
    for cname, card in se.get(model, {}).items():
        if not isinstance(card, dict):
            continue
        why = E.skip_reason(new, cname) or E.skip_reason(model, cname)
        if why:
            skipped.append((cname, why))
            continue
        good, res = E.check(new, cname, card, have, reg, order, families,
                            retarget=True)
        if not good:
            skipped.append((cname, res))
            continue
        tag = res['tag']
        if not tag:
            tag = W.resolve(card.get('tag'), GAME, order)
        new_card = {k: card[k] for k in NW.CARD_KEEP if k in card}
        new_card['game'] = [GAME]
        new_card['tag'] = tag
        tplan = res.get('targets') or {}
        rows = []
        for i, t in enumerate(W.resolve(card.get('targets'), GAME, order) or []):
            if not isinstance(t, dict):
                continue
            g = t.get('games')
            if isinstance(g, list) and GAME not in g and not tplan.get(i, {}).get('games'):
                continue
            rows.append(NW.build_target(t, order, tplan.get(i, {}), new, cname))
        if not rows:
            skipped.append((cname, 'no targets survive in Halo 4'))
            continue
        new_card['targets'] = rows
        name, desc = RENAME.get((new, cname), (cname, None))
        if desc:
            new_card['desc'] = desc
            # The inherited debug_desc explains the MODEL's mechanic; drop it rather
            # than leave a Crawler card talking about methane tanks.
            new_card.pop('debug_desc', None)
        cards[name] = new_card
    return cards, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--show', action='store_true')
    a = ap.parse_args()

    doc = json.load(io.open(HALO_JSON, encoding='utf-8'))
    order = list(doc['Missions'])
    se = doc['Enemy modifiers']['Specific Enemy modifier']

    print('resolving Halo 4 char tags...')
    have, _melee = W.campaign_tags()
    families = E.species_family()
    reg = W.halo_patch.PluginRegistry(W.PLUGINS, W.SUBDIRS)

    built, total = collections.OrderedDict(), 0
    for new, model in MODELS:
        if new in se:
            print('=== %-10s already in halo.json -- skipped' % new)
            continue
        cards, skipped = build(new, model, se, have, reg, order, families)
        built[new] = cards
        total += len(cards)
        print('=== %-10s %2d cards from %s' % (new, len(cards), model))
        if a.show:
            for cname, c in cards.items():
                print('        %-26s %s' % (cname, str(c['tag'])[:88]))
        for cname, why in skipped:
            print('        (not built) %-24s %s' % (cname, why))
    print('\n%d new cards across %d species' % (total, len(built)))

    if not a.apply:
        print('(report only -- pass --apply)')
        return

    lines = io.open(HALO_JSON, encoding='utf-8').read().split('\n')
    key = '\t\t"Specific Enemy modifier": {'
    si = next(i for i, l in enumerate(lines) if l.rstrip('\r') == key)
    depth, end = 0, None
    for j in range(si, len(lines)):
        depth += lines[j].count('{') - lines[j].count('}')
        if depth <= 0:
            end = j
            break
    blocks = [NW.emit(n, c) for n, c in built.items() if c]
    lines[end - 1] = lines[end - 1].rstrip() + ','
    lines[end:end] = (',\n'.join(blocks)).split('\n')
    out = '\n'.join(lines)
    json.loads(out)
    io.open(HALO_JSON, 'w', encoding='utf-8', newline='').write(out)
    print('wrote %d cards into halo.json' % total)


if __name__ == '__main__':
    main()
