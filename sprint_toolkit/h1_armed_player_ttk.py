r"""What an ARMED enemy's port does to the PLAYER (read-only) -- the numbers a step-11 WDM decision asks
for ('a one-hit weapon in enemy hands: show me the Legendary numbers', the Binary Rifle, C6 2026-10-16).
Per hit = the damage effect's upper bound x its cyborg shield / armour modifier x the actor's Weapon Damage
Modifier x the globals' enemy DAMAGE scale per difficulty; against the cyborg's shield + body (the
collision model). Direct hits only; shield recharge and headshots not simulated.

    python h1_armed_player_ttk.py "<damage effect>" <wdm> [<wdm> ...] [--dmg 162.9]
    e.g. python h1_armed_player_ttk.py "weapons\binary rifle\bullet" 0.626 0.323 0.4
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.coll import coll_def  # noqa: E402
from reclaimer.hek.defs.jpt_ import jpt__def  # noqa: E402
from reclaimer.hek.defs.matg import matg_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
DIFF = ('easy', 'normal', 'heroic', 'legendary')


def hits(per_shield, per_body, shield, body):
    """Shots to kill: the shield first, the killing shot's overflow carried to the body (body modifier)."""
    n, s, b = 0, shield, body
    while b > 0:
        n += 1
        if s > 0:
            over = per_shield - s
            s -= per_shield
            if over > 0:
                b -= over / per_shield * per_body
        else:
            b -= per_body
        if n > 99:
            return None
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('jpt')
    ap.add_argument('wdm', nargs='+', type=float)
    ap.add_argument('--dmg', type=float, help='damage a hit instead of the tag upper bound (a balanced row)')
    a = ap.parse_args()
    g = matg_def.build(filepath=os.path.join(TAGS, r'globals\globals.globals')).data.tagdata
    dmg_scale = list(g.difficulties.STEPTREE[0].enemy_scales.damage)
    c = coll_def.build(filepath=os.path.join(TAGS, r'characters\cyborg\cyborg.model_collision_geometry')).data.tagdata
    body, shield = c.body.maximum_body_vitality, c.shield.maximum_shield_vitality
    j = jpt__def.build(filepath=os.path.join(TAGS, a.jpt + '.damage_effect')).data.tagdata
    dmg = a.dmg or max(j.damage.damage_upper_bound)
    ms, mb = j.damage_modifiers.cyborg_energy_shield, j.damage_modifiers.cyborg_armor
    print('%s: %.1f a hit, cyborg shield x%g / armour x%g; player %g shield + %g body; enemy damage %s'
          % (a.jpt, dmg, ms, mb, shield, body, dict(zip(DIFF, [round(x, 2) for x in dmg_scale]))))
    for w in a.wdm:
        row = []
        for d, k in zip(DIFF, dmg_scale):
            per = dmg * w * k
            row.append('%s %.1f (%s)' % (d, per, hits(per * ms, per * mb, shield, body)))
        print('  WDM %-6g ' % w + ' | '.join(row) + '   -- per hit (hits to kill)')


if __name__ == '__main__':
    main()
