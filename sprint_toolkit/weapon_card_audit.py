r"""Does a weapon card actually LAND on the maps that offer that weapon?

A card can pass every review and still do nothing in play, because "the effect is in
halo.json" and "the field exists in this map's copy of the tag" are different questions.
This asks the second one, per game, per map, using the same resolution the patcher does.

Two checks, chosen because they fail in two different ways:

  --check zoom     resolve `Magnification Levels` / `Magnification Range` on the
                   weapon's `weap` tag and print the CURRENT value. A `weap` tag the
                   map does not carry, or a field the plugin does not define, shows up
                   as `unresolved` rather than as a silent no-op at patch time.

  --check reload   the reload cards do not write a tag field at all: MCC reloads by
                   first-person ANIMATION, so the card scales the jmad (Halo 2/3/ODST)
                   or antr (Halo 1) reload animations. The only meaningful test is
                   whether `halo3_reload.reload_frames` finds any reload animation for
                   that graph in that map -- if it finds none, the card reports success
                   and changes nothing.

    python weapon_card_audit.py --check reload
    python weapon_card_audit.py --check zoom --game "Halo 3"
    python weapon_card_audit.py --check reload --all      # every map, not a summary

Reads only. MCC may be running.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import assembly_plugins
import halo_patch as HP                                          # noqa: E402
import halo3_reload as RL                                        # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import map_vault as V                                            # noqa: E402

# Resolved rather than hardcoded: Assembly moved off the Steam drive and every
# CLI tool that had the old path baked in stopped finding it.
PLUGINS = assembly_plugins.plugins_dir()
SUBDIRS = {'Halo 1': ['Halo1MCC', 'Halo1'], 'Halo 2': ['Halo2MCC', 'Halo2'],
           'Halo 3': ['Halo3MCC', 'Halo3'], 'Halo 3: ODST': ['ODSTMCC', 'ODST'],
           'Halo Reach': ['ReachMCC', 'Reach']}
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HALO_JSON = os.path.join(TOOL, 'halo.json')

# halo.json's mission weapon lists use the in-game names; the effect keys use the
# toolkit's. Only where they differ.
ALIASES = {'Magnum': 'Pistol', 'Auto Magnum': 'Pistol', 'Silenced SMG': 'SMG'}


def _resolve(value, game, order):
    """halo_enhancer.resolve_gamed: exact match, else the nearest EARLIER game."""
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


def _games_of(card):
    g = card.get('game')
    if g is None:
        return None                     # every game
    return [g] if isinstance(g, str) else list(g)


def _offered_on(mission, weapon):
    """Does this mission list the weapon, under any of its names?"""
    listed = []
    for key in ('weapons', 'turret', 'grenades'):
        listed += mission.get(key) or []
    return any(ALIASES.get(n, n) == weapon for n in listed)


def audit(game, data, check, show_all):
    order = list(data['Missions'])
    reg = HP.PluginRegistry(PLUGINS, SUBDIRS[game])
    swm = data['Player Modifiers']['Specific Weapon Modifier']
    card_name = 'Zoom' if check == 'zoom' else 'Reload Time'

    rows = {}                           # weapon -> {verdict: [mission ids]}
    for mid, mission in data['Missions'][game].items():
        path = V.resolve(game, mid)
        if not path:
            continue
        m = None
        for weapon, entry in swm.items():
            card = entry.get(card_name)
            if not card:
                continue
            games = _games_of(card)
            # ODST inherits Halo 3's effects, the same way the patcher does.
            reach = games is None or game in games or (
                game == 'Halo 3: ODST' and 'Halo 3' in games)
            if not reach or not _offered_on(mission, weapon):
                continue
            tag = _resolve(card.get('tag'), game, order)
            if not tag:
                rows.setdefault(weapon, {}).setdefault('no tag for this game', []).append(mid)
                continue
            if m is None:
                m = HP.open_map(path, game)
            cls, rest = tag.split(' ', 1)
            verdict = (_zoom_verdict if check == 'zoom' else _reload_verdict)(
                m, reg, game, cls, rest, card, order)
            rows.setdefault(weapon, {}).setdefault(verdict, []).append(mid)

    print("== %s" % game)
    for weapon in sorted(rows):
        for verdict, mids in sorted(rows[weapon].items()):
            flag = ' ' if verdict.startswith('ok') else '!'
            shown = (", ".join(mids) if show_all or len(mids) <= 4
                     else "%s \u2026 (%d maps)" % (", ".join(mids[:4]), len(mids)))
            print("  %s %-18s %-34s %s" % (flag, weapon, verdict, shown))


def _zoom_verdict(m, reg, game, cls, rest, card, order):
    plugin = reg.get(cls)
    if plugin is None:
        return 'no %s plugin' % cls
    # A card may name several tags with ' & '; every one has to resolve.
    vals, bad = [], []
    for part in rest.split(' & '):
        part = part.strip()
        if not m.find_tags(cls, part):
            bad.append('tag absent')
            continue
        v = m.read_first(cls, part, 'Magnification Levels', plugin)
        if v is None:
            bad.append('field unresolved')
        else:
            vals.append(v)
    if bad:
        return 'MISSING: ' + ', '.join(sorted(set(bad)))
    return 'ok (levels now %s)' % ('/'.join(str(v) for v in sorted(set(vals))))


def _reload_verdict(m, reg, game, cls, rest, card, order):
    """The reload card scales animations, so ask the animation reader directly."""
    if not any(t.get('reload_anim') for t in (card.get('targets') or [])):
        return 'not an animation card \u2014 check by hand'
    if cls not in ('jmad', 'antr'):
        return 'unexpected tag class %s' % cls
    try:
        found = RL.reload_frames(m, rest, game=game)
    except Exception as e:
        return 'ERROR %s' % e
    if not found:
        # Distinguish "no such graph in this map" from "graph has no reload animation":
        # the first is a wrong tag pattern, the second a weapon that does not reload.
        if not m.find_tags(cls, rest):
            return 'MISSING: no %s graph matches' % cls
        return 'MISSING: graph has no reload animation'
    frames = sorted({f for _who, fs in found for f in fs})
    return 'ok (%d graph(s), %s frames)' % (
        len(found), '/'.join(str(f) for f in frames[:4]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', choices=('zoom', 'reload'), default='reload')
    ap.add_argument('--game', action='append', choices=sorted(SUBDIRS))
    ap.add_argument('--all', action='store_true', help='list every map, not a summary')
    a = ap.parse_args(argv)
    with open(HALO_JSON, encoding='utf-8') as f:
        data = json.load(f)
    for game in (a.game or list(data['Missions'])):
        audit(game, data, a.check, a.all)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
