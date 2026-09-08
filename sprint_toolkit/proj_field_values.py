"""Value spread for the proj fields under consideration, per game and per weapon.

The question a card has to answer is not "does the field exist" but "does it vary
across weapons in a way a player would feel". So this prints the distinct values and
which projectiles hold them, and separates PLAYER-carried weapons from vehicle guns,
because a field only vehicles set is not worth a weapon card.
"""
import collections
import io
import json
import os
import sys

TOOL = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool"
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
import halo_patch as hp
import h4_census as hc
import h4_wire_weapons as W

SEP = chr(92)
P = r'F:\SteamLibrary\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins'
ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection"
GAMES = [
    ('Halo 3', ['Halo3MCC', 'Halo3'], os.path.join(ROOT, 'halo3', 'maps'),
     ['010_jungle', '030_outskirts', '070_waste', '120_halo']),
    ('Halo Reach', ['ReachMCC', 'Reach'], os.path.join(ROOT, 'haloreach', 'maps'),
     ['m10', 'm20', 'm30', 'm35', 'm45', 'm50', 'm52', 'm60', 'm70']),
    ('Halo 4', ['Halo4MCC', 'Halo4'], hc.MAPS, [m for m, _t in hc.CAMPAIGN]),
]
AI = ['AI Normal Velocity Scale', 'AI Heroic Velocity Scale',
      'AI Legendary Velocity Scale', 'AI Normal Guided Angular Velocity Scale',
      'AI Legendary Guided Angular Velocity Scale']
CAND = [('Targeted Leading Fraction', None), ('Minimum Velocity', None),
        ('Arming Time', None),
        ('Chance Fraction', 'Material Response'),
        ('And Velocity', 'Material Response'),
        ('Parallel Friction', 'Material Response'),
        ('Perpendicular Friction', 'Material Response')]
# projectile folders the player actually shoots
PLAYER = ('weapons' + SEP + 'rifle', 'weapons' + SEP + 'pistol',
          'weapons' + SEP + 'support_high', 'weapons' + SEP + 'support_low',
          'weapons' + SEP + 'shotgun', 'weapons' + SEP + 'grenade',
          'weapons' + SEP + 'melee', 'weapons' + SEP + 'sniper', 'weapons' + SEP + 'smg')


def is_player(path):
    return any(p in path for p in PLAYER)


for game, subs, mapdir, maps in GAMES:
    pl = hp.PluginRegistry(P, subs).get('proj')
    seen = {}
    for mid in maps:
        fp = os.path.join(mapdir, mid + '.map')
        if not os.path.exists(fp):
            print('   !! missing map %s' % fp)
            continue
        m = hp.open_map(fp, game)
        for t in m.tags:
            n = t['name'] or ''
            if t['class'] != 'proj' or t['base'] is None or n in seen:
                continue
            row = {}
            for f in AI:
                row[f] = m.read_tag_field(t['base'], f, pl, None, 0)
            for f, b in CAND:
                row[f] = m.read_tag_field(t['base'], f, pl, b, 0)
            seen[n] = row
    print('=' * 78)
    print('%s -- %d projectiles' % (game, len(seen)))
    nset = sum(1 for r in seen.values() if any(r.get(f) not in (None, 0, 0.0) for f in AI))
    print('   AI velocity/guided ladder: %d projectile(s) set at least one' % nset)
    for f, b in CAND:
        vals = collections.Counter()
        players = collections.Counter()
        for n, r in seen.items():
            v = r.get(f)
            if v in (None, 0, 0.0):
                continue
            vals[round(v, 4) if isinstance(v, float) else v] += 1
            if is_player(n):
                players[round(v, 4) if isinstance(v, float) else v] += 1
        if not vals:
            print('   %-26s %-18s -- zero/absent on every projectile' % (f, b or ''))
            continue
        top = ', '.join('%s x%d' % (k, c) for k, c in vals.most_common(6))
        who = [n.rsplit(SEP, 1)[-1] for n in seen
               if is_player(n) and seen[n].get(f) not in (None, 0, 0.0)]
        print('   %-26s %-18s %2d proj (%d player): %s'
              % (f, b or '', sum(vals.values()), sum(players.values()), top))
        if who:
            print('        player weapons: %s' % ', '.join(sorted(who)[:8]))
