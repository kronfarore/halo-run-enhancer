r"""Flamethrower (S1) step 4a: Halo 1's flamethrower through each yardstick candidate's ratio
(H2 value / H1 value, per value), side by side, and the Halo 2 time to kill on legendary for the
peers and each candidate's result (h2_ar_ttk_4a.py's machinery).

The source is HALO 1 (HCEEK tags, reclaimer); the yardsticks exist in both games with cards in
both (halo.json): Plasma Rifle, Shotgun, SMG (Halo 1's is a PORT), Sentinel Beam (Halo 1's is a
PORT, derived numbers). Halo 2's live barrel error / magnetism are the SECOND declaration (A1).
The flame's damage groups: Halo 2's own `burning` group (Halo 1's category `flame`).

    python h2_ft_ttk_4a.py [--json out.json]
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
import ttk_common as tc  # noqa: E402
import ttk_halo2 as t2  # noqa: E402
from reclaimer.hek.defs.weap import weap_def  # noqa: E402
from reclaimer.hek.defs.proj import proj_def  # noqa: E402
from reclaimer.hek.defs.jpt_ import jpt__def  # noqa: E402

H1TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
deg = math.degrees
W = r'objects\weapons'
SOURCE = r'weapons\flamethrower\flamethrower'
YARDSTICKS = [  # label, Halo 1 tag, Halo 2 tag
    ('Plasma Rifle', r'weapons\plasma rifle\plasma rifle', W + r'\rifle\plasma_rifle\plasma_rifle'),
    ('Shotgun', r'weapons\shotgun\shotgun', W + r'\rifle\shotgun\shotgun'),
    ('SMG (H1 port)', r'weapons\smg\smg', W + r'\rifle\smg\smg'),
    ('Sentinel Beam (H1 port)', r'weapons\sentinel beam\sentinel beam',
     r'objects\characters\sentinel_aggressor\weapons\beam\sentinel_aggressor_beam'),
]
PEERS = [('Shotgun', W + r'\rifle\shotgun\shotgun'), ('Plasma Rifle', W + r'\rifle\plasma_rifle\plasma_rifle'),
         ('SMG', W + r'\rifle\smg\smg'),
         ('Sentinel Beam', r'objects\characters\sentinel_aggressor\weapons\beam\sentinel_aggressor_beam'),
         ('Energy Blade', None)]
C = r'objects\characters'
ENEMIES = [('Elite minor', C + r'\elite\ai\elite.character', 'armored_torso'),
           ('Brute minor', C + r'\brute\ai\brute.character', 'body'),
           ('Grunt minor', C + r'\grunt\ai\grunt.character', None),
           ('Jackal minor', C + r'\jackal\ai\jackal.character', None),
           ('Flood combat (elite)', C + r'\floodcombat_elite\ai\floodcombat_elite.character', None)]
# the values the ratio rule carries (key, label)
KEYS = [('dmg', 'damage per projectile (upper)'), ('dmg_lo', 'damage lower bound'),
        ('rps', 'rounds per second'), ('pps', 'projectiles per shot'),
        ('loaded', 'magazine loaded'), ('initial', 'rounds initial'), ('maximum', 'rounds maximum'),
        ('reload', 'reload time s'), ('heat', 'heat per round'), ('loss', 'heat loss /s'),
        ('recovery', 'heat recovery threshold'), ('overheat', 'overheated threshold'),
        ('err_lo', 'error angle lo deg'), ('err_hi', 'error angle hi deg'),
        ('vel', 'initial velocity'), ('range', 'maximum range'),
        ('auto_a', 'autoaim angle deg'), ('auto_r', 'autoaim range'),
        ('mag_a', 'magnetism angle deg'), ('mag_r', 'magnetism range')]


def h1(rel):
    d = weap_def.build(filepath=os.path.join(H1TAGS, rel + '.weapon')).data.tagdata.weap_attrs
    m = d.magazines.STEPTREE[0] if len(d.magazines.STEPTREE) else None
    tr = d.triggers.STEPTREE[0]
    f, p = tr.firing, tr.projectile
    pp = proj_def.build(filepath=os.path.join(H1TAGS, p.projectile.filepath + '.projectile')).data.tagdata.proj_attrs
    jd = jpt__def.build(filepath=os.path.join(H1TAGS, pp.physics.impact_damage.filepath + '.damage_effect')).data.tagdata
    a = d.aiming
    return dict(dmg=sum(jd.damage.damage_upper_bound) / 2.0, dmg_lo=jd.damage.damage_lower_bound,
                rps=f.rounds_per_second[1], pps=p.projectiles_per_shot,
                loaded=m.rounds_loaded_maximum if m else 0, initial=m.rounds_total_initial if m else 0,
                maximum=m.rounds_total_maximum if m else 0, reload=m.reload_time if m else 0,
                heat=tr.misc.heat_generated_per_round, loss=d.heat.loss_per_second,
                recovery=d.heat.recovery_threshold, overheat=d.heat.overheated_threshold,
                err_lo=deg(p.error_angle[0]), err_hi=deg(p.error_angle[1]),
                vel=pp.physics.initial_velocity, range=pp.detonation.maximum_range,
                auto_a=deg(a.autoaim_angle), auto_r=a.autoaim_range,
                mag_a=deg(a.magnetism_angle), mag_r=a.magnetism_range,
                category=jd.damage.category.enum_name)


def h2(path):
    t = t2.Tag(path + '.weapon', {})
    b, mg = 'barrels/[0]/', 'magazines/[0]/'
    has_m = t.count('magazines') > 0
    pr = t2.Tag(t.s(b + 'projectile') + '.projectile', {})
    j = t2.Tag(pr.s('impact damage') + '.damage_effect', {})
    err = t.pair(b + "error angle'")
    return dict(dmg=sum(j.pair('damage upper bound')) / 2.0, dmg_lo=j.f('damage lower bound'),
                rps=t.pair(b + 'rounds per second')[1], pps=t.f(b + 'projectiles per shot') or 1.0,
                loaded=t.f(mg + 'rounds loaded maximum') if has_m else 0,
                initial=t.f(mg + 'rounds total initial') if has_m else 0,
                maximum=t.f(mg + 'rounds total maximum') if has_m else 0,
                reload=t.f(mg + 'reload time') if has_m else 0,
                heat=t.f(b + 'heat generated per round'), loss=t.f('heat loss per second'),
                recovery=t.f('heat recovery threshold'), overheat=t.f('overheated threshold'),
                err_lo=err[0], err_hi=err[1], vel=pr.f('initial velocity'), range=pr.f('maximum range'),
                auto_a=t.f('autoaim angle'), auto_r=t.f('autoaim range'),
                mag_a=t.f("magnetism angle'"), mag_r=t.f("magnetism range'"),
                groups=(j.s('general_damage'), j.s('specific_damage')))


def h1_ttk():
    """Halo 1's own time to kill on legendary (ttk_halo1's tick model: heat and magazine per SHOT)
    for the flamethrower and the native yardsticks vs the Elite minor -- the pool from the a10
    baseline, the weapons from HCEEK (the flamethrower is in no stock map)."""
    import ttk_halo1 as t1
    r = t1.Reader(os.path.join(t1.BASELINE, 'a10.map'))
    g = t1.read_matg(r)
    actv, _, _, cref = t1.read_actv(r, t1.ELITE_ACTV)
    coll = t1.read_coll(r, cref[1])
    esh = (actv['Shield Vitality (+0x204)'] or coll['Maximum Shield Vitality (+0xCC)']) * g['Enemy Shield']
    ebo = (actv['Body Vitality (+0x200)'] or coll['Maximum Body Vitality (+0x8)']) * g['Enemy Vitality']
    names = {n: n.lower().replace(' (', '_').replace(')', '').replace(' ', '_') for n in t1.MATERIALS}
    out = {}
    for label, rel in [('Flamethrower', SOURCE)] + [(a, b) for a, b, _ in YARDSTICKS]:
        d = weap_def.build(filepath=os.path.join(H1TAGS, rel + '.weapon')).data.tagdata.weap_attrs
        tr = d.triggers.STEPTREE[0]
        m = d.magazines.STEPTREE[0] if len(d.magazines.STEPTREE) else None
        pp = proj_def.build(filepath=os.path.join(H1TAGS, tr.projectile.projectile.filepath + '.projectile')).data.tagdata.proj_attrs
        jd = jpt__def.build(filepath=os.path.join(H1TAGS, pp.physics.impact_damage.filepath + '.damage_effect')).data.tagdata
        mods = {n: getattr(jd.damage_modifiers, names[n], 1.0) for n in t1.MATERIALS}
        jpt = {'upper': sum(jd.damage.damage_upper_bound) / 2.0, 'modifiers': mods}
        w = {'Triggers[0] Rounds Per Second (+0x4)': tr.firing.rounds_per_second[0],
             'Triggers[0] Rounds Per Second Max (+0x8)': tr.firing.rounds_per_second[1],
             'Triggers[0] Rate Of Fire Acceleration Rate (+0xF8, runtime per tick)':
                 (1.0 / (tr.firing.acceleration_time * t1.TICK)) if tr.firing.acceleration_time else 0.0,
             'Triggers[0] Heat Generated Per Round (+0xB8)': tr.misc.heat_generated_per_round,
             'Overheated Threshold (+0x350)': d.heat.overheated_threshold,
             'Heat Recovery Threshold (+0x34C)': d.heat.recovery_threshold,
             'Heat Loss Per Second (+0x35C)': d.heat.loss_per_second}
        if m:
            w['Magazines[0] Rounds Loaded Maximum (+0xA)'] = m.rounds_loaded_maximum // max(1, tr.firing.rounds_per_shot)
            w['Magazines[0] Reload Time (+0x14)'] = m.reload_time
        sh, bo, _ = t1.damage(jpt, coll, tr.projectile.projectiles_per_shot or 1)
        n, _ = tc.shots_to_kill(esh, ebo, sh, bo)
        t, ev = t1.player_ticks(n, w)
        out[label] = (n, None if t is None else round(t, 2), ev)
    return out


def ratio_result(src, y1, y2):
    out = {}
    for k, _ in KEYS:
        if k == 'rps' and not y2.get(k):
            out[k] = (src[k], 'no ratio (Halo 2 rate 0: fire recovery drives it): raw H1')
        elif y1.get(k) and y2.get(k) is not None and y1[k] != 0:
            out[k] = (src[k] * y2[k] / y1[k], 'ratio %.4g' % (y2[k] / y1[k]))
        else:
            out[k] = (src[k], 'no ratio (yardstick %s in H1 / %s in H2): raw H1' % (y1.get(k), y2.get(k)))
    return out


def main():
    src = h1(SOURCE)
    log = {}
    g = t2.Globals(log)
    # the enemies (h2_ar_ttk_4a.py)
    targets = []
    for elabel, cpath, bm in ENEMIES:
        try:
            chain = t2.char_chain(cpath.replace('.character', ''), {})
            vt, vp = t2.char_vitality(chain)
            unit = chain[0].s('unit')
            model = t2.Tag(unit + '.biped', {}).s('model') + '.model'
            mt = t2.Tag(model, {})
            names = [mt.s('materials/[%d]/material name' % i, False) for i in range(mt.count('materials'))]
            if bm is None:
                bm = 'body' if 'body' in names else names[0]
            em = t2.model_damage_info(model, {}, bm)
            targets.append((elabel, vt.f(vp + 'legendary shield vitality') * g.dial['enemy shield'],
                            vt.f(vp + 'legendary body vitality') * g.dial['enemy vitality'],
                            em['global shield material name'], em['body material']))
        except Exception as e:  # noqa: BLE001
            print('enemy %s: %s' % (elabel, e))

    def ttk(w, groups):
        out = []
        for elabel, esh, ebo, shm, bom in targets:
            msh = g.multiplier(groups, shm)[0] if esh > 0 else 0
            mbo = g.multiplier(groups, bom)[0]
            per = w['upper'] * w['projectiles per shot']
            n, _ = tc.shots_to_kill(esh, ebo, per * msh, per * mbo)
            if not w['rps'][1]:
                out.append((elabel, n, 'rate 0 in the tag', 0, 0))
                continue
            t, ev = t2.sim_player(n, w)
            out.append((elabel, n, None if t is None else round(t, 2), ev.get('overheats', 0), ev.get('reloads', 0)))
        return out

    res = {'source_h1': src, 'targets': targets, 'peers': {}, 'candidates': {},
           'h1_ttk_elite_minor': h1_ttk()}
    for label, p in PEERS:
        if p is None:
            continue
        w = t2.read_weapon(p, {})
        res['peers'][label] = ttk(w, (w['general_damage'], w['specific_damage']))
    base = t2.read_weapon(W + r'\rifle\smg\smg', {})
    for label, r1, r2 in YARDSTICKS:
        y1, y2 = h1(r1), h2(r2)
        rr = ratio_result(src, y1, y2)
        w = dict(base)
        w.update(upper=rr['dmg'][0], rps=[rr['rps'][0]] * 2, accel=0.0, mag=int(round(rr['loaded'][0])),
                 reload=rr['reload'][0], **{'projectiles per shot': src['pps'], 'shots per fire': [1, 1],
                                            'fire recovery': 0.0, 'heat per round': rr['heat'][0],
                                            'overheated threshold': rr['overheat'][0],
                                            'heat recovery threshold': rr['recovery'][0],
                                            'heat loss': rr['loss'][0], 'overheated heat loss': rr['loss'][0]})
        res['candidates'][label] = {'h1': y1, 'h2': y2, 'result': rr,
                                    'ttk_burning': ttk(w, ('burning', '')),
                                    # the H2 row nearest Halo 1's flame table (shields x0.5, organics x1)
                                    'ttk_explosion_small': ttk(w, ('explosion_small', '')),
                                    'ttk_yard_groups': ttk(w, y2['groups'])}
    print(json.dumps(res, indent=1, default=str))
    if '--json' in sys.argv:
        json.dump(res, open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
