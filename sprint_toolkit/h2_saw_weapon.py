r"""Give the Halo 2 SAW a weapon tag of its own, and a projectile nothing else fires.

Step 3 of the port. The cut GPMG is a hybrid Bungie left half-finished: it borrows the
Warthog's anti-personnel turret for its ammunition, so `h_turret_ap_bullet.projectile`
and both of its damage effects are shared with `h_turret_ap.weapon`, which is a live
weapon on real maps. Tuning the SAW's damage through those tags would quietly retune the
Warthog turret with it -- the exact leak this step exists to prevent.

So the port takes copies:

    objects\weapons\rifle\saw\saw.weapon                         <- gpmg.weapon
    objects\weapons\rifle\saw\projectiles\saw_bullet.projectile  <- h_turret_ap_bullet
    objects\weapons\rifle\saw\damage_effects\saw_bullet          <- its damage effect
    objects\weapons\rifle\saw\damage_effects\saw_trigger         <- the firing damage

and nothing Bungie shipped is touched. **The GPMG's own tag stays exactly as it is.**
That is the whole point of this donor: its HUD (`ui\hud\gpmg`) and its five pickup
message ids are referenced, not taken over, because no live weapon uses them.

It also fixes a bug in the donor while it is here. The GPMG lists TWO first-person
models, one per player species, and the Elite's points at the SNIPER RIFLE's -- so a
Dervish holding it would have been holding a sniper. Both now point at the port's.

What stays shared, deliberately: the melee damage effects, which every Halo 2 weapon
shares, and the pickup sound. Cloning those is not what "its own projectile" means, and
the Halo 1 and Halo 3 ports left them shared too. A balance row that moves melee damage
would move it for every weapon in the game -- worth knowing before one is written.

    python h2_saw_weapon.py [--force]

`--force` replaces tags that already exist; without it they are left alone, so a re-run
after hand-editing does not throw the edits away.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_tagref

B = os.sep
H2EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
TAGS = os.path.join(H2EK, 'tags')
SAW = B.join(['objects', 'weapons', 'rifle', 'saw'])
GPMG = B.join(['objects', 'weapons', 'rifle', 'gpmg'])
TURRET = B.join(['objects', 'vehicles', 'h_turret_ap'])

#: (what it is copied from, what it becomes)
CLONES = [
    (GPMG + B + 'gpmg.weapon', SAW + B + 'saw.weapon'),
    (TURRET + B + B.join(['weapon', 'h_turret_ap_bullet.projectile']),
     SAW + B + B.join(['projectiles', 'saw_bullet.projectile'])),
    (TURRET + B + B.join(['damage_effects', 'h_turret_ap_bullet.damage_effect']),
     SAW + B + B.join(['damage_effects', 'saw_bullet.damage_effect'])),
    (TURRET + B + B.join(['damage_effects', 'h_turret_ap_trigger.damage_effect']),
     SAW + B + B.join(['damage_effects', 'saw_trigger.damage_effect'])),
]

#: (tag, class, the path it currently names, what it should name instead, why)
WIRING = [
    (SAW + B + 'saw.weapon', 'hlmt', GPMG + B + 'gpmg', SAW + B + 'saw',
     'world model'),
    (SAW + B + 'saw.weapon', 'mode', GPMG + B + B.join(['fp_gpmg', 'fp_gpmg']),
     SAW + B + B.join(['fp_saw', 'fp_saw']), 'first person model, Master Chief'),
    (SAW + B + 'saw.weapon', 'mode',
     B.join(['objects', 'weapons', 'rifle', 'sniper_rifle', 'fp_sniper_rifle',
             'fp_sniper_rifle']),
     SAW + B + B.join(['fp_saw', 'fp_saw']),
     'first person model, Dervish -- the donor pointed this at the SNIPER RIFLE'),
    (SAW + B + 'saw.weapon', 'proj',
     TURRET + B + B.join(['weapon', 'h_turret_ap_bullet']),
     SAW + B + B.join(['projectiles', 'saw_bullet']), 'projectile'),
    (SAW + B + 'saw.weapon', 'jpt!',
     TURRET + B + B.join(['damage_effects', 'h_turret_ap_trigger']),
     SAW + B + B.join(['damage_effects', 'saw_trigger']), 'firing damage'),
    (SAW + B + B.join(['projectiles', 'saw_bullet.projectile']), 'jpt!',
     TURRET + B + B.join(['damage_effects', 'h_turret_ap_bullet']),
     SAW + B + B.join(['damage_effects', 'saw_bullet']), 'impact damage'),
]

#: references the port keeps pointing at somebody else's tag, and the reason
SHARED = [
    ('ui\\hud\\gpmg', 'the donor HUD -- the reason this donor was chosen'),
    ('effects\\objects\\weapons\\rifle\\gpmg\\gpmg_gun_fire',
     'firing effect, owned by the GPMG and used by nothing else'),
    ('objects\\weapons\\damage_effects\\*_melee', 'shared by every Halo 2 weapon'),
    ('sound\\weapons\\sniper_rifle\\sniper_ammo', 'pickup sound'),
]


def clone(force):
    for src, dest in CLONES:
        s, d = os.path.join(TAGS, src), os.path.join(TAGS, dest)
        if os.path.exists(d) and not force:
            print('   %-34s exists, left alone' % os.path.basename(dest))
            continue
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy(s, d)
        print('   %-34s <- %s' % (os.path.basename(dest), src))


def wire():
    for tag, cls, old, new, why in WIRING:
        path = os.path.join(TAGS, tag)
        have = h2_tagref.references(path)
        if (cls, new) in have and (cls, old) not in have:
            print('   %-34s %s already points at the port' % (os.path.basename(tag), why))
            continue
        h2_tagref.set_reference(path, cls, old, new)
        print('      (%s)' % why)


def main():
    force = '--force' in sys.argv
    print('cloning the tags the Warthog turret would otherwise share:')
    clone(force)
    print('wiring them together:')
    wire()
    print('still pointing at somebody else, on purpose:')
    for path, why in SHARED:
        print('   %-52s %s' % (path, why))
    print('what the port now owns:')
    for _src, dest in CLONES:
        print('   %s' % dest)
        for cls, path in h2_tagref.references(os.path.join(TAGS, dest)):
            mark = '  <- own' if path.startswith(SAW) else ''
            print('      %-6s %s%s' % (cls, path, mark))


if __name__ == '__main__':
    main()
