r"""h4_new_weapons.py -- author halo.json cards for the weapons Halo 4 introduced.

Ten weapons and one grenade have no card anywhere, because nothing before Halo 4 had
them. `h4_wire_weapons` cannot help: there is no earlier card to widen. So each new
weapon is MODELLED on an existing one -- the user's mapping, 2026-09-07 -- and gets a
copy of that weapon's card set retargeted at its own Halo 4 tags:

    Storm Rifle          <- Plasma Rifle       SAW                  <- Assault Rifle
    Scattershot          <- Shotgun            LightRifle           <- Covenant Carbine
    Suppressor           <- Assault Rifle      Boltshot             <- Pistol
    Railgun              <- Spartan Laser      Sticky Detonator     <- Grenade Launcher
    Binary Rifle         <- Sniper Rifle       Incineration Cannon  <- Rocket Launcher
    Pulse Grenade        <- Plasma Grenade

The Target Designator is deliberately absent: it designates for an off-map MAC that
exists only in Reclaimer's Mammoth section, so it would do nothing anywhere else.

WHY THIS REUSES h4_wire_weapons RATHER THAN RESOLVING TAGS ITSELF. Deciding which Halo
4 tag a card means is the same question that tool already answers, traps included --
the `storm_` rename, `_npc`/`_knight`/`_pawnhead` variants, per-target tag redirects to
the projectile, the `nth` mismatch, shared melee tags. Answering it twice would mean
two answers to keep in step. `check()` is called here with the NEW weapon's name and
the MODEL's card, and returns both the tag and the per-target adjustments.

THE EMITTED CARDS ARE HALO 4 ONLY, so every per-game value collapses to its Halo 4
answer: `field`, `block` and `nth` are written as plain values rather than dicts, a
target's `games` list is dropped, and a target's tag redirect becomes a plain string.
That keeps the new blocks readable next to the hand-written ones instead of carrying
five games of history none of these weapons has.

`desc` and `debug_desc` are copied verbatim. Both describe the FIELDS and the mechanic,
not the weapon -- "How hard your aim is pulled toward a target" is as true of the
Suppressor as of the Assault Rifle -- so copying is right and rewriting them per weapon
would be noise. Where a debug_desc cites shipped values it cites the model's; that is
worth knowing and is not worth inventing new numbers over.

    python sprint_toolkit/h4_new_weapons.py            # report
    python sprint_toolkit/h4_new_weapons.py --show
    python sprint_toolkit/h4_new_weapons.py --apply
"""

import argparse
import collections
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h4_wire_weapons as W                            # noqa: E402

TOOL = W.TOOL
HALO_JSON = W.HALO_JSON
GAME = W.GAME
SEP = W.SEP

MODELS = [
    ('Storm Rifle', 'Plasma Rifle'),
    ('SAW', 'Assault Rifle'),
    ('Scattershot', 'Shotgun'),
    ('LightRifle', 'Covenant Carbine'),
    ('Suppressor', 'Assault Rifle'),
    ('Boltshot', 'Pistol'),
    ('Railgun', 'Spartan Laser'),
    ('Sticky Detonator', 'Grenade Launcher'),
    ('Binary Rifle', 'Sniper Rifle'),
    ('Incineration Cannon', 'Rocket Launcher'),
    ('Pulse Grenade', 'Plasma Grenade'),
]

# Halo 4's grenade_list rows, in the order globals/grenade_list stores them.
GRENADE_ROW = {'Frag Grenade': 0, 'Plasma Grenade': 1, 'Pulse Grenade': 2}

# Keys copied onto a target untouched -- everything that is about the DECISION rather
# than about which game is being patched.
TARGET_KEEP = ('group', 'harder_when', 'min', 'max', 'scale', 'offset', 'zero_is',
               'index', 'choice', 'follows_choice', 'reload_anim', 'swap_anim',
               'diff_prefix_nl', 'difficulty', 'derived', 'map_swap', 'map_equip',
               'equip_drop', 'nudge')
CARD_KEEP = ('desc', 'debug_desc', 'ignore', 'wildcard', 'upgrade_of')


def build_target(t, order, plan_for_target, new_weapon, cname):
    """One model target, collapsed to its Halo 4 answer."""
    out = {}
    f = W.resolve(t.get('field'), GAME, order)
    if isinstance(f, str):
        out['field'] = f
    blk = W.resolve(t.get('block'), GAME, order)
    if blk:
        out['block'] = blk
    nth = plan_for_target.get('nth')
    if nth is None:
        nth = W.resolve(t.get('nth'), GAME, order) or 0
    if nth:
        out['nth'] = nth
    own = plan_for_target.get('tag')
    if own is None and t.get('tag') is not None:
        own = W.resolve(t.get('tag'), GAME, order)
    if own:
        out['tag'] = own
    for k in TARGET_KEEP:
        if k in t:
            out[k] = t[k]
    # The grenade count lives in a different tag with a per-grenade row.
    if cname == 'Maximum Count' and new_weapon in GRENADE_ROW:
        out['index'] = GRENADE_ROW[new_weapon]
    return out


def build(new, model, sw, have, melee, reg, order, patterns):
    """(cards, skipped) for one new weapon."""
    cards, skipped = {}, []
    for cname, card in sw.get(model, {}).items():
        if not isinstance(card, dict):
            continue
        why = W.skip_reason(new, cname) or W.skip_reason(model, cname)
        if why:
            skipped.append((cname, why))
            continue
        good, res = W.check(new, cname, card, have, reg, order, patterns, melee)
        if not good:
            skipped.append((cname, res))
            continue
        tag = res['tag']
        if not tag:
            # The model's inherited wildcard resolved as-is. A Halo 4-only card cannot
            # rely on that fallback, so write the tag out explicitly.
            tag = W.resolve(card.get('tag'), GAME, order)
        new_card = {k: card[k] for k in CARD_KEEP if k in card}
        new_card['game'] = [GAME]
        new_card['tag'] = tag
        tplan = res.get('targets') or {}
        targets = W.resolve(card.get('targets'), GAME, order) or []
        rows = []
        for i, t in enumerate(targets):
            if not isinstance(t, dict):
                continue
            g = t.get('games')
            if isinstance(g, list) and GAME not in g and not tplan.get(i, {}).get('games'):
                continue                      # this target is not offered in Halo 4
            rows.append(build_target(t, order, tplan.get(i, {}), new, cname))
        if not rows:
            skipped.append((cname, 'no targets survive in Halo 4'))
            continue
        new_card['targets'] = rows
        cards[cname] = new_card
    return cards, skipped


def emit(name, cards):
    """One weapon block in halo.json's house style: tabs, one-line targets."""
    L = ['\t\t\t%s: {' % json.dumps(name, ensure_ascii=False)]
    items = list(cards.items())
    for ci, (cname, card) in enumerate(items):
        L.append('\t\t\t\t%s: {' % json.dumps(cname, ensure_ascii=False))
        body = []
        for k in ('desc', 'debug_desc', 'ignore', 'wildcard', 'upgrade_of'):
            if k in card:
                body.append('\t\t\t\t\t%s: %s'
                            % (json.dumps(k), json.dumps(card[k], ensure_ascii=False)))
        body.append('\t\t\t\t\t"game": ["%s"]' % GAME)
        body.append('\t\t\t\t\t"tag": %s' % json.dumps(card['tag'], ensure_ascii=False))
        rows = ',\n'.join('\t\t\t\t\t\t%s' % json.dumps(t, ensure_ascii=False)
                          for t in card['targets'])
        body.append('\t\t\t\t\t"targets": [\n%s\n\t\t\t\t\t]' % rows)
        L.append(',\n'.join(body))
        L.append('\t\t\t\t}' + (',' if ci < len(items) - 1 else ''))
    L.append('\t\t\t}')
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--show', action='store_true', help='print every card and its tag')
    a = ap.parse_args()

    doc = json.load(io.open(HALO_JSON, encoding='utf-8'))
    order = list(doc['Missions'])
    sw = doc['Player Modifiers']['Specific Weapon Modifier']

    print('resolving Halo 4 tags...')
    have, melee = W.campaign_tags()
    patterns = W.tag_patterns()
    reg = W.halo_patch.PluginRegistry(W.PLUGINS, W.SUBDIRS)

    built, total = collections.OrderedDict(), 0
    for new, model in MODELS:
        if new in sw:
            print('=== %-20s already in halo.json -- skipped' % new)
            continue
        cards, skipped = build(new, model, sw, have, melee, reg, order, patterns)
        built[new] = cards
        total += len(cards)
        print('=== %-20s %2d cards from %s' % (new, len(cards), model))
        if a.show:
            for cname, c in cards.items():
                print('        %-24s %s' % (cname, str(c['tag'])[:96]))
        for cname, why in skipped:
            print('        (not built) %-22s %s' % (cname, why))
    print('\n%d new cards across %d weapons' % (total, len(built)))

    if not a.apply:
        print('(report only -- pass --apply)')
        return

    lines = io.open(HALO_JSON, encoding='utf-8').read().split('\n')
    # Insert before the closing brace of "Specific Weapon Modifier".
    key = '\t\t"Specific Weapon Modifier": {'
    si = next(i for i, l in enumerate(lines) if l.rstrip('\r') == key)
    depth, end = 0, None
    for j in range(si, len(lines)):
        depth += lines[j].count('{') - lines[j].count('}')
        if depth <= 0:
            end = j
            break
    blocks = [emit(n, c) for n, c in built.items() if c]
    lines[end - 1] = lines[end - 1].rstrip() + ','
    lines[end:end] = (',\n'.join(blocks)).split('\n')
    out = '\n'.join(lines)
    json.loads(out)
    io.open(HALO_JSON, 'w', encoding='utf-8', newline='').write(out)
    print('wrote %d cards into halo.json' % total)


if __name__ == '__main__':
    main()
