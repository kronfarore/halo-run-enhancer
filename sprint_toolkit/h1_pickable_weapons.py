r"""Make Halo 1's enemy-only Energy Sword and Fuel Rod pickable (HCEEK kit tags).

Halo 1 SHIPS both weapons -- the Elites' `weapons\energy sword\energy sword` and the
Grunts' `weapons\fuel rod gun\fuel rod` -- but as enemy-only items: each carries the weapon
flag `detonates_when_dropped` (the sword disperses, the fuel rod blows up 1.75-3 s after
landing), and neither has a first-person model, first-person animations or (the fuel rod)
a HUD. The user's call (2026-10-05): pick up the ORIGINAL weapons, behaviour unchanged --
the fuel rod keeps its 4-round magazine, 1.25 s charge and rod projectile.

What this writes, all idempotent, every stock tag backed up once as <tag>.before_pickable:

  weapon tag     detonates_when_dropped cleared; first-person model + animations named
                 (h1_fp_retarget.py builds those from Halo 3's FP animations); the fuel rod
                 gets its own HUD and its own melee damage (Halo 1: every weapon owns one)
  FP animations  melee key frames (Halo 3's primary_keyframe) and the stock Halo 1 sounds
                 that fit: the Elite's sword swing, the fuel rod's own melee, the PC fuel
                 rod's ready sound. Reload stays silent until the port's own sounds (step 10).
  fuel rod HUD   the PC fuel rod's (`weapons\plasma_cannon`: its crosshair and pickup icon)
                 with the Assault Rifle's magazine readout -- child `ui\hud\master rounds`
                 and a 4-tick meter from ammo_meter.py -- instead of its heat display
  player biped   `characters\cyborg\cyborg` is taught the two labels: `fr` from the PC fuel
                 rod's `pc` (plasmacannon class), `fb` from the oddball's `b` (pistol class).
                 Without the label the third-person pose has no animations (enemy AI in
                 the same case fell back to its default weapon, halo1-enemy-weapon-teaching).

The sword gets no HUD and no trigger -- exactly the oddball's setup (`weapons\ball\ball`:
no HUD interface, no triggers, own melee). Its FP model is its own world model; the
retarget poses that directly (h1_fp_retarget.py, 'same_space').

Maps must be REBUILT afterwards (h1_rebuild_all.py): every change here is a kit tag.

    python h1_pickable_weapons.py            # show what it would do
    python h1_pickable_weapons.py --write
"""
import argparse
import copy
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.weap import weap_def  # noqa: E402
from reclaimer.hek.defs.antr import antr_def  # noqa: E402
from reclaimer.hek.defs.wphi import wphi_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
BACKUP = '.before_pickable'
CYBORG = r'characters\cyborg\cyborg'

WEAPONS = {
    'energy_sword': {
        'weapon': r'weapons\energy sword\energy sword',
        'fp_model': r'weapons\energy sword\energy sword',
        'fp_anims': r'weapons\energy sword\fp\fp',
        'teach': ('fb', 'b'),
        'keys': {'first-person melee': 5},
        'sounds': {'first-person melee':
                   r'sound\sfx\impulse\animations\elite\stand_sword_melee.mov'},
    },
    'fuel_rod': {
        'weapon': r'weapons\fuel rod gun\fuel rod',
        'fp_model': r'weapons\fuel rod gun\fp\fp',
        'fp_anims': r'weapons\fuel rod gun\fp\fp',
        'teach': ('fr', 'pc'),
        'keys': {'first-person melee': 5},
        'sounds': {'first-person melee': r'sound\sfx\weapons\weapon_anims\fuelrod_melee',
                   'first-person ready': r'sound\sfx\weapons\weapon_anims\plasrifle_ready'},
        # Halo 1 rule (PORTING.md step 3): a weapon owns its melee damage tag. The PC fuel
        # rod's is the Chief-held fuel rod's melee; the response stays shared (feedback).
        'melee': (r'weapons\plasma_cannon\effects\plasma_cannon_melee',
                  r'weapons\fuel rod gun\melee'),
        'melee_response': r'weapons\plasma_cannon\effects\plasma_cannon_melee_response',
        'hud': {'donor': r'weapons\plasma_cannon\plasma_cannon',
                'readout': r'weapons\assault rifle\assault rifle',
                'out': r'weapons\fuel rod gun\fuel rod',
                'meter': r'weapons\fuel rod gun\bitmaps\fuel_rod_ammo'},
    },
}


def path(rel, ext):
    return os.path.join(TAGS, rel + ext)


def backup(p):
    if os.path.exists(p) and not os.path.exists(p + BACKUP):
        shutil.copy2(p, p + BACKUP)


def save(tag, p, write):
    if write:
        backup(p)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tag.serialize(filepath=p, temp=False, backup=False)


def make_hud(w, write):
    """The PC fuel rod's HUD with the AR's magazine readout, for a 4-round magazine."""
    from ammo_meter import step as ammo_step
    h = w['hud']
    t = wphi_def.build(filepath=path(h['donor'], '.weapon_hud_interface'))
    ar = wphi_def.build(filepath=path(h['readout'], '.weapon_hud_interface')).data.tagdata
    d = t.data.tagdata
    d.child_hud.filepath = ar.child_hud.filepath                  # master plasma -> rounds
    mag = 4
    for name, field, suffix in (('static_elements', 'interface_bitmap', '_alphas'),
                                ('meter_elements', 'meter_bitmap', '_meters')):
        dst = getattr(d, name).STEPTREE
        dst[:] = []
        for e in getattr(ar, name).STEPTREE:
            if e.state_attached_to.enum_name != 'loaded_ammo':
                continue
            e = copy.deepcopy(e)
            getattr(e, field).filepath = h['meter'] + suffix
            e.sequence_index = 0
            if name == 'meter_elements':                         # see saw_weapon.py
                e.alpha_multiplier = ammo_step(mag)
                e.alpha_bias = 1
                e.value_scale = 0
            dst.append(e)
    fc = d.flash_cutoffs
    fc.heat_cutoff = 0
    fc.loaded_ammo_cutoff = 1
    fc.total_ammo_cutoff = 4
    out = path(h['out'], '.weapon_hud_interface')
    if write:
        import ammo_meter
        ammo_meter.make(mag, h['meter']) if hasattr(ammo_meter, 'make') else \
            os.system('python "%s" %d "%s"' % (os.path.join(HERE, 'ammo_meter.py'), mag,
                                               h['meter']))
    save(t, out, write)
    return h['out']


def edit_weapon(key, write):
    w = WEAPONS[key]
    p = path(w['weapon'], '.weapon')
    src = p + BACKUP if os.path.exists(p + BACKUP) else p
    t = weap_def.build(filepath=src)
    d = t.data.tagdata
    a = d.weap_attrs
    print('%s: flags before %s' % (key, [f for f in a.flags.NAME_MAP if a.flags.get(f)]))
    a.flags.detonates_when_dropped = False
    a.interface.first_person_model.filepath = w['fp_model']
    a.interface.first_person_animations.filepath = w['fp_anims']
    if 'melee' in w:
        donor, own = w['melee']
        if write:
            backup(path(own, '.damage_effect'))
            shutil.copy2(path(donor, '.damage_effect'), path(own, '.damage_effect'))
        a.melee.player_damage.filepath = own
        a.melee.player_response.filepath = w['melee_response']
    if 'hud' in w:
        a.interface.hud_interface.filepath = make_hud(w, write)
    print('   -> flags %s | fp %s | anims %s | hud %s | melee %s'
          % ([f for f in a.flags.NAME_MAP if a.flags.get(f)],
             a.interface.first_person_model.filepath,
             a.interface.first_person_animations.filepath,
             a.interface.hud_interface.filepath, a.melee.player_damage.filepath))
    t.filepath = p
    save(t, p, write)


def edit_fp_anims(key, write):
    """Melee key frames and sounds on the compiled FP animation tag. Recompiling it with
    `tool animations` resets both, so run this after every h1_fp_retarget --write."""
    w = WEAPONS[key]
    p = path(w['fp_anims'], '.model_animations')
    t = antr_def.build(filepath=p)
    d = t.data.tagdata
    refs = d.sound_references.STEPTREE
    have = [r.sound.filepath for r in refs]
    for a in d.animations.STEPTREE:
        if a.name in w['keys']:
            a.key_frame_index = w['keys'][a.name]
        snd = w['sounds'].get(a.name)
        if snd:
            if snd not in have:
                refs.append()
                refs[-1].sound.filepath = snd
                have.append(snd)
            a.sound = have.index(snd)
            a.sound_frame_index = 0
        print('   %-30s key %2d sound %s' % (a.name, a.key_frame_index,
                                              have[a.sound] if a.sound >= 0 else '-'))
    save(t, p, write)


def teach_cyborg(write):
    """Append `fr` (from `pc`) and `fb` (from `b`) wherever the donor label exists."""
    p = path(CYBORG, '.model_animations')
    src = p + BACKUP if os.path.exists(p + BACKUP) else p
    t = antr_def.build(filepath=src)
    added = []
    for u in t.data.tagdata.units.STEPTREE:
        for wc in u.weapons.STEPTREE:
            wt = wc.weapon_types.STEPTREE
            labels = [x.label for x in wt]
            for w in WEAPONS.values():
                new, donor = w['teach']
                if donor in labels and new not in labels:
                    e = copy.deepcopy(wt[labels.index(donor)])
                    e.label = new
                    wt.append(e)
                    labels.append(new)
                    added.append('%s/%s %s<-%s' % (u.label, wc.name, new, donor))
    print('cyborg: %d label(s) taught: %s' % (len(added), ', '.join(added)))
    t.filepath = p
    save(t, p, write)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    for key in WEAPONS:
        edit_weapon(key, a.write)
        if os.path.exists(path(WEAPONS[key]['fp_anims'], '.model_animations')):
            edit_fp_anims(key, a.write)
        else:
            print('   (no FP animation tag yet: python h1_fp_retarget.py %s --write, then '
                  'tool animations)' % key)
    teach_cyborg(a.write)
    if not a.write:
        print('\n(dry run -- --write to save)')


if __name__ == '__main__':
    main()
