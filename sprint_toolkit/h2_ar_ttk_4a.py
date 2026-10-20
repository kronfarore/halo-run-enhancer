r"""AR pilot step 4a: Halo 2 time to kill, legendary, for the peers and the AR candidates."""
import sys, os, json
sys.path.insert(0, r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool\sprint_toolkit')
import ttk_common as tc
import ttk_halo2 as t2

W = r'objects\weapons'
FP = r'objects\characters\masterchief\fp\weapons'
t2.RELOAD_ANIM[W + r'\rifle\saw\saw'] = (FP + r'\rifle\fp_saw\fp_saw.model_animation_graph', 'first_person:reload_empty')
PEERS = [('SMG', W + r'\rifle\smg\smg'), ('Battle Rifle', W + r'\rifle\battle_rifle\battle_rifle'),
         ('Plasma Rifle', W + r'\rifle\plasma_rifle\plasma_rifle'),
         ('Brute Plasma Rifle', W + r'\rifle\brute_plasma_rifle\brute_plasma_rifle'),
         ('SAW (port)', W + r'\rifle\saw\saw')]
C = r'objects\characters'
ENEMIES = [('Elite minor', C + r'\elite\ai\elite.character', 'armored_torso'),
           ('Brute minor', C + r'\brute\ai\brute.character', 'body'),
           ('Grunt minor', C + r'\grunt\ai\grunt.character', None),
           ('Jackal minor', C + r'\jackal\ai\jackal.character', None)]

def frames(jmad, name):
    a = t2.Tag(jmad, {})
    for i in range(a.count('animations')):
        if a.s('animations/[%d]/name' % i, False) == name:
            return a.f('animations/[%d]/frame count' % i)

log = {}
g = t2.Globals(log)
weapons = {}
for label, p in PEERS:
    weapons[label] = t2.read_weapon(p, {})
extra = {}
for label, p in PEERS:
    w = weapons[label]
    tag = t2.Tag(p + '.weapon', {})
    extra[label] = dict(carry=tag.f('magazines/[0]/rounds total maximum') if tag.count('magazines') else 0,
                        initial=tag.f('magazines/[0]/rounds total initial') if tag.count('magazines') else 0,
                        err=tag.pair('barrels/[0]/error angle'), minerr=tag.f('barrels/[0]/minimum error'),
                        aa=(tag.f('autoaim angle'), tag.f('autoaim range'), tag.f('magnetism angle'), tag.f('magnetism range')),
                        dual=tag.s('flags'))
    pr = t2.Tag(w['projectile'] + '.projectile', {})
    extra[label]['vel'] = (pr.f('initial velocity'), pr.f('final velocity'))
    extra[label]['range'] = pr.f('maximum range')
fpn = {'SMG': 'fp_smg', 'Battle Rifle': 'fp_battle_rifle', 'Plasma Rifle': 'fp_plasma_rifle', 'SAW (port)': 'fp_saw'}
for k, v in fpn.items():
    j = FP + r'\rifle\%s\%s.model_animation_graph' % (v, v)
    extra[k]['reload_frames'] = frames(j, 'first_person:reload_empty')
    extra[k]['ready_frames'] = frames(j, 'first_person:ready')

# the enemies
targets = []
for elabel, cpath, bm in ENEMIES:
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
                    em['global shield material name'], em['body material'], names))

def ttk(w):
    out = []
    groups = (w['general_damage'], w['specific_damage'])
    for elabel, esh, ebo, shm, bom, _ in targets:
        msh = g.multiplier(groups, shm)[0] if esh > 0 else 0
        mbo = g.multiplier(groups, bom)[0]
        n, _ = tc.shots_to_kill(esh, ebo, w['upper'] * w['projectiles per shot'] * msh,
                                w['upper'] * w['projectiles per shot'] * mbo)
        t, ev = t2.sim_player(n, w)
        out.append((elabel, n, t))
    return out

res = {'targets': [(a, b, c, d, e) for a, b, c, d, e, _ in targets], 'peers': {}, 'ar': {}}
for label in weapons:
    w = weapons[label]
    res['peers'][label] = dict(w=dict((k, w[k]) for k in ('rps', 'accel', 'mag', 'reload', 'upper', 'general_damage', 'heat per round', 'shots per fire', 'fire recovery')),
                               extra=extra[label], ttk=ttk(w))

# AR variants: built on the SMG's H2 damage effect groups (a bullet), the numbers swapped
smg = weapons['SMG']
def ar(dmg, rps, mag, reload_s, groups_from='SMG'):
    w = dict(weapons[groups_from]); w.update(upper=dmg, rps=[rps, rps], accel=0.0, mag=mag, reload=reload_s,
              **{'shots per fire': [1, 1], 'fire recovery': 0.0, 'heat per round': 0.0})
    return w
V = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else {}
for name, (dmg, rps, mag, rl) in V.items():
    res['ar'][name] = ttk(ar(dmg, rps, mag, rl))
print(json.dumps(res, indent=1, default=str))
