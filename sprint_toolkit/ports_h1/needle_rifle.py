r"""Needle Rifle (Halo Reach, wave B2): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=20, wave='B2', name='Needle Rifle', source='Halo Reach',
    messages=(73, 74), icon=40, reticle=29, label='nr', teach_from='pr',
    sound_dir='sound\\weapons\\needle_rifle_port', weapon_dir='weapons\\needle rifle',
    yardstick={
        # step 4a (user, 2026-10-10; h1_role_compare.py needle_rifle)
        'pick': 'Needler',
        'reason': ("the needle family (Reach's `needle` group = Halo 1's needle materials) and the "
                   "only Halo 1 weapon with a supercombine; FIRED LIKE A PRECISION WEAPON (Reach's "
                   "semi-auto trigger, straight unguided needle, 2x zoom). The port has its OWN "
                   "supercombine damage (a Halo 1 projectile names its own super_detonation "
                   "effect; only the count, 7, is the engine's): default Reach's 390 at 7, stuck "
                   "4 s; balanced 60 at 7 (needler ratio), stuck 0.75 s x 6/2 shot intervals "
                   "(7 needles vs Reach's 3) = 2.25 s. Per-weapon count via halo1.dll: a later "
                   "Supercombine Needle Count card for Halo 1"),
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\needle_rifle\\needle_rifle',
            'provisional': 'Needler',
            'alternatives': ['Pistol', 'Sniper Rifle'],
            'direct': None,
            'peers': ['Pistol', 'Needler', 'Sniper Rifle'],
            'why': 'magazine, semi-auto, 2x zoom, fast needle that supercombines like the needler',
            'lacks': ''}},
    # step 11: the source game's ai\generic entry (26 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\needle_rifle\\needle_rifle'},
)
