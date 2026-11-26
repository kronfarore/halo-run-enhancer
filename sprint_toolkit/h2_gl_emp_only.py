r"""The Halo 2 Grenade Launcher's ISOLATED VEHICLE-STALL TEST (B4, user boot 4: 'the vehicles mostly die to the damage
and get knocked around'): in a BUILT test map (h2_port_test_map.py ... --level 06b_floodzone, then this on
H2EK\h2_maps_win64_dx11\port_test\06b_floodzone.map, then copy it live), the release grenade does the EMP alone --
its tethered blast a token 5 damage, no knockback, the shared impact 0. The kit is never touched. Result (boot 8):
no stall -- Halo 2's unused `side effect` emp does nothing visible.

    python h2_gl_emp_only.py <built map path>
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import halo_patch as hp
import ai_firing_profile as A

M = sys.argv[1]
m = hp.open_map(M, 'Halo 2')
pl = A._plugins()('Halo 2').get('jpt!')
D = r'objects\weapons\rifle\grenade_launcher\damage_effects' + '\\'
for tag in ('grenade_launcher_tethered_explosion', 'grenade_launcher_impact'):
    for field in ('Damage Lower Bound', 'Damage Upper Bound', 'Damage Upper Bound Max', 'Instantaneous Acceleration'):
        # a token 5 damage (boot 8: it popped the then-spawned EMP grenade; harmless to a vehicle)
        v = 5.0 if (tag == 'grenade_launcher_tethered_explosion' and field.startswith('Damage')) else 0.0
        for r in m.apply_field('jpt!', D + tag, field, 'set', v, pl):
            print(tag, field, r.get('old'), '->', r.get('new'), '' if r.get('ok') else 'NOT OK %s' % r.get('reason'))
for field in ('Damage Lower Bound', 'Damage Upper Bound', 'EMP Radius', 'Radius Max'):
    print('emp', field, m.read_field('jpt!', D + 'grenade_launcher_emp', field, pl) if hasattr(m, 'read_field') else '')
m.save()
print('saved', M)
