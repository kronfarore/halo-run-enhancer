r"""melee_clang_wire.py -- add each weapon's CLANG melee damage to its Melee Damage card.

A clang is the melee that happens when two swings meet, and Halo splits it by what is
being swung: `gun_to_gun_clang_melee`, `sword_to_gun_clang_melee`,
`hammer_to_gun_clang_melee`, and -- from Reach on -- a second ref for clashing against
a melee WEAPON (`gun_to_sword`, `sword_to_melee`, `hammer_to_melee`). Every weapon
names its own pair, and until now nothing carded them.

They go ON the existing Melee Damage card rather than into a card of their own, on the
user's call: it is one decision -- how hard this weapon hits in melee -- and a clang is
that same swing landing on another swing.

WHERE THE REFS LIVE, which differs by game and is why this reads maps rather than
assuming: Reach and Halo 4 keep them in `Melee Damage Parameters` (Clang at +0x78,
Clang Against Melee Weapon at +0x98 inside the element). Halo 4's ordinary guns leave
the second ref EMPTY where Reach's fill it, so the count varies per weapon as well as
per game -- and the LightRifle points its clang at `sword_to_gun_clang_melee`, which
looks like an authoring slip in 343's tags but is what the game ships and what reading
rather than assuming turns up.

HALO 3 IS DELIBERATELY NOT HERE. Measured on 030_outskirts: its `Clang Melee Damage`
ref (weap root 0x2EC) is NULL on every weapon, so there is nothing to add. Worth
recording alongside that, because it misleads: Halo 3's melee damage is not on `Player
Melee Damage` (0x220, also null) but on `1st Hit Melee Damage` (0x24C) -- strike_melee
for most guns, cut_melee for the Spike Rifle, slice_melee for the Brute Shot -- which
is exactly what its hand-written cards already name.

APPENDED, NEVER REPLACED. Halo 3's Melee Damage cards name hand-picked melee TIERS
(`smash_melee & strike_melee`) that no single ref reproduces, so rewriting the tag from
the refs would quietly drop one.

    python sprint_toolkit/melee_clang_wire.py
    python sprint_toolkit/melee_clang_wire.py --apply
"""

import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import halo_patch                                      # noqa: E402
import melee_damage_fill as MF                          # noqa: E402

HALO_JSON = MF.HALO_JSON
SEP = MF.SEP
ROOT = MF.ROOT

# game -> (plugin subdirs, map folder, maps, clang offsets, block name or None)
LAYOUT = {
    'Halo Reach': (['ReachMCC', 'Reach'], os.path.join(ROOT, 'haloreach', 'maps'),
                   ['m10', 'm20', 'm30', 'm35', 'm45', 'm50', 'm52', 'm60', 'm70'],
                   [0x78, 0x98], 'Melee Damage Parameters'),
    'Halo 4': (['Halo4MCC', 'Halo4'], os.path.join(ROOT, 'halo4', 'maps'),
               ['m10_crash', 'm020', 'm30_cryptum', 'm60_rescue', 'm40_invasion',
                'm70_liftoff', 'm80_delta', 'm90_sacrifice'],
               [0x78, 0x98], 'Melee Damage Parameters'),
}


def clang_refs(game, sw, order):
    """{weapon: [clang jpt! tag, ...]} for this game, read off each weap tag."""
    subs, mapdir, maps, offsets, block_name = LAYOUT[game]
    block = MF.melee_block(subs) if block_name else None
    if block_name and block is None:
        return {}
    want = {}
    for w in sw:
        wt = MF.weap_tag_for(sw, w, game, order)
        if wt:
            want.setdefault(wt.lower(), w)
    out = {}
    for mid in maps:
        path = os.path.join(mapdir, mid + '.map')
        if not os.path.exists(path):
            continue
        m = halo_patch.open_map(path, game)
        for t in m.tags:
            if t['class'] != 'weap' or not t['name'] or t['base'] is None:
                continue
            w = want.get(t['name'].lower())
            if not w or w in out:
                continue
            if block is None:
                base = t['base']
            else:
                cnt = m.i32(t['base'] + block)
                arr = m.data2off(m.u32(t['base'] + block + 4))
                if not arr or cnt <= 0:
                    continue
                base = arr
            names = []
            for off in offsets:
                ident = m.u32(base + off + 0xC)
                if ident == 0xFFFFFFFF:
                    continue
                r = m.tag(ident & 0xFFFF)
                if r and r['name'] and r['name'] not in names:
                    names.append(r['name'])
            if names:
                out[w] = names
    return out


def _span(lines, i):
    depth, started = 0, False
    for j in range(i, len(lines)):
        depth += lines[j].count('{') - lines[j].count('}')
        if '{' in lines[j]:
            started = True
        if started and depth <= 0:
            return i, j
    return i, len(lines) - 1


def _indent(line):
    return line[:len(line) - len(line.lstrip())]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    doc = json.load(io.open(HALO_JSON, encoding='utf-8'))
    order = list(doc['Missions'])
    sw = doc['Player Modifiers']['Specific Weapon Modifier']

    print('reading clang refs off the maps...')
    refs = {g: clang_refs(g, sw, order) for g in LAYOUT}

    plan = []
    for w in sorted(sw):
        card = sw[w].get('Melee Damage')
        if not isinstance(card, dict):
            continue
        g = card.get('game')
        gl = [g] if isinstance(g, str) else list(g or [])
        for game in LAYOUT:
            if gl and game not in gl:
                continue
            have = MF.resolve(card.get('tag'), game, order)
            if not isinstance(have, str) or not have.startswith('jpt! '):
                continue
            cur = [x.strip() for x in have[5:].split('&')]
            add = [x for x in refs.get(game, {}).get(w, []) if x not in cur]
            if add:
                plan.append((w, game, 'jpt! ' + ' & '.join(cur + add), add))

    for w, game, _tag, add in plan:
        print('%-20s %-11s + %s'
              % (w, game, ', '.join(x.rsplit(SEP, 1)[-1] for x in add)))
    print('\n%d card/game tag(s) to extend' % len(plan))
    if not a.apply:
        print('(report only -- pass --apply)')
        return

    lines = io.open(HALO_JSON, encoding='utf-8').read().split('\n')
    written = 0
    for w, game, tag, _add in plan:
        wi = next((i for i, l in enumerate(lines) if l.strip() == '"%s": {' % w), None)
        if wi is None:
            continue
        ws, we = _span(lines, wi)
        ci = next((i for i in range(ws, we + 1)
                   if lines[i].strip() == '"Melee Damage": {'), None)
        if ci is None:
            continue
        cs, ce = _span(lines, ci)
        ti = next((i for i in range(cs, ce + 1)
                   if lines[i].strip().startswith('"tag":')), None)
        if ti is None:
            continue
        jt = json.dumps(tag, ensure_ascii=False)
        stripped = lines[ti].strip()
        if stripped.startswith('"tag": "'):
            # A PLAIN-STRING tag: the Halo 4-only cards authored by h4_new_weapons all
            # look like this, so a per-game marker lookup finds nothing and silently
            # skipped nine of them.
            head = lines[ti][:lines[ti].index('"tag":')]
            trail = ',' if lines[ti].rstrip().endswith(',') else ''
            lines[ti] = '%s"tag": %s%s' % (head, jt, trail)
            written += 1
        elif lines[ti].rstrip().endswith('{'):
            ts, te = _span(lines, ti)
            gi = next((i for i in range(ts, te + 1)
                       if lines[i].strip().startswith('"%s":' % game)), None)
            if gi is None:
                continue
            trail = ',' if lines[gi].rstrip().endswith(',') else ''
            lines[gi] = '%s"%s": %s%s' % (_indent(lines[gi]), game, jt, trail)
            written += 1
        else:
            marker = '"%s": ' % game
            i = lines[ti].find(marker)
            if i < 0:
                continue
            j = lines[ti].find('"', i + len(marker) + 1)
            while j > 0 and lines[ti][j - 1] == SEP:
                j = lines[ti].find('"', j + 1)
            if j < 0:
                continue
            lines[ti] = lines[ti][:i] + marker + jt + lines[ti][j + 1:]
            written += 1

    out = '\n'.join(lines)
    json.loads(out)
    io.open(HALO_JSON, 'w', encoding='utf-8', newline='').write(out)
    print('extended %d tag(s)' % written)


if __name__ == '__main__':
    main()
