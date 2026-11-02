import sys, json
T = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool\sprint_toolkit'
sys.path.insert(0, T)
import ttk_common as t
S = chr(92)
W = ['rifle\\assault_rifle\\assault_rifle', 'rifle\\battle_rifle\\battle_rifle', 'rifle\\smg\\smg', 'rifle\\saw\\saw',
     'rifle\\spike_rifle\\spike_rifle', 'rifle\\shotgun\\shotgun', 'rifle\\sniper_rifle\\sniper_rifle',
     'pistol\\magnum\\magnum', 'pistol\\excavator\\excavator', 'support_high\\rocket_launcher\\rocket_launcher',
     'support_high\\flak_cannon\\flak_cannon', 'support_high\\spartan_laser\\spartan_laser',
     'support_low\\brute_shot\\brute_shot', 'support_low\\sentinel_gun\\sentinel_gun',
     'melee\\energy_blade\\energy_blade', 'melee\\gravity_hammer\\gravity_hammer',
     'turret\\machinegun_turret\\machinegun_turret', 'turret\\plasma_cannon\\plasma_cannon',
     'turret\\flamethrower\\flamethrower', 'turret\\missile_pod\\missile_pod']
for w in W:
    try:
        v = t.flatten('H3EK', 'objects\\weapons\\' + w + '.weapon')
    except SystemExit as e:
        print(w, 'ERR', e); continue
    print(w.rsplit(S, 1)[-1], {k: x[1] for k, x in v.items() if k in ('weapon class', 'weapon name')}, flush=True)
