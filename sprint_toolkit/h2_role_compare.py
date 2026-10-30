r"""HALO 2 role comparison + time to kill for a port: steps 4a and 5b, the Halo 2 counterpart of
h1_role_compare.py (it replaces the per-port h2_ar_ttk_4a / h2_spiker_ttk_4a / h2_ft_ttk_4a scripts).

    python h2_role_compare.py <key> [--balanced] [--peers "SMG,Needler"] [--json out.json]

The set: the port, its config's yardstick candidates (provisional + alternatives) and step-5b
peers (`yardstick.candidates.peers`), each a stock Halo 2 weapon (STOCK) or another port in the
'Halo 2' catalog. Everything is read from the H2EK kit through ttk_halo2 (tool export-tag-to-xml):
  weapon      barrel 0: rounds per second (+ the rate ramp), shots per fire, projectiles per shot,
              fire recovery, heat; magazine 0; error; aim assist; dual-wield flag
  damage      the projectile's impact damage effect: the mean of its upper bounds x the matg damage
              table (damage group x the hit material's armour)
  enemies     Elite / Brute / Grunt / Jackal minor on LEGENDARY: the character's vitality (parent
              chain) x the matg difficulty dials
  time        ttk_halo2.sim_player: rate ramp, bursts, heat + overheat, a reload whenever the
              magazine empties (the masterchief FP graph's reload_empty when the tag's reload
              time is 0)
STATED ASSUMPTIONS (ttk_halo2's): body shots, direct hits, no headshots, no splash, no recharge
(a Needler's supercombine is splash: not counted); the Jackal's shield is its HAND shield (its model
has no body shield), so a body shot meets the body alone. Error = the SINGLE-wield cone.

The kit's tags hold a port's DEFAULT numbers (its source game's). --balanced lays the catalog's
balance rows over every port in the set (the fields this tool knows) and scales its reload by the
row's `anims` reload -- what the enhancer's Balanced box writes. Stock weapons read the same in both.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.dirname(HERE))
import ttk_common as tc  # noqa: E402
import ttk_halo2 as t2   # noqa: E402
import ports_h2          # noqa: E402

CATALOG = os.path.join(os.path.dirname(HERE), 'weapon_ports_catalog.json')
W = 'objects\\weapons\\'
FP = 'objects\\characters\\masterchief\\fp\\weapons\\'

# Halo 2's stock weapons by the names the configs use (Bungie's tag + FP graph folder)
STOCK = {
    'SMG': ('rifle\\smg\\smg', 'rifle\\fp_smg\\fp_smg'),
    'Battle Rifle': ('rifle\\battle_rifle\\battle_rifle', 'rifle\\fp_battle_rifle\\fp_battle_rifle'),
    'Plasma Rifle': ('rifle\\plasma_rifle\\plasma_rifle', None),
    'Brute Plasma Rifle': ('rifle\\brute_plasma_rifle\\brute_plasma_rifle', None),
    'Carbine': ('rifle\\covenant_carbine\\covenant_carbine', 'rifle\\fp_covenant_carbine\\fp_covenant_carbine'),
    'Covenant Carbine': ('rifle\\covenant_carbine\\covenant_carbine', 'rifle\\fp_covenant_carbine\\fp_covenant_carbine'),
    'Beam Rifle': ('rifle\\beam_rifle\\beam_rifle', None),
    'Shotgun': ('rifle\\shotgun\\shotgun', 'rifle\\fp_shotgun\\fp_shotgun'),
    'Sniper': ('rifle\\sniper_rifle\\sniper_rifle', 'rifle\\fp_sniper_rifle\\fp_sniper_rifle'),
    'Sniper Rifle': ('rifle\\sniper_rifle\\sniper_rifle', 'rifle\\fp_sniper_rifle\\fp_sniper_rifle'),
    'Magnum': ('pistol\\magnum\\magnum', 'pistol\\fp_magnum\\fp_magnum'),
    'Pistol': ('pistol\\magnum\\magnum', 'pistol\\fp_magnum\\fp_magnum'),
    'Needler': ('pistol\\needler\\needler', 'pistol\\fp_needler\\fp_needler'),
    'Plasma Pistol': ('pistol\\plasma_pistol\\plasma_pistol', None),
    'Rocket Launcher': ('support_high\\rocket_launcher\\rocket_launcher',
                        'support_high\\fp_rocket_launcher\\fp_rocket_launcher'),
    'RL': ('support_high\\rocket_launcher\\rocket_launcher',
           'support_high\\fp_rocket_launcher\\fp_rocket_launcher'),
    'Fuel Rod': ('support_high\\flak_cannon\\flak_cannon', 'support_high\\fp_flak_cannon\\fp_flak_cannon'),
    'Brute Shot': ('support_low\\brute_shot\\brute_shot', 'support_low\\fp_brute_shot\\fp_brute_shot'),
    'Sword': ('melee\\energy_blade\\energy_blade', None),
    'Energy Blade': ('melee\\energy_blade\\energy_blade', None),
    'Sentinel Beam': ('objects\\characters\\sentinel_aggressor\\weapons\\beam\\sentinel_aggressor_beam',
                      'support_low\\fp_sentinel_beam\\fp_sentinel_beam'),
}

ERROR_FIELDS = ('Minimum Error', 'Error Angle', 'Error Angle Max')

ENEMIES = [('Elite minor', 'objects\\characters\\elite\\ai\\elite', 'armored_torso'),
           ('Brute minor', 'objects\\characters\\brute\\ai\\brute', 'body'),
           ('Grunt minor', 'objects\\characters\\grunt\\ai\\grunt', None),
           ('Jackal minor', 'objects\\characters\\jackal\\ai\\jackal', None)]


def catalog_ports():
    try:
        return {p['weapon']: p for p in json.load(open(CATALOG, encoding='utf-8')).get('Halo 2') or ()}
    except (OSError, ValueError):
        return {}


def port_paths(entry):
    """(weapon tag, masterchief FP graph) of a catalog entry."""
    import weapon_ports
    fp = entry.get('fp_animations')
    fp = fp.replace('*', 'masterchief') if fp else None
    return weapon_ports.weap_path(entry), fp


def resolve(name, cat):
    """(label, weapon path, FP graph, catalog entry or None) for a set member, or None."""
    name = name[:-len(' (port)')] if name.endswith(' (port)') else name
    if name not in cat and name not in STOCK:
        name = name.split(' (')[0].strip()      # a config's note: 'Plasma Rifle (native in ...)'
    if name in cat:
        w, fp = port_paths(cat[name])
        return ('%s (port)' % name, w, fp, cat[name])
    if name in STOCK:
        w, fp = STOCK[name]
        return (name, w if w.startswith('objects\\') else W + w, (FP + fp + '.model_animation_graph') if fp else None, None)
    return None


def overlay(w, ex, entry):
    """Lay a catalog entry's balance rows over the read weapon (the fields this tool knows)."""
    rows, err = {}, {}
    for r in entry.get('balance') or ():
        if r.get('index') not in (None, 0, 'all'):
            continue
        if r['field'] in ERROR_FIELDS:
            # declared twice in a Halo 2 barrel: the DUAL-wield copy first (no nth), the
            # single-wield one second (nth 1) -- H2_PORT_PLAN A1's barrel order
            if r.get('nth') == 1:
                err[r['field']] = r['value']
            continue
        # the shot's OWN damage effect: another jpt! row (the Spartan Laser's splash, a melee) would
        # overwrite the same field
        if r['class'] == 'jpt!' and r.get('tag', '').lower() != w['impact damage'].lower():
            continue
        rows[(r['class'], r['field'])] = r['value']
    g = rows.get
    if ('jpt!', 'Damage Upper Bound') in rows:
        hi = g(('jpt!', 'Damage Upper Bound Max'), rows[('jpt!', 'Damage Upper Bound')])
        w['upper'] = (rows[('jpt!', 'Damage Upper Bound')] + hi) / 2.0
    if ('weap', 'Rounds Per Second') in rows:
        w['rps'] = [rows[('weap', 'Rounds Per Second')],
                    g(('weap', 'Rounds Per Second Max'), rows[('weap', 'Rounds Per Second')])]
    for field, key in (('Projectiles Per Shot', 'projectiles per shot'), ('Fire Recovery Time', 'fire recovery'),
                       ('Heat Generated Per Round', 'heat per round')):
        if ('weap', field) in rows:
            w[key] = rows[('weap', field)] or (1.0 if key == 'projectiles per shot' else 0.0)
    if ('weap', 'Shots Per Fire') in rows:
        w['shots per fire'] = [rows[('weap', 'Shots Per Fire')],
                               g(('weap', 'Shots Per Fire Max'), rows[('weap', 'Shots Per Fire')])]
    if ('weap', 'Acceleration Time') in rows:
        w['accel'] = rows[('weap', 'Acceleration Time')]
    if ('weap', 'Rounds Loaded Maximum') in rows:
        w['mag'] = int(rows[('weap', 'Rounds Loaded Maximum')])
    mult = (entry.get('anims') or {}).get('reload')
    if mult:
        w['reload'] *= mult
    for field, key in (('Rounds Total Maximum', 'carry'), ('Rounds Total Initial', 'initial')):
        if ('weap', field) in rows:
            ex[key] = rows[('weap', field)]
    if ('proj', 'Initial Velocity') in rows:
        ex['vel'] = (rows[('proj', 'Initial Velocity')], g(('proj', 'Final Velocity'), ex['vel'][1]))
    if ('proj', 'Maximum Range') in rows:
        ex['range'] = rows[('proj', 'Maximum Range')]
    if 'Error Angle' in err:
        ex['err'] = [err['Error Angle'], err.get('Error Angle Max', ex['err'][1])]
    if ('weap', 'Autoaim Angle') in rows:
        ex['aa'] = (rows[('weap', 'Autoaim Angle')], g(('weap', 'Autoaim Range'), ex['aa'][1]))
    return w, ex


def read(label, path, fp, entry, balanced, log):
    if fp:
        t2.RELOAD_ANIM[path] = (fp if fp.endswith('.model_animation_graph') else fp + '.model_animation_graph',
                                'first_person:reload_empty')
    w = t2.read_weapon(path, log)
    tag = t2.Tag(path + '.weapon', log)
    mags = tag.count('magazines')
    pr = t2.Tag(w['projectile'] + '.projectile', log)
    ex = dict(carry=tag.f('magazines/[0]/rounds total maximum') if mags else 0,
              initial=tag.f('magazines/[0]/rounds total initial') if mags else 0,
              err=tag.pair("barrels/[0]/error angle'" if tag.raw("barrels/[0]/error angle'") is not None
                           else 'barrels/[0]/error angle'),   # the single-wield copy (see overlay)
              aa=(tag.f('autoaim angle'), tag.f('autoaim range')),
              dual='can be dual wielded' in tag.s('flags'),
              vel=(pr.f('initial velocity'), pr.f('final velocity')), range=pr.f('maximum range'))
    if balanced and entry:
        w, ex = overlay(w, ex, entry)
    if not (w['rps'][0] or w['rps'][1]) and w['fire recovery']:
        # a weapon paced by its fire recovery alone (Halo 2's shotgun: rate 0, recovery 1.0 s)
        w['rps'] = [1.0 / w['fire recovery']] * 2
        w['fire recovery'] = 0.0
    if 'charge' in w['trigger behavior'] and 'charge' in tag.s('new triggers/[0]/primary action'):
        # a charge-to-fire weapon (the Spartan Laser: a release fires nothing): one shot a charge, and
        # a shot that overheats adds the vent. ttk() puts the first charge in front of the first shot
        vent = ((w['overheated threshold'] - w['heat recovery threshold']) / w['overheated heat loss']
                if w['heat per round'] >= w['overheated threshold'] > 0 else 0.0)
        w['charge'] = tag.f('new triggers/[0]/charging time')
        w['rps'] = [1.0 / (w['charge'] + vent)] * 2
        w['heat per round'] = w['accel'] = w['fire recovery'] = 0.0
    per = tag.f('magazines/[0]/rounds reloaded') if mags else 0
    if per and w['mag'] and per < w['mag']:
        w['reload'] *= w['mag'] / per         # shell by shell: the tag's time is per shell
    return w, ex


def enemies(g):
    out = []
    for label, cpath, bm in ENEMIES:
        chain = t2.char_chain(cpath, {})
        vt, vp = t2.char_vitality(chain)
        model = t2.Tag(chain[0].s('unit') + '.biped', {}).s('model') + '.model'
        mt = t2.Tag(model, {})
        names = [mt.s('materials/[%d]/material name' % i, False) for i in range(mt.count('materials'))]
        bm = bm or ('body' if 'body' in names else names[0])
        em = t2.model_damage_info(model, {}, bm)
        # a model with NO shield (the Jackal): the character's shield is its HAND shield, which a
        # body shot goes around
        shield = vt.f(vp + 'legendary shield vitality') if em['maximum shield vitality'] else 0.0
        out.append((label, shield * g.dial['enemy shield'],
                    vt.f(vp + 'legendary body vitality') * g.dial['enemy vitality'],
                    em['global shield material name'], em['body material']))
    return out


def ttk(g, targets, w):
    groups = (w['general_damage'], w['specific_damage'])
    per = w['upper'] * (w['projectiles per shot'] or 1.0)
    out = []
    if not (w['rps'][0] or w['rps'][1]):
        return [(t[0], None, None) for t in targets]   # no rate (a melee weapon): no fire TTK
    for label, esh, ebo, shm, bom in targets:
        msh = g.multiplier(groups, shm)[0] if esh > 0 else 0
        n, _ = tc.shots_to_kill(esh, ebo, per * msh, per * g.multiplier(groups, bom)[0])
        t, _ = t2.sim_player(n, w)
        out.append((label, n, t + w.get('charge', 0.0)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key')
    ap.add_argument('--balanced', action='store_true')
    ap.add_argument('--peers', default='', help='the set instead of the config\'s (comma separated names)')
    ap.add_argument('--json')
    a = ap.parse_args()
    cfg = ports_h2.load(a.key)
    cat = catalog_ports()
    cand = (cfg.get('yardstick') or {}).get('candidates') or {}
    names = [x.strip() for x in a.peers.split(',') if x.strip()] or \
        [cand.get('provisional')] + list(cand.get('alternatives') or ()) + list(cand.get('peers') or ())
    own = cfg.get('name') or (cfg.get('catalog') or {}).get('name')
    if own not in cat:
        raise SystemExit('%s: no Halo 2 catalog entry named %r (make_port_catalog_h2.py %s --write)'
                         % (a.key, own, a.key))
    members, seen, skipped = [], set(), []
    for n in [own] + names:
        r = resolve(n, cat) if n else None
        if r is None:
            if n:
                skipped.append(n)
            continue
        if r[1] not in seen:
            seen.add(r[1])
            members.append(r)
    log = {}
    g = t2.Globals(log)
    targets = enemies(g)
    rows = []
    for label, path, fp, entry in members:
        if not t2.Tag(path + '.weapon', {}).s('barrels/[0]/projectile', False):
            skipped.append('%s (no projectile: melee)' % label)
            continue
        w, ex = read(label, path, fp, entry, a.balanced, log)
        rate = w['rps'][1] or w['rps'][0]
        dps = w['upper'] * (w['projectiles per shot'] or 1.0) * rate
        rows.append(dict(label=label, tag=path, damage=w['upper'], projectiles=w['projectiles per shot'],
                         rate=w['rps'], dps=dps, mag=w['mag'], reload=w['reload'], carry=ex['carry'],
                         initial=ex['initial'], vel=ex['vel'], range=ex['range'], error=ex['err'],
                         autoaim=ex['aa'], dual=ex['dual'], heat=w['heat per round'],
                         ttk=ttk(g, targets, w)))
    print('%s -- %s, legendary, body shots (ttk_halo2)%s' % (
        own, 'BALANCED (catalog rows on the ports)' if a.balanced else 'DEFAULT (the kit\'s tags)',
        ('; not a Halo 2 weapon here: ' + ', '.join(skipped)) if skipped else ''))
    print('%-24s %6s %9s %6s %4s %6s %8s %11s %5s %11s %9s %4s' % (
        'weapon', 'dmg', 'rate/s', 'dps', 'mag', 'reload', 'init/max', 'vel', 'range', 'error', 'autoaim', 'dual'))
    for r in rows:
        dmg = '%.3g%s' % (r['damage'], 'x%d' % r['projectiles'] if (r['projectiles'] or 1) > 1 else '')
        print('%-24s %6s %9s %6.1f %4s %6.2f %8s %11s %5.0f %11s %9s %4s' % (
            r['label'][:24], dmg, '%.3g-%.3g' % tuple(r['rate']), r['dps'], r['mag'] or '-', r['reload'],
            '%d/%d' % (r['initial'], r['carry']), '%.4g/%.4g' % tuple(r['vel']), r['range'],
            '%.3g-%.3g' % tuple(r['error']), '%.3g/%.3g' % tuple(r['autoaim']), 'y' if r['dual'] else ''))
    print('\ntime to kill (shots / seconds):')
    print('%-24s' % '' + ''.join('%17s' % t[0] for t in targets))
    for r in rows:
        print('%-24s' % r['label'][:24] + ''.join(
            '%17s' % ('%s / %s' % (n, '%.2f s' % t if t is not None else '-') if n else '-')
            for _, n, t in r['ttk']))
    if a.json:
        json.dump({'port': own, 'balanced': a.balanced, 'targets': targets, 'rows': rows},
                  open(a.json, 'w', encoding='utf-8'), indent=1, default=str)
        print('wrote %s' % a.json)


if __name__ == '__main__':
    main()
