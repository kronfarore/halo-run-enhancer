r"""h4_wire_weapons.py -- give Halo 4's weapons their halo.json cards.

The Reach counterpart of this tool (`reach_wire_weapons.py`) could usually inherit the
tag: Reach kept Halo 3's tag paths, so wiring was mostly a matter of adding the game to
an allow list. **Halo 4 renamed every weapon tag with a `storm_` prefix**
(`objects\weapons\rifle\storm_br\storm_br`), so nothing inherits and every wired card
needs a tag path written for it. That is the whole difference, and it is why this is a
separate tool rather than a `--game` flag on the Reach one.

It also makes the failure mode worse rather than better. `resolve_gamed` falls back to
the nearest EARLIER game, so an unwired card does not go quiet -- it resolves a Halo 3
path, finds nothing in the map, and reports "not present in this map", which reads like
a fact about the level rather than a hole in the card set.

So the wiring is checked, not assumed. For each card this works out the Halo 4 tag from
the census vocabulary, then asks two questions against the real Halo 4 maps and the
Halo 4 plugin:

    does the TAG exist in Halo 4?     (union of every campaign map's tag names, for
                                       the card's OWN tag class -- grenade cards are
                                       not all `weap`)
    do the FIELDS resolve on it?      (plugin.find, honouring block / nth /
                                       diff_prefix_nl, exactly as the patcher does)

Only a card that passes both gets a Halo 4 entry. Everything else is reported with its
reason, because those are the cards that need real work.

WHICH VARIANTS A CARD NAMES, and why it is not just the base tag. Halo 4 ships `_npc`
and `_knight` copies of the Forerunner weapons beside the base. Measured on Shutdown:
they are SEPARATE tag-data blocks (so naming both cannot double-apply -- see the
shared-block hazard this project has hit before), they differ only in AI ammo counts,
and -- the deciding fact -- they are squad-carried but never PLACED. Halo 4 places very
few pickups (Shutdown places three weapons in the whole mission), so the LightRifle the
player is actually holding is nearly always the `_npc` one off a dead Knight. A card
naming only the base would silently miss it.

`_pawnhead` is excluded on the opposite reasoning: those are the Crawler's head-mounted
guns, a body part the player never picks up, so tuning them under a PLAYER weapon card
would only buff the enemy shooting at you. They are listed by --variants so the call
stays visible.

    python sprint_toolkit/h4_wire_weapons.py               # report only
    python sprint_toolkit/h4_wire_weapons.py --variants    # the tag map it will write
    python sprint_toolkit/h4_wire_weapons.py --show-ok
    python sprint_toolkit/h4_wire_weapons.py --apply
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import assembly_plugins                               # noqa: E402
import halo_patch                                     # noqa: E402
import h4_census as hc                                # noqa: E402

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HALO_JSON = os.path.join(TOOL, 'halo.json')
PLUGINS = assembly_plugins.plugins_dir()
SEP = chr(92)
GAME = 'Halo 4'
SUBDIRS = ['Halo4MCC', 'Halo4']
DIFF_PREFIXES = ('Normal ', 'Legendary ')
ALIAS = {'Magnum': 'Pistol'}

# Folder patterns per vocabulary name, matched as substrings of a forward-slashed tag
# path exactly as in h4_census. The weapon and grenade tables come straight from the
# census so there is ONE vocabulary; only the two turrets need their own entries,
# because the census matches those on the EMPLACEMENT (a `vehi` tag) while a card has
# to name the gun.
TURRET_TAGS = {
    'Machine Gun': ('weapons/turret/storm_machinegun_turret/',
                    'vehicles/human/turrets/machinegun/weapon/'),
    'Plasma Cannon': ('vehicles/covenant/turrets/plasma_turret/weapon/',),
}
# Variants that exist but must NOT be wired. See the module docstring.
EXCLUDE_VARIANTS = ('_pawnhead',)
# Suffixes that split ONE damage effect into who it lands on rather than naming two
# different effects. A card that means the effect wants every one of them.
AUDIENCE_SUFFIXES = ('_enemy', '_friendly')

# Cards that RESOLVE in Halo 4 and must still not be wired, because the mechanic behind
# them is gone. Nothing in the tags says so -- every one of these reads and writes
# perfectly well -- so the check cannot find them and the list has to be explicit.
# Reported in their own section rather than dropped quietly.
#
# A key is either a card name (every weapon) or `Weapon/Card` for one weapon.
SKIP_CARDS = {
    'Rider Damage':
        'deprecated from Reach on -- the fields still read, but the user tested them '
        'in game on Tip of the Spear and they do nothing. Halo 4 is a later engine '
        'than Reach, so wiring it would ship 15 cards that silently no-op.',
    'Dual Weapon Damage': 'Halo 4 has no dual wielding (see DUAL_WIELD_ABSENT).',
    'Dual Weapon Error': 'Halo 4 has no dual wielding (see DUAL_WIELD_ABSENT).',
    # The three the PLUGIN cannot rule out: it declares the block, the Halo 4 tag ships
    # it with zero elements, and a write to a zero-element block goes nowhere. Found by
    # running deadcards.py against a wired halo.json -- that tool asks the map, which
    # is the only place this shows up. Re-run it after changing anything here.
    'Machine Gun/Melee Seeking':
        'a melee card on a turret is meaningless, and the damage pyramid block is '
        'empty on both Halo 4 machine-gun tags.',
    'Plasma Cannon/Melee Seeking':
        'a melee card on a turret is meaningless, and the damage pyramid block is '
        'empty on both Halo 4 plasma-turret tags.',
    'Gravity Hammer/Accuracy Penalties':
        "Halo 4's gravity hammer ships an empty accuracy-penalty block, so every "
        'write lands in nothing.',
}


def skip_reason(weapon, cname):
    """Why this card must not be wired, or None."""
    return SKIP_CARDS.get('%s/%s' % (weapon, cname)) or SKIP_CARDS.get(cname)


def tag_patterns():
    """{vocabulary name: (folder pattern, ...)}.

    Keys go through ALIAS because the census speaks the mission list's language
    (Magnum) while a card is filed under the canonical weapon (Pistol). Forgetting
    that silently produced zero tag matches for every Magnum card.
    """
    out = {}
    for pat, name in list(hc.WEAPONS) + list(hc.GRENADES):
        out.setdefault(ALIAS.get(name, name), []).append(pat)
    for name, pats in TURRET_TAGS.items():
        out.setdefault(ALIAS.get(name, name), []).extend(pats)
    return {k: tuple(v) for k, v in out.items()}


def _leaf(path):
    return path.rsplit(SEP, 1)[-1].lower()


def _norm_leaf(path):
    """A leaf with Halo 4's `storm_` prefixing removed, for comparison across games."""
    return _leaf(path).replace('storm_', '')


def disambiguate(candidates, inherited_path):
    """Narrow several same-folder candidates to the ONE the inherited card meant.

    Needed because a weapon folder holds a family of damage effects, not one. A card
    that means "Frag Grenade explosion" folder-matches the impact, the boarding
    explosion and the equipment explosion too, and wiring all four would quietly
    change what the card does rather than port it.

    Exact normalised leaf first, then the longest matching tail of the inherited
    leaf's tokens -- `flak_explosion` finds `flak_bolt_explosion` on the tail
    `explosion` once the fuller tails miss. Anything still ambiguous is REPORTED, not
    guessed.
    """
    want = _norm_leaf(inherited_path)
    exact = [c for c in candidates if _norm_leaf(c) == want]
    if len(exact) == 1:
        return exact, None
    parts = want.split('_')
    for n in range(len(parts), 0, -1):
        tail = '_'.join(parts[-n:])
        hit = [c for c in candidates if _norm_leaf(c).endswith(tail)]
        if len(hit) == 1:
            return hit, None
        if len(hit) > 1 and _one_effect(hit):
            # Not really a choice: Halo 4 splits some damage effects into an `_enemy`
            # and a `_friendly` copy of the same thing (the Sentinel Beam does). The
            # card means the effect, so it gets both -- and they are separate tag-data
            # blocks, so naming both cannot double-apply.
            return sorted(hit), None
    if _one_effect(candidates):
        # The same case, reached when the Halo 4 leaf was renamed far enough that no
        # tail of the inherited one matches at all: the Sentinel Beam's
        # `sentinel_gun_impact` became `storm_sentinel_beam_beam_{enemy,friendly}`.
        # There is still only one effect here, so there is still nothing to choose.
        return sorted(candidates), None
    return None, ('ambiguous: %s matches %s' %
                  (_leaf(inherited_path),
                   ', '.join(sorted(_leaf(c) for c in candidates))))


def _one_effect(paths):
    """Do these paths differ only by an audience suffix, i.e. name one effect?"""
    stems = set()
    for p in paths:
        leaf = _norm_leaf(p)
        for suf in AUDIENCE_SUFFIXES:
            if leaf.endswith(suf):
                leaf = leaf[:-len(suf)]
                break
        else:
            return False
        stems.add(leaf)
    return len(stems) == 1


def _wild_hits(pattern, names):
    """Does this `*`-wildcard tag path match anything Halo 4 ships?"""
    matcher = halo_patch.hm._wildcard_matcher(pattern)
    return any(matcher(n) for n in names)


# Folders holding damage effects that belong to NO weapon -- the melee set every
# weapon shares. Halo 3 keeps them in objects/weapons/damage_effects and Halo 4 moved
# them to globals/damage_effects, so both spellings have to be recognised on the way in
# AND searched on the way out.
SHARED_ROOTS = ('globals/damage_effects/', 'objects/weapons/damage_effects/')


def _is_shared(path):
    """A damage effect that belongs to the engine rather than to any one weapon.

    Worth its own branch because folder-matching one against the weapon produces
    confident nonsense rather than a failure: `smash_melee` "matched"
    `flak_bolt_explosion`, and wiring that would have made the Flak Cannon's MELEE
    card retune its explosion.
    """
    return any(r in hc._norm(path) for r in SHARED_ROOTS)


def _shared_in_h4(path, names):
    """The Halo 4 tag holding this shared effect, matched by leaf, or None."""
    want = _norm_leaf(path)
    for n in names:
        if _is_shared(n) and _norm_leaf(n) == want:
            return n
    return None


def _fp_wildcard(weapon, cls, have, patterns):
    """`*fp_<name>*` for this weapon's Halo 4 first-person graph, or None.

    Derived from the weapon's own Halo 4 `weap` leaf with the `storm_` prefix taken
    off, because the fp folder tracks the weapon's Halo 4 name and not its Halo 3 one.
    """
    weaps = h4_paths(weapon, 'weap', have, patterns)
    if not weaps:
        return None
    stem = _leaf(weaps[0]).replace('storm_', '')
    pattern = '*fp_%s*' % stem
    return pattern if _wild_hits(pattern, have.get(cls, ())) else None


def campaign_tags():
    """{class: {full tag name}} across every Halo 4 campaign map."""
    have = {}
    for mid, _ in hc.CAMPAIGN:
        m = halo_patch.open_map(os.path.join(hc.MAPS, mid + '.map'), GAME)
        for t in m.tags:
            if t.get('name'):
                have.setdefault(t['class'], set()).add(t['name'])
    return have


def h4_paths(name, cls, have, patterns):
    """The Halo 4 tag paths of class `cls` this weapon name claims, base variant first.

    Sorted by path length so the base (`storm_forerunner_rifle`) leads its own
    variants; a card reads better that way and `find_tags` does not care about order.
    """
    pats = patterns.get(name)
    if not pats:
        return []
    hits = []
    for path in have.get(cls, ()):
        n = hc._norm(path)
        if any(p in n for p in hc.IGNORE_WEAPONS):
            continue
        if any(path.rsplit(SEP, 1)[-1].endswith(x) for x in EXCLUDE_VARIANTS):
            continue
        if any(p in n for p in pats):
            hits.append(path)
    return sorted(hits, key=lambda p: (len(p), p))


def resolve(value, game, order):
    """halo_enhancer.resolve_gamed, kept local so this tool needs no GUI import."""
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


def field_names(target, order):
    f = resolve(target.get('field'), GAME, order)
    if not isinstance(f, str):
        return []
    return [p + f for p in DIFF_PREFIXES] if target.get('diff_prefix_nl') else [f]


def check(weapon, card, have, registry, order, patterns):
    """(ok, tag-or-reason). ok means the tag exists in Halo 4 and every field resolves."""
    inherited = resolve(card.get('tag'), GAME, order)
    if not isinstance(inherited, str) or ' ' not in inherited:
        return False, 'no tag to inherit'
    cls, _, rest = inherited.partition(' ')
    inherited_paths = [p.strip() for p in rest.split('&')]

    if cls in ('matg', 'scnr'):
        # Singletons, resolved by tag-group magic rather than by path, so the
        # inherited string is already correct in every game. Only the FIELDS matter.
        tag = inherited
    elif all(_is_shared(p) for p in inherited_paths):
        # SHARED damage effects, matched by leaf across both spellings of the folder.
        # Halo 4 keeps `strike_melee`, `crush_melee` and `dash_melee` but has no
        # `smash_melee` or `slice_melee`, so a card naming only those is a real
        # decision rather than a rename this tool can make.
        keep = [q for q in (_shared_in_h4(p, have.get(cls, ())) for p in inherited_paths)
                if q]
        if not keep:
            return False, 'shared tag absent in Halo 4: ' + ', '.join(
                _leaf(p) for p in inherited_paths)
        tag = cls + ' ' + ' & '.join(keep)
    elif any('*' in p for p in inherited_paths):
        # A WILDCARD tag, which the animation cards use (`jmad *fp_assault_rifle*`).
        # Halo 4 does ship first-person graphs, under
        # objects/characters/storm_fp/weapons/<cat>/fp_<name>/storm_fp_<name>, so most
        # of these wildcards still hit and the card needs no Halo 4 tag at all.
        #
        # Where the inherited wildcard misses, it is because the WEAPON was renamed,
        # and the fp folder follows the weapon: Halo 4's `storm_br` has `fp_br` and its
        # `storm_fuel_rod_cannon` has `fp_fuel_rod_cannon`, neither of which
        # `*fp_battle_rifle*` or `*fp_flak_cannon*` can match. So derive the Halo 4
        # wildcard from the weapon's own Halo 4 tag rather than keeping a table of
        # renames -- it is the same rename, already resolved once.
        if all('*' not in p or _wild_hits(p, have.get(cls, ())) for p in inherited_paths):
            tag = None                  # inherited wildcard still hits: widen `game`
        else:
            derived = _fp_wildcard(weapon, cls, have, patterns)
            if derived is None:
                return False, 'wildcard matches nothing in Halo 4 (%s %s)' % (
                    cls, ', '.join(inherited_paths))
            tag = cls + ' ' + derived
    else:
        cands = h4_paths(weapon, cls, have, patterns)
        if not cands:
            if weapon not in patterns:
                return False, 'no Halo 4 tag pattern for %s' % weapon
            return False, 'tag absent in Halo 4 (%s)' % cls
        if cls == 'weap' or len(cands) == 1:
            # weap keeps every variant on purpose -- see the module docstring. One
            # candidate needs no narrowing whatever the class.
            paths = cands
        else:
            paths, why = disambiguate(cands, inherited_paths[0])
            if paths is None:
                return False, why
        tag = cls + ' ' + ' & '.join(paths)

    plugin = registry.get(cls)
    if plugin is None:
        return False, 'no %s plugin for Halo 4' % cls
    targets = resolve(card.get('targets'), GAME, order) or []
    if not targets:
        return False, 'no targets for Halo 4'
    bad, good = [], 0
    for t in targets:
        if not isinstance(t, dict):
            continue
        # Targets that do not read a plugin field at all -- the animation scalers and
        # the placement/equipment ops go through their own machinery, so asking the
        # plugin about them would report a working card as broken.
        if any(t.get(k) for k in ('reload_anim', 'swap_anim', 'map_swap',
                                  'map_equip', 'equip_drop', 'choice', 'derived')):
            continue
        blk = resolve(t.get('block'), GAME, order)
        nth = resolve(t.get('nth'), GAME, order) or 0
        names = field_names(t, order)
        if not names:
            bad.append('(unnamed field)')
            continue
        if any(plugin.find(n, blk, nth) for n in names):
            good += 1
        else:
            bad.append(names[0] + (' in %s' % blk if blk else ''))
    if bad:
        # Say how much of the card survives. "1 of 3 fields resolve" is a different
        # and much smaller job than a card Halo 4 has nothing for, and lumping the two
        # together made the backlog unreadable.
        scope = ('field absent (%d of %d resolve)' % (good, good + len(bad))
                 if good else 'field absent')
        return False, scope + ': ' + '; '.join(bad)
    # `None` means "the inherited tag already resolves in Halo 4" -- wire the game
    # list and leave the tag alone.
    return True, tag


# ------------------------------------------------------------------ JSON surgery
#
# halo.json is hand-maintained and heavily commented in its own `desc` fields, so this
# edits the TEXT rather than round-tripping through json.dump, which would reflow all
# 13k lines. Every write is parsed before it is saved.

def _span(lines, i):
    depth, started = 0, False
    for j in range(i, len(lines)):
        depth += lines[j].count('{') - lines[j].count('}')
        if '{' in lines[j]:
            started = True
        if started and depth <= 0:
            return i, j
    return i, len(lines) - 1


def _find(lines, pred, lo, hi):
    for j in range(lo, min(hi, len(lines) - 1) + 1):
        if pred(lines[j]):
            return j
    return None


def _indent(line):
    return line[:len(line) - len(line.lstrip())]


def wire_card(lines, weapon, card, tag, order):
    """Add Halo 4 to one card. Returns True if anything changed."""
    w = _find(lines, lambda l: l.strip() == '"%s": {' % weapon, 0, len(lines) - 1)
    if w is None:
        return False
    ws, we = _span(lines, w)
    c = _find(lines, lambda l: l.strip() == '"%s": {' % card, ws, we)
    if c is None:
        return False
    cs, ce = _span(lines, c)
    changed = False
    jtag = json.dumps(tag, ensure_ascii=False) if tag else None

    # --- game: add Halo 4 to the allow list. NO `game` key means "every game", which
    # already includes Halo 4 -- adding one would NARROW the card, not widen it.
    g = _find(lines, lambda l: l.strip().startswith('"game":'), cs, ce)
    if g is not None and '"Halo 4"' not in lines[g]:
        if '[' not in lines[g]:
            head, _, rest = lines[g].partition(':')
            trail = ',' if rest.rstrip().endswith(',') else ''
            lines[g] = '%s: [%s, "Halo 4"]%s' % (head, rest.strip().rstrip(','), trail)
        elif lines[g].rstrip().rstrip(',').endswith(']'):
            lines[g] = lines[g].replace(']', ', "Halo 4"]', 1)
        else:
            ge = _find(lines, lambda l: l.strip().startswith(']'), g, ce)
            lines[ge - 1] = lines[ge - 1].rstrip() + ','
            lines.insert(ge, _indent(lines[ge - 1]) + '"Halo 4"')
            ce += 1
        changed = True

    # --- tag. `jtag` is None when the inherited tag already resolves in Halo 4 (a
    # wildcard that still matches): widening `game` is the whole edit.
    t = _find(lines, lambda l: l.strip().startswith('"tag":'), cs, ce)
    if t is None or jtag is None:
        return changed
    stripped = lines[t].strip()
    if '"Halo 4"' in lines[t]:
        return changed
    if lines[t].rstrip().endswith('{'):
        # multi-line per-game dict: add a row before the close
        ts, te = _span(lines, t)
        if not any('"Halo 4"' in lines[k] for k in range(ts, te + 1)):
            lines[te - 1] = lines[te - 1].rstrip() + ','
            lines.insert(te, _indent(lines[te - 1]) + '"Halo 4": ' + jtag)
            ce += 1
            changed = True
    elif stripped.startswith('"tag": {'):
        # one-line per-game dict: insert before the last closing brace
        i = lines[t].rfind('}')
        lines[t] = lines[t][:i].rstrip().rstrip(',') + ', "Halo 4": ' + jtag + lines[t][i:]
        changed = True
    else:
        # a PLAIN STRING tag, which applies to every game. Promote it to a dict with
        # the old string under `default` -- resolve_gamed checks the exact game first
        # and `default` second, so every other game keeps exactly what it had.
        head, _, rest = lines[t].partition(':')
        trail = ',' if rest.rstrip().endswith(',') else ''
        old = rest.strip().rstrip(',')
        lines[t] = '%s: {"default": %s, "Halo 4": %s}%s' % (head, old, jtag, trail)
        changed = True

    # --- targets: mirror the inherited game's array when targets are per-game
    tg = _find(lines, lambda l: l.strip().startswith('"targets":'), cs, ce)
    if tg is not None and lines[tg].rstrip().endswith('{'):
        gs, ge2 = _span(lines, tg)
        if not any('"Halo 4"' in lines[k] for k in range(gs, ge2 + 1)):
            src = None
            for g2 in reversed(order[:order.index(GAME)]):
                k = _find(lines, lambda l, gg=g2: l.strip().startswith('"%s": [' % gg),
                          gs, ge2)
                if k is not None:
                    src = k
                    break
            if src is not None:
                se = _find(lines, lambda l: l.strip().startswith(']'), src, ge2)
                body = list(lines[src:se + 1])
                ind = _indent(body[0])
                body[0] = ind + '"Halo 4": ['
                if not body[-1].rstrip().endswith(','):
                    body[-1] = body[-1].rstrip() + ','
                lines[src:src] = body
                changed = True
    return changed


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true', help='write the Halo 4 entries')
    ap.add_argument('--show-ok', action='store_true', help='list the passing cards too')
    ap.add_argument('--variants', action='store_true',
                    help='print the tag map, including what is excluded')
    a = ap.parse_args()

    doc = json.load(open(HALO_JSON, encoding='utf-8'))
    order = list(doc['Missions'])
    sw = doc['Player Modifiers']['Specific Weapon Modifier']
    names = set()
    for mm in doc['Missions'][GAME].values():
        for k in ('weapons', 'turrets', 'grenades'):
            names |= set(mm.get(k) or [])
    names = {ALIAS.get(n, n) for n in names}

    print('resolving Halo 4 tags across %d campaign maps...' % len(hc.CAMPAIGN))
    have = campaign_tags()
    patterns = tag_patterns()
    registry = halo_patch.PluginRegistry(PLUGINS, SUBDIRS)

    if a.variants:
        for name in sorted(names):
            rows = [(cls, p) for cls in sorted(have)
                    for p in h4_paths(name, cls, have, patterns)]
            print('=== %s' % name)
            if not rows:
                print('    (no Halo 4 tag matches this name)')
            for cls, p in rows:
                print('    %-5s %s' % (cls, p))
        excluded = sorted({p for cls in have for p in have[cls]
                           if any(p.rsplit(SEP, 1)[-1].endswith(x)
                                  for x in EXCLUDE_VARIANTS)})
        print('\n=== excluded variants (%d)' % len(excluded))
        for p in excluded:
            print('    %s' % p)
        return

    ok, bad, skipped, missing = [], [], [], sorted(names - set(sw))
    for weapon in sorted(names & set(sw)):
        for cname, card in sw[weapon].items():
            if not isinstance(card, dict):
                continue
            if isinstance(card.get('tag'), dict) and GAME in card['tag']:
                continue                                # already wired
            why_skip = skip_reason(weapon, cname)
            if why_skip:
                skipped.append((weapon, cname, why_skip))
                continue
            good, why = check(weapon, card, have, registry, order, patterns)
            (ok if good else bad).append((weapon, cname, why))

    print('\n=== would wire (%d) ===' % len(ok))
    if a.show_ok:
        for w, n, tag in ok:
            shown = tag.split(' ', 1)[1][:78] if tag else '(inherited tag already resolves)'
            print('   %-16s %-26s %s' % (w, n, shown))
    else:
        byw = {}
        for w, n, _ in ok:
            byw.setdefault(w, []).append(n)
        for w in sorted(byw):
            print('   %-16s %d: %s' % (w, len(byw[w]), ', '.join(sorted(byw[w]))))

    print('\n=== needs real work (%d) ===' % len(bad))
    byreason = {}
    for w, n, why in bad:
        byreason.setdefault(why.split(':')[0], []).append('%s/%s' % (w, n))
    for r in sorted(byreason):
        print('   %-34s %3d  e.g. %s' % (r, len(byreason[r]), ', '.join(byreason[r][:3])))

    if skipped:
        print('\n=== deliberately NOT wired (%d) ===' % len(skipped))
        byc = {}
        for w, n, why in skipped:
            byc.setdefault((n, why), []).append(w)
        for key in sorted(byc):
            print('   %s (%d weapons)\n      %s' % (key[0], len(byc[key]), key[1]))

    if missing:
        print('\n=== Halo 4 weapons with NO card entry at all (%d) ===' % len(missing))
        print('   ' + ', '.join(missing))
        print('   (authoring, not wiring -- nothing here to inherit)')

    if not a.apply:
        print('\n(report only -- pass --apply to write the Halo 4 entries)')
        return
    lines = open(HALO_JSON, encoding='utf-8').read().split('\n')
    written = 0
    for w, n, tag in ok:
        if wire_card(lines, w, n, tag, order):
            written += 1
    out = '\n'.join(lines)
    json.loads(out)                      # refuse to write anything unparseable
    open(HALO_JSON, 'w', encoding='utf-8', newline='').write(out)
    print('\nwired %d card(s) into halo.json' % written)


if __name__ == '__main__':
    main()
