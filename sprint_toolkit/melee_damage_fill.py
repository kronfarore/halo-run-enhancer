r"""melee_damage_fill.py -- give a Melee Damage card to the weapons that have none.

Every weapon can melee, and the damage it does is a `jpt!` its own weap tag names in
`Melee Damage Parameters / Melee Damage` (Reach and Halo 4) -- but a weapon only ever
got a Melee Damage card if some earlier game's card happened to be inheritable. That
left nine weapons offering no melee card at all: the whole Reach-introduced set, plus
Halo 4's Sticky Detonator, whose model (the Grenade Launcher) had none to copy.

The tag is READ, not guessed: this opens the campaign maps and follows each weapon's
own Melee Damage ref, the same way `h4_wire_weapons` does. In practice every one of
them lands on `globals/damage_effects/strike_melee`, which is worth stating plainly --
these cards share one tag with each other AND with every existing Melee Damage card in
the same game, so a melee card on any weapon moves melee for all of them. That is not
new; it is how Reach and Halo 4 build melee, and Halo 3 was the game with tiers.

Not filled, and each for its own reason:
  * Energy Blade -- its melee is already carded, as Strike Damage and Dash Damage.
    A third card would land on the same fields.
  * the grenades -- you do not melee with a grenade.
  * Machine Gun, Plasma Cannon, Missile Pod, Flamethrower -- turrets cannot melee,
    which is the user's own rule.
  * ODST looked like it was missing eleven of these; it is not. ODST INHERITS Halo 3,
    so a card listing Halo 3 already applies there. Checking the raw `game` list
    without that rule reports a gap that does not exist.

    python sprint_toolkit/melee_damage_fill.py
    python sprint_toolkit/melee_damage_fill.py --apply
"""

import argparse
import collections
import io
import json
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import assembly_plugins                               # noqa: E402
import halo_patch                                     # noqa: E402

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HALO_JSON = os.path.join(TOOL, 'halo.json')
PLUGINS = assembly_plugins.plugins_dir()
SEP = chr(92)
ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection"

# game -> (plugin subdirs, map folder, campaign map basenames)
GAMES = {
    'Halo Reach': (['ReachMCC', 'Reach'], os.path.join(ROOT, 'haloreach', 'maps'),
                   ['m10', 'm20', 'm30', 'm35', 'm45', 'm50', 'm52', 'm60', 'm70']),
    'Halo 4': (['Halo4MCC', 'Halo4'], os.path.join(ROOT, 'halo4', 'maps'),
               ['m10_crash', 'm020', 'm30_cryptum', 'm60_rescue', 'm40_invasion',
                'm70_liftoff', 'm80_delta', 'm90_sacrifice']),
}
# Offsets inside a Melee Damage Parameters element (Reach and Halo 4 share them).
MELEE_DAMAGE_REF = 0x18
CLANG_REFS = [('Clang Melee Damage', 0x78),
              ('Clang Melee Against Melee Weapon Damage', 0x98)]
# Halo 3 has no such block -- its melee tagRefs sit at the weap ROOT, and it has no
# "against melee weapon" ref at all; that pair arrives in Reach.
H3_CLANG_ROOT = 0x2EC
MODEL = ('Assault Rifle', 'Melee Damage')   # the card whose text and targets to copy


def melee_block(subs):
    for sub in subs:
        p = os.path.join(PLUGINS, sub, 'weap.xml')
        if not os.path.isfile(p):
            continue
        for ch in ET.parse(p).getroot():
            if ch.tag.lower() == 'tagblock' and ch.get('name') == 'Melee Damage Parameters':
                return int(ch.get('offset'), 16)
    return None


def resolve(value, game, order):
    """halo_enhancer.resolve_gamed, local so this needs no GUI import."""
    if not isinstance(value, dict):
        return value
    if game in value:
        return value[game]
    if 'default' in value:
        return value['default']
    if game in order:
        for g in reversed(order[:order.index(game)]):
            if g in value:
                return value[g]
    return None


def weap_tag_for(sw, weapon, game, order):
    """The weapon's own weap tag in this game, taken from any card that names one.

    Resolved with the game FALLBACK rather than an exact key lookup. Several weapons
    carry no entry for their own game -- the Concussion Rifle's cards name Halo 3 and
    Halo 4 but not Reach, because Reach shares Halo 3's path -- and an exact lookup
    silently found nothing for exactly those.
    """
    for cname, c in sw.get(weapon, {}).items():
        if not isinstance(c, dict):
            continue
        v = resolve(c.get('tag'), game, order)
        if isinstance(v, str) and v.startswith('weap '):
            return v[5:].split('&')[0].strip()
    return None


def collect(game, wanted, sw, order):
    """{weapon: its Melee Damage jpt!} for this game."""
    subs, mapdir, maps = GAMES[game]
    off = melee_block(subs)
    if off is None:
        return {}
    want_tags = {}
    for w in wanted:
        wt = weap_tag_for(sw, w, game, order)
        if wt:
            want_tags[wt.lower()] = w
    out = {}
    for mid in maps:
        path = os.path.join(mapdir, mid + '.map')
        if not os.path.exists(path):
            continue
        m = halo_patch.open_map(path, game)
        for t in m.tags:
            if t['class'] != 'weap' or not t['name'] or t['base'] is None:
                continue
            w = want_tags.get(t['name'].lower())
            if not w or w in out:
                continue
            cnt = m.i32(t['base'] + off)
            arr = m.data2off(m.u32(t['base'] + off + 4))
            if not arr or cnt <= 0:
                continue
            names = []
            for off in [MELEE_DAMAGE_REF] + [o for _n, o in CLANG_REFS]:
                ident = m.u32(arr + off + 0xC)
                if ident == 0xFFFFFFFF:
                    continue
                r = m.tag(ident & 0xFFFF)
                if r and r['name'] and r['name'] not in names:
                    names.append(r['name'])
            if names:
                out[w] = names
        if len(out) == len(want_tags):
            break
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    doc = json.load(io.open(HALO_JSON, encoding='utf-8'))
    sw = doc['Player Modifiers']['Specific Weapon Modifier']
    model = sw[MODEL[0]][MODEL[1]]

    gap = collections.defaultdict(list)          # weapon -> [game]
    for game in GAMES:
        names = set()
        for mm in doc['Missions'][game].values():
            for k in ('weapons', 'turrets', 'grenades'):
                names |= set(mm.get(k) or [])
        names = {('Pistol' if n == 'Magnum' else n) for n in names}
        for w in sorted(names & set(sw)):
            if w in SKIP:
                continue
            c = sw[w].get('Melee Damage')
            if isinstance(c, dict):
                g = c.get('game')
                gl = [g] if isinstance(g, str) else list(g or [])
                if not gl or game in gl:
                    continue
                gap[w].append(game)
            else:
                gap[w].append(game)

    order = list(doc['Missions'])
    refs = {g: collect(g, [w for w in gap if g in gap[w]], sw, order)
            for g in GAMES}

    plan = {}
    for w, games in sorted(gap.items()):
        rows = {}
        for g in games:
            names = refs.get(g, {}).get(w)
            if names:
                rows[g] = 'jpt! ' + ' & '.join(names)
        if rows:
            plan[w] = rows
        print('%-20s %s' % (w, ' | '.join(
            '%s -> %s' % (g, ', '.join(x.rsplit(SEP, 1)[-1] for x in t[5:].split(' & ')))
            for g, t in rows.items()) or 'NO REF FOUND'))
    print('\n%d Melee Damage card(s) to add' % len(plan))
    if not a.apply:
        print('(report only -- pass --apply)')
        return

    lines = io.open(HALO_JSON, encoding='utf-8').read().split('\n')

    def find(pred, lo, hi):
        for j in range(lo, min(hi, len(lines) - 1) + 1):
            if pred(lines[j]):
                return j
        return None

    def span(i):
        depth, started = 0, False
        for j in range(i, len(lines)):
            depth += lines[j].count('{') - lines[j].count('}')
            if '{' in lines[j]:
                started = True
            if started and depth <= 0:
                return i, j
        return i, len(lines) - 1

    added = 0
    for w, rows in plan.items():
        if isinstance(sw[w].get('Melee Damage'), dict):
            print('   %s already has the card in another game -- widen by hand' % w)
            continue
        wi = find(lambda l: l.strip() == '"%s": {' % w, 0, len(lines) - 1)
        if wi is None:
            continue
        ws, we = span(wi)
        card = ['\t\t\t\t"Melee Damage": {',
                '\t\t\t\t\t"desc": %s' % json.dumps(model['desc'], ensure_ascii=False) + ',']
        if 'debug_desc' in model:
            card.append('\t\t\t\t\t"debug_desc": %s,'
                        % json.dumps(model['debug_desc'], ensure_ascii=False))
        card.append('\t\t\t\t\t"game": [%s],'
                    % ', '.join(json.dumps(g) for g in rows))
        card.append('\t\t\t\t\t"tag": {%s},'
                    % ', '.join('%s: %s' % (json.dumps(g), json.dumps(t, ensure_ascii=False))
                                for g, t in rows.items()))
        tg = ',\n'.join('\t\t\t\t\t\t%s' % json.dumps(t, ensure_ascii=False)
                        for t in model['targets'])
        card.append('\t\t\t\t\t"targets": [\n%s\n\t\t\t\t\t]' % tg)
        card.append('\t\t\t\t},')
        lines[ws + 1:ws + 1] = card
        added += 1

    out = '\n'.join(lines)
    json.loads(out)
    io.open(HALO_JSON, 'w', encoding='utf-8', newline='').write(out)
    print('added %d Melee Damage card(s)' % added)


# Weapons that must NOT get one -- see the module docstring.
SKIP = {'Energy Blade', 'Frag Grenade', 'Plasma Grenade', 'Pulse Grenade',
        'Claymore Grenade', 'Firebomb Grenade', 'Machine Gun', 'Plasma Cannon',
        'Missile Pod', 'Flamethrower'}

if __name__ == '__main__':
    main()
