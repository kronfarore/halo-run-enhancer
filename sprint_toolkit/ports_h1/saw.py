r"""The SAW, Halo 4 -> Halo 1 (the first port, 2026-09/10). Built by its OWN SAW-hardwired
tools (saw_build.py, saw_to_jms.py, saw_port_values.py, saw_weapon.py, h1_saw_sounds.py,
make_port_catalog.py), not by the generic pipeline: this config carries only what the
shared tools need -- its reservations (so no port takes them), its step-11 firing profile
and its backup folders."""

PORT = {
    'order': 0,
    'wave': 'pre-plan',
    'name': 'SAW',
    'source': 'Halo 4',
    'status': 'done',
    # label 'ar': the SAW is taught nothing -- it uses the Assault Rifle's animations
    'reservations': {'messages': (47, 48), 'icon': 25, 'reticle': None, 'label': 'ar',
                     'teach_from': None, 'sound_dir': r'sound\weapons\saw_port',
                     'weapon_dir': r'weapons\saw'},
    'yardstick': {'pick': 'Assault Rifle',
                  'reason': 'ratio rule against the Assault Rifle (balance_SAW_Halo4_to_Halo1.json)',
                  'candidates': {}},
    # step 11: a foreign source -- Halo 4's ai\generic firing values for the storm_lmg over
    # an AR carrier (the label search finds the base). The stored profile drops 0.4..0.8
    # loaded where m020's ai\generic says 0.2..0.4 (set over it; reproduces the stored file
    # exactly, checked 2026-10-07)
    'firing_profile': {'mode': 'source', 'from_game': 'Halo 4',
                       'from_map': r'halo4\maps\m020.map',
                       'from_weapon': r'objects\weapons\rifle\storm_lmg\storm_lmg',
                       'set': ['0x1D8=0.4000000059604645:Drop Weapon Loaded',
                               '0x1DC=0.800000011920929:Drop Weapon Loaded Max']},
}
