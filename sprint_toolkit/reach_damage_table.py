r"""Halo Reach's globals DAMAGE TABLE (HREK): damage group x armor multipliers side by side -- step 4a's
"damage group vs Halo 1's materials" (the Focus Rifle, B7, 2026-10-12: plasma_fast vs plasma_slow /
sniper per armour class; the Plasma Repeater's RP_FAST_SLOW and the Grenade Launcher's explosion rows
came from the same table). Read-only; port_ttk.damage_tables pointed at HREK.

    python reach_damage_table.py plasma_fast plasma_slow sniper bullet_fast
    python reach_damage_table.py --groups          (the group names)

Reach armour classes of the matching models (the repeater's reading): Elite shield energy_shield_thin,
Elite BODY hard_metal_thin, Spartan the same pair, Hunter armour hard_metal_thick, Jackal shield
energy_shield_thick, Marine armour tough_inorganic, flesh soft / tough_organic.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import port_ttk  # noqa: E402


def main(argv):
    port_ttk.KIT = 'HREK'
    table, _mats = port_ttk.damage_tables()
    if not argv or argv == ['--groups']:
        print('groups:', ' '.join(sorted(table)))
        return
    arms = sorted({a for g in argv for a in table.get(g, {})})
    print('%-28s' % 'armor' + ''.join('%-14s' % g for g in argv))
    for a in arms:
        print('%-28s' % a + ''.join('%-14s' % table.get(g, {}).get(a, '-') for g in argv))


if __name__ == '__main__':
    main(sys.argv[1:])
