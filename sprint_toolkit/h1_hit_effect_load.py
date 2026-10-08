r"""Halo 1: the SHIELD-HIT effect on the player, per weapon, and THE HIT-EFFECT RULE.

A projectile hitting the player plays the projectile's own response effect for the player's
material (the same table it uses on walls): shielded = material #22 `cyborg energy shield`.
Stock Halo 1 never scales it by fire rate -- the AR's 49-particle shield hit plays at 15/s --
and the ports inherit their donor's. At a high rate it covers the view (the Spike Rifle's
Armed test, 2026-10-08).

  load per hit = sum over the effect's particles of created count x mean radius^2
  load per second = load per hit x rounds/s x projectiles per shot

THE RULE (user, 2026-10-08), v2: 'the higher the fire rate, the smaller the effect'. The donor's
per-hit load is kept up to the stock pistol's RATE (3.5/s); above it, it falls as (3.5 / rate)^K,
K = 3.19 fitted to the user's APPROVED Spike Rifle effect (12/s: 2% of the AR's load). The
effect shrinks in SIZE only (scale = sqrt of the load factor). The rate is the higher of the
port's default and balanced rates. v1 (a load-per-second budget = the stock pistol's 4.36) was
too big (user). Ports apply it with h1_pickable_weapons `bullet.impact_thin` {'materials': [22],
'thin': {}, 'rate': r}.

    python h1_hit_effect_load.py            the table: every stock weapon + every Halo 1 port,
                                            its load per second and the rule's size scale
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.weap import weap_def  # noqa: E402
from reclaimer.hek.defs.proj import proj_def  # noqa: E402
from reclaimer.hek.defs.effe import effe_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
SHIELD = 22                                  # Halo 1 material: cyborg energy shield
BUDGET = 1.2461 * 3.5                        # the stock pistol's load per second (4.36)
# rates MEASURED in game where the tag's is capped (PORTING: the 15/s observation)
SAW = r'weapons\saw\saw'
MEASURED = {r'weapons\smg\smg': 15.0, r'weapons\saw\saw': 15.0, r'weapons\sentinel beam\sentinel beam': 15.0}


def effect_load(effect):
    """(load per hit, particle count) of one effect tag (path without extension)."""
    if not effect:
        return 0.0, 0
    e = effe_def.build(filepath=os.path.join(TAGS, effect + '.effect')).data.tagdata
    tot, n = 0.0, 0
    for ev in e.events.STEPTREE:
        for q in ev.particles.STEPTREE:
            c = (q.created_count[0] + q.created_count[1]) / 2.0
            r = (q.radius[0] + q.radius[1]) / 2.0
            tot += c * r * r
            n += int(round(c))
    return tot, n


# THE RULE, v2 (user, 2026-10-08: 'the pistol budget keeps the effect too big -- a steeper
# curve'): the donor's per-hit load is kept up to the stock pistol's RATE, above it it falls as
# (FREE_RATE / rate)^K. K is fitted to the user's APPROVED Spike Rifle effect (the AR's shield
# hit, every 4th spark at x0.25 size: 0.0118 of 0.6015 per hit = 0.0196 at 12/s) -> K = 3.19
FREE_RATE = 3.5
ANCHOR_RATE, ANCHOR_FACTOR = 12.0, 0.0118 / 0.6015
K = math.log(ANCHOR_FACTOR) / math.log(FREE_RATE / ANCHOR_RATE)


def load_factor(rate, per_shot=1):
    """The share of the donor's per-hit load THE RULE keeps at `rate` rounds/s (pellets count
    as rate: a shotgun's 15 pellets hit at once)."""
    r = rate * per_shot
    return 1.0 if r <= FREE_RATE or r <= 0 else (FREE_RATE / r) ** K


def rule_scale(effect, rate, per_shot=1, budget=None):
    """The SIZE scale THE RULE gives an effect fired at `rate` rounds/s (load ~ size^2).
    `budget` is the v1 rule (a load per second cap), kept for comparison only."""
    if budget:
        load, _n = effect_load(effect)
        per_s = load * rate * per_shot
        return 1.0 if per_s <= budget or per_s <= 0 else math.sqrt(budget / per_s)
    return math.sqrt(load_factor(rate, per_shot))


def thin_effect(spec, src_e):
    """An OWN copy of the response effect `src_e` for `bullet.impact_thin` `spec`:
    {'out': folder, 'thin': {particle path substring: keep every n-th}, 'rate': r (THE RULE's
    size), or 'scale': s by hand, 'per_shot', 'budget' (v1), 'from': the DONOR's effect --
    for a writer that edits the port's projectile in place (the SAW's saw_port_values.py):
    a second run would otherwise scale the own copy again}.
    Returns (effect tag, own path, particles kept, particles thinned) -- the caller saves it."""
    src_e = spec.get('from') or src_e
    scale = spec.get('scale', 1.0)
    if spec.get('rate'):
        # THE HIT-EFFECT RULE (user, 2026-10-08; v2 'steeper'): the donor's load kept up to
        # the pistol's rate, above it x (3.5 / rate)^3.19 -- size = sqrt of that
        scale = rule_scale(src_e, spec['rate'], spec.get('per_shot', 1), spec.get('budget'))
        print('   hit-effect rule: %s at %.1f/s -> size x%.3f' % (src_e, spec['rate'], scale))
    et = effe_def.build(filepath=os.path.join(TAGS, src_e + '.effect'))
    kept = total = 0
    for ev in et.data.tagdata.events.STEPTREE:
        pts = ev.particles.STEPTREE
        seen = {}
        for k in range(len(pts) - 1, -1, -1):
            key = next((s for s in spec['thin'] if s in pts[k].particle_type.filepath), None)
            if key is None:
                continue
            total += 1
            seen[key] = seen.get(key, -1) + 1
            if seen[key] % spec['thin'][key]:
                pts.pop(k)
            else:
                kept += 1
        for q in pts:                             # the size: every remaining particle's radius
            q.radius[0], q.radius[1] = q.radius[0] * scale, q.radius[1] * scale
    return et, spec['out'] + src_e.rsplit('\\', 1)[-1], kept, total


def weapon_row(weapon, rate=None):
    a = weap_def.build(filepath=os.path.join(TAGS, weapon + '.weapon')).data.tagdata.weap_attrs
    tr = a.triggers.STEPTREE[0]
    rate = rate or MEASURED.get(weapon) or max(tr.firing.rounds_per_second)
    pps = tr.projectile.projectiles_per_shot or 1
    pr = proj_def.build(filepath=os.path.join(TAGS, tr.projectile.projectile.filepath + '.projectile')).data.tagdata
    eff = pr.proj_attrs.material_responses.STEPTREE[SHIELD].effect.filepath
    load, n = effect_load(eff)
    return rate, pps, n, load, eff


def main():
    stock = ['pistol\\pistol', 'assault rifle\\assault rifle', 'plasma pistol\\plasma pistol',
             'plasma rifle\\plasma rifle', 'needler\\needler', 'shotgun\\shotgun', 'sniper rifle\\sniper rifle']
    rows = [('weapons\\' + w, 'stock', None) for w in stock]
    import ports_h1
    for key, P in ports_h1.all_ports():
        w = (P.get('pickable') or {}).get('weapon')
        if w and os.path.exists(os.path.join(TAGS, w + '.weapon')):
            thin = (P['pickable'].get('bullet') or {}).get('impact_thin') or {}
            rows.append((w, key, thin.get('rate')))
    # the SAW: built by its own writers (saw_port_values.py applies the rule), not a pickable
    if os.path.exists(os.path.join(TAGS, SAW + '.weapon')):
        from ports_h1 import saw
        rows.append((SAW, 'saw (own writer)', saw.PORT['impact_thin']['rate']))
    print('THE RULE v2: load kept up to %.1f/s, above x (%.1f / rate)^%.2f (fitted to the approved '
          'Spike Rifle)\n' % (FREE_RATE, FREE_RATE, K))
    print('%-42s %-16s %6s %4s %5s %9s %9s %7s  %s' % ('weapon', 'config', 'rate', 'x', 'parts', 'load/hit',
                                                      'load/s', 'scale', 'shield-hit effect'))
    for w, key, applied in rows:
        rate, pps, n, load, eff = weapon_row(w, applied)
        key += ' *' if applied else ''
        per_s = load * rate * pps
        sc = math.sqrt(load_factor(rate, pps))
        print('%-42s %-16s %6.1f %4d %5d %9.4f %9.3f %7.3f  %s' % (w, key, rate, pps, n, load, per_s, sc, eff))
    print('\n(rates: the tag maximum, or MEASURED; * = the port APPLIES the rule at this rate, its '
          "impact_thin\n'rate' = max(default, balanced) -- its load/hit is then its own, already shrunk "
          "effect.\nFuel Rod: the tag's 10/s is never fired (1.25 s charge; balanced 2.5/s), see PORTING "
          '"Balance")')


if __name__ == '__main__':
    main()
