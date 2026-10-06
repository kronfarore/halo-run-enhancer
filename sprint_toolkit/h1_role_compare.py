r"""HALO 1 role comparison + time to kill: does a port (or a restored weapon) play like it
belongs between the Halo 1 weapons of its role? The Halo 1 counterpart of
port_role_compare.py / port_ttk.py (those read the Halo 4 / Reach kits through
`tool export-tag-to-xml` and Halo 4's damage tables; Halo 1 needs neither).

Everything is read from HCEEK tags with Reclaimer:
  weapon      trigger 0: rounds per second, charging time, projectiles / rounds per shot;
              magazine 0; aim assist; melee damage effect; first-person reload / ready
              animation lengths (30 fps)
  damage      the projectile's IMPACT damage effect plus every damage effect its detonation
              effect fires (the explosion); a damage effect's damage = the mean of its upper
              bounds (a direct hit), x its per-MATERIAL modifier, its radius = splash
  enemies     body / shield from the actor variant (when it overrides) else the collision
              model, x the globals' difficulty scales (normal 1.0, legendary 1.4 / 1.4 on
              vitality / shield); the shield takes the shield material's modifier, the
              overflow of the killing shot carries to the body at the body's
  time        charge + one interval per further shot + a reload whenever the magazine is
              empty (the reload animation's length). Melee: one swing per melee animation.

STATED ASSUMPTIONS: direct hits only (splash is listed, not simulated); no headshots; a
damage effect's lower bound (the far edge of splash) is ignored; Halo 1 shields recharge
is not simulated (a burst from cold).

    python h1_role_compare.py flak_cannon [--balanced]
    python h1_role_compare.py energy_blade [--balanced]
    python h1_role_compare.py sentinel_beam [--balanced]

A weapon entry may carry a 4th element {'rate': rounds/s}: the rate MEASURED in game,
used instead of the tag's (the Sentinel Beam's 30/s fires 15/s, PORTING.md). Stock
weapons keep their tag rate: the tick rule is an observation on one weapon, unverified on
the others. A weapon with heat or battery also gets a sustained-fire table.

--balanced applies the catalog's balance rows (weapon_ports_catalog.json, Halo 1) the
fields this tool knows -- what the enhancer's per-port Balanced box turns on.
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.weap import weap_def  # noqa: E402
from reclaimer.hek.defs.proj import proj_def  # noqa: E402
from reclaimer.hek.defs.jpt_ import jpt__def  # noqa: E402
from reclaimer.hek.defs.effe import effe_def  # noqa: E402
from reclaimer.hek.defs.actv import actv_def  # noqa: E402
from reclaimer.hek.defs.coll import coll_def  # noqa: E402
from reclaimer.hek.defs.antr import antr_def  # noqa: E402
from reclaimer.hek.defs.matg import matg_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
CATALOG = os.path.join(os.path.dirname(HERE), 'weapon_ports_catalog.json')
B = '\\'
W = 'weapons' + B

SETS = {
    # the restored fuel rod against the explosive power weapons of Halo 1
    'flak_cannon': {'port': 'Flak Cannon', 'weapons': [
        ('Fuel Rod (restored)', W + r'fuel rod gun\fuel rod', 'shot'),
        ('Rocket Launcher', W + r'rocket launcher\rocket launcher', 'shot'),
        ('PC Fuel Rod (MP)', W + r'plasma_cannon\plasma_cannon', 'shot'),
    ]},
    # the restored sword: its slash and lunge against every other way Halo 1 kills up close
    'energy_blade': {'port': 'Energy Blade', 'weapons': [
        ('Sword slash (restored)', W + r'energy sword\energy sword', 'melee'),
        ('Sword lunge (restored)', W + r'energy sword\energy sword', 'shot'),
        ('Shotgun', W + r'shotgun\shotgun', 'shot'),
        ('Shotgun melee', W + r'shotgun\shotgun', 'melee'),
        ('Assault Rifle melee', W + r'assault rifle\assault rifle', 'melee'),
        ('Rocket Launcher melee', W + r'rocket launcher\rocket launcher', 'melee'),
        ('Oddball melee', W + r'ball\ball', 'melee'),
    ]},
    # the Sentinel Beam (a full Halo 3 port) against Halo 1's SENTINEL GUN -- the direct
    # yardstick: Halo 3's Sentinels carry the player's own sentinel_gun, so the H1 player
    # beam = the H1 Sentinel gun x 1 for damage / rate / range -- and the automatics of
    # Halo 1. Both Sentinel weapons are tagged 30/s and fire 15/s (measured on the port).
    'sentinel_beam': {'port': 'Sentinel Beam', 'weapons': [
        ('Sentinel Beam (port)', W + r'sentinel beam\sentinel beam', 'shot', {'rate': 15.0}),
        ('Sentinel gun (H1 AI)', r'characters\sentinel\sentinel', 'shot', {'rate': 15.0}),
        ('Plasma Rifle', W + r'plasma rifle\plasma rifle', 'shot'),
        ('Assault Rifle', W + r'assault rifle\assault rifle', 'shot'),
        ('Needler', W + r'needler\needler', 'shot'),
        ('Pistol', W + r'pistol\pistol', 'shot'),
    ], 'enemies': [
        ('Flood combat (elite)', r'characters\floodcombat elite\floodcombat elite plasma rifle',
         'floodcombat elite'),
        ('Sentinel', r'characters\sentinel\sentinel', 'sentinel'),
        ('Sentinel (shielded)', r'characters\sentinel\sentinel_shielded', 'sentinel'),
    ]},
}

ENEMIES = [
    ('Grunt minor', r'characters\grunt\grunt minor plasma pistol', 'grunt'),
    ('Jackal (body)', r'characters\jackal\jackal minor plasma pistol', 'jackal'),
    ('Elite minor', r'characters\elite\elite minor\elite minor plasma rifle', 'elite'),
    ('Elite major', r'characters\elite\elite major\elite major plasma rifle', 'elite'),
    ('Elite commander', r'characters\elite\elite commander\elite commander plasma rifle', 'elite'),
    ('Hunter (armour)', r'characters\hunter\hunter', 'hunter'),
    ('Flood combat (human)', r'characters\floodcombat_human\floodcombat_human', 'floodcombat_human'),
]


def load(defn, rel, ext):
    p = os.path.join(TAGS, rel + ext)
    return defn.build(filepath=p).data.tagdata if os.path.exists(p) else None


def damage(rel):
    """{'dmg', 'radius', 'mods': {material: x}} of one damage effect."""
    j = load(jpt__def, rel, '.damage_effect')
    if j is None:
        return None
    up = j.damage.damage_upper_bound
    mods = {k: getattr(j.damage_modifiers, k) for k in j.damage_modifiers.desc['NAME_MAP']}
    return {'tag': rel, 'dmg': (up[0] + up[1]) / 2.0, 'radius': (j.radius[0], j.radius[1]),
            'mods': mods}


def projectile_damage(rel):
    """Every damage a projectile deals on a direct hit: impact + its detonation's parts."""
    p = load(proj_def, rel, '.projectile')
    if p is None:
        return [], None
    out = []
    ph = p.proj_attrs.physics
    if ph.impact_damage.filepath:
        out.append(damage(ph.impact_damage.filepath))
    eff = p.proj_attrs.detonation.effect.filepath
    if eff:
        e = load(effe_def, eff, '.effect')
        for ev in (e.events.STEPTREE if e else []):
            for part in ev.parts.STEPTREE:
                if part.type.tag_class.enum_name == 'damage_effect':
                    out.append(damage(part.type.filepath))
    # a 0-damage part (Halo 1's shared frag-grenade 'shock wave', radius 8) only shoves
    return [d for d in out if d and d['dmg'] > 0], p


def anim_seconds(rel, names):
    a = load(antr_def, rel, '.model_animations') if rel else None
    if a is None:
        return None
    for anim in a.animations.STEPTREE:
        if anim.name in names:
            return anim.frame_count / 30.0
    return None


def weapon(label, rel, mode, overrides, extra=None):
    d = load(weap_def, rel, '.weapon')
    w = d.weap_attrs
    fp = w.interface.first_person_animations.filepath
    out = {'label': label, 'mode': mode,
           'aim': (math.degrees(w.aiming.autoaim_angle), w.aiming.autoaim_range,
                   math.degrees(w.aiming.magnetism_angle), w.aiming.magnetism_range)}
    if mode == 'melee':
        out['damage'] = [damage(w.melee.player_damage.filepath)] if w.melee.player_damage.filepath else []
        out['interval'] = anim_seconds(fp, ('first-person melee',)) or 1.0
        out['charge'], out['mag'], out['reload'], out['per_shot'] = 0.0, None, None, 1
        out['speed'] = out['range'] = None
    else:
        tr = w.triggers.STEPTREE[0]
        rps = tr.firing.rounds_per_second
        out['rps'] = max(rps[0], rps[1])
        out['charge'] = tr.charging.charging_time
        out['per_shot'] = tr.projectile.projectiles_per_shot or 1
        dmg, p = projectile_damage(tr.projectile.projectile.filepath)
        out['damage'] = dmg
        out['speed'] = p.proj_attrs.physics.initial_velocity if p else None
        out['range'] = p.proj_attrs.detonation.maximum_range if p else None
        out['interval'] = 1.0 / out['rps'] if out['rps'] else 0.0
        if out['charge']:                    # a charged shot cannot repeat faster than it charges
            out['interval'] = max(out['interval'], out['charge'])
        mags = w.magazines.STEPTREE
        out['mag'] = (mags[0].rounds_loaded_maximum if len(mags) and mags[0].rounds_loaded_maximum
                      else None)
        out['rounds_per_shot'] = tr.firing.rounds_per_shot
        out['reload'] = anim_seconds(fp, ('first-person reload-empty', 'first-person reload-full'))
        out['tag_rps'] = out['rps']
        if extra and extra.get('rate'):
            out['rps'] = extra['rate']
            out['interval'] = 1.0 / out['rps']
        h = w.heat
        out['heat'] = (tr.misc.heat_generated_per_round, h.overheated_threshold,
                       h.loss_per_second, h.recovery_threshold)
        out['age'] = tr.misc.age_generated_per_round
    apply_rows(out, overrides)
    return out


AIM = ('Autoaim Angle', 'Autoaim Range', 'Magnetism Angle', 'Magnetism Range')


def apply_rows(out, rows):
    """Catalog balance rows over one computed weapon, for the fields that change a time to
    kill or the role table: trigger rate / charge, aim assist, damage, splash, per-material
    modifiers. (Energy, ammo, animation rows do not enter the simulation.)"""
    aim = list(out['aim'])
    for r in rows:
        f, v = r['field'], r['value']
        if r['class'] == 'weap':
            if f == 'Charging Time':
                out['charge'] = v
            elif f in ('Rounds Per Second', 'Rounds Per Second Max'):
                out['rps'] = v if f == 'Rounds Per Second Max' else max(v, out.get('rps') or 0)
            elif f in AIM:
                aim[AIM.index(f)] = v
        elif r['class'] == 'jpt!':
            for d in out['damage']:
                if d['tag'].lower() != r['tag'].lower():
                    continue
                if f == 'Radius':
                    d['radius'] = (v, d['radius'][1])
                elif f == 'Radius Max':
                    d['radius'] = (d['radius'][0], v)
                elif f in ('Damage Upper Bound', 'Damage Upper Bound Max'):
                    d['dmg'] = v                           # both bounds are written alike
                else:
                    key = f.lower().replace(' ', '_')
                    if key in d['mods']:
                        d['mods'][key] = v
    out['aim'] = tuple(aim)
    if out['mode'] != 'melee':
        out['interval'] = 1.0 / out['rps'] if out.get('rps') else 0.0
        if out['charge']:
            out['interval'] = max(out['interval'], out['charge'])


def balanced_overrides(port):
    """The port's catalog balance rows (Halo 1)."""
    cat = json.load(open(CATALOG, encoding='utf-8'))
    e = next((x for x in cat.get('Halo 1', []) if x['weapon'] == port), None)
    return e.get('balance', []) if e else []


def scales():
    g = load(matg_def, r'globals\globals', '.globals')
    es = g.difficulties.STEPTREE[0].enemy_scales
    return {'normal': (es.vitality[1], es.shield[1]), 'legendary': (es.vitality[3], es.shield[3])}


def enemy(path, char):
    a = load(actv_def, path, '.actor_variant')
    c = load(coll_def, os.path.join('characters', char, char), '.model_collision_geometry')
    body = (a.unit_properties.body_vitality if a and a.unit_properties.body_vitality else
            c.body.maximum_body_vitality)
    shield = (a.unit_properties.shield_vitality if a and a.unit_properties.shield_vitality else
              c.shield.maximum_shield_vitality)
    body_mat = c.materials.STEPTREE[0].material_type.enum_name if len(c.materials.STEPTREE) else ''
    shield_mat = c.shield.shield_material_type.enum_name
    if char == 'jackal':                     # the hand shield is a separate target
        shield = 0
    return body, shield, body_mat, shield_mat


def kill(wpn, body, shield, bmat, smat):
    """(shots, seconds) for a burst from cold."""
    per = []
    for d in wpn['damage']:
        per.append((d['dmg'] * d['mods'].get(smat, 1.0), d['dmg'] * d['mods'].get(bmat, 1.0)))
    if not per:
        return None, None
    s_hit = sum(p[0] for p in per) * wpn['per_shot']
    b_hit = sum(p[1] for p in per) * wpn['per_shot']
    if b_hit <= 0:
        return None, None
    shots, sh, bo = 0, shield, body
    while bo > 0 and shots < 500:
        shots += 1
        if sh > 0 and s_hit > 0:
            if s_hit >= sh:                  # the killing shot's overflow reaches the body
                frac = 1 - sh / s_hit
                sh = 0
                bo -= b_hit * frac
            else:
                sh -= s_hit
        else:
            bo -= b_hit
    t = wpn['charge'] + (shots - 1) * wpn['interval']
    if wpn.get('mag') and wpn.get('reload'):
        per_mag = max(1, wpn['mag'] // max(1, wpn.get('rounds_per_shot') or 1))
        t += ((shots - 1) // per_mag) * wpn['reload']
    return shots, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('set', choices=sorted(SETS))
    ap.add_argument('--balanced', action='store_true')
    a = ap.parse_args()
    s = SETS[a.set]
    over = balanced_overrides(s['port']) if a.balanced else []
    rows = [weapon(e[0], e[1], e[2], over if '(restored)' in e[0] or '(port)' in e[0] else [],
                   e[3] if len(e) > 3 else None)
            for e in s['weapons']]
    enemies = ENEMIES + s.get('enemies', [])
    print('%s%s\n' % (s['port'], '  -- BALANCED rows applied' if a.balanced else ''))
    print('%-26s %8s %7s %8s %6s %6s %5s %6s %6s %6s  %s' % (
        'weapon', 'damage', 'splash', 'interval', 'rate', 'dps', 'mag', 'reload', 'speed',
        'range', 'aim assist (deg/wu auto, magnet)'))
    for r in rows:
        dmg = '+'.join('%g' % round(d['dmg'], 1) for d in r['damage']) or '-'
        spl = max((d['radius'][1] for d in r['damage']), default=0)
        rate = 1.0 / r['interval'] if r['interval'] else 0
        dps = sum(d['dmg'] for d in r['damage']) * r['per_shot'] * rate
        tag = r.get('tag_rps')
        rtxt = ('%g' % rate) + ('*' if tag and abs(tag - rate) > 0.01 else '')
        print('%-26s %8s %7s %7.2fs %6s %6.0f %5s %6s %6s %6s  %4.1f/%-4g %4.1f/%-4g'
              % (r['label'], dmg, '%.2f' % spl if spl else '-', r['interval'], rtxt, dps,
                 r.get('mag') or '-', '%.1fs' % r['reload'] if r.get('reload') else '-',
                 '%g' % r['speed'] if r.get('speed') else '-',
                 '%g' % r['range'] if r.get('range') else '-', *r['aim']))
    if any(r.get('tag_rps') and abs(r['tag_rps'] - 1.0 / r['interval']) > 0.01 for r in rows
           if r['interval']):
        print('  * measured in game, not the tag rate (tag: %s)' % ', '.join(
            '%s %g/s' % (r['label'], r['tag_rps']) for r in rows
            if r.get('tag_rps') and r['interval'] and abs(r['tag_rps'] - 1.0 / r['interval']) > 0.01))
    hot = [r for r in rows if r.get('heat') and (r['heat'][0] or r.get('age'))]
    if hot:
        print('\nSUSTAINED FIRE (heat / battery)')
        print('%-26s %9s %9s %9s %10s %8s %10s %9s' % ('weapon', 'heat/rnd', 'overheat', 'loss/s',
                                                      'to overheat', 'vent', 'battery', 'per batt'))
        for r in hot:
            hpr, oh, loss, rec = r['heat']
            rate = 1.0 / r['interval']
            net = hpr * rate - loss
            t_oh = ('%.1fs' % (oh / net)) if hpr and net > 0 else 'never'
            vent = ('%.1fs' % ((oh - rec) / loss)) if hpr and loss else '-'
            rounds = (1.0 / r['age']) if r.get('age') else 0
            print('%-26s %9.4f %9g %9g %10s %8s %10s %9s'
                  % (r['label'], hpr, oh, loss, t_oh, vent,
                     ('%d rnds' % rounds) if rounds else '-',
                     ('%.1fs' % (rounds / rate)) if rounds else '-'))
    sc = scales()
    for diff in ('normal', 'legendary'):
        vs, ss = sc[diff]
        print('\nTIME TO KILL, %s (shots / seconds, burst from cold, direct hits)' % diff)
        print('%-26s' % 'weapon' + ''.join('%-17s' % e[0][:16] for e in enemies))
        stats = [(lbl,) + enemy(p, ch) for lbl, p, ch in enemies]
        for r in rows:
            line = '%-26s' % r['label']
            for _l, body, shield, bm, sm in stats:
                n, t = kill(r, body * vs, shield * ss, bm, sm)
                line += '%-17s' % ('-' if n is None else '%d / %.2fs' % (n, t))
            print(line)
    print('\nenemies: ' + '; '.join('%s %g/%g (%s, %s)' % (st[0], st[1], st[2], st[3], st[4])
                                    for st in stats))


if __name__ == '__main__':
    main()
