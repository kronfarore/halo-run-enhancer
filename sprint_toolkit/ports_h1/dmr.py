r"""DMR (Halo Reach, wave B1, the REACH PILOT): a MAGAZINE semi-automatic with a 3x zoom on a
copy of the Halo 1 SNIPER RIFLE (the yardstick and its bullet materials, step 4a). The
Battle Rifle (battle_rifle.py) is the nearest shape; what is new is the SOURCE GAME: Reach's
geometry, animations, textures, sounds and chud (the route this pilot proves for wave B)."""
from ._common import reserved

PORT = reserved(
    order=19, wave='B1', name='DMR', source='Halo Reach',
    messages=(71, 72), icon=39, reticle=28, label='dm', teach_from='ar',
    sound_dir='sound\\weapons\\dmr_port', weapon_dir='weapons\\dmr',
    yardstick={
        # step 4a (user, 2026-10-10): h1_role_compare.py dmr, the Reach side from
        # h3_weapon_values.py --kit reach. Reach: DMR 17.5 (bullet_fast, headshots) per 0.33 s
        # = 3.0/s, 15 (45 / 75), reload 68 / 59 fr, error 0.15 -> 2, 3x, 3000 wu/s, range 250,
        # aim 2.25/20 5/20; Reach sniper 80 per 0.75 s = 1.33/s, 4 (12 / 24), 86 / 72 fr, error
        # 0.08 -> 4, zoom (4, 10), 6000, 500, aim 0.8/20 1.6/20. H1 sniper 101 x 2/s, 4 (12 /
        # 24), 94 / 83 fr, error 0.5 flat, zoom (2, 8), 1000 wu/s, range 1000, aim 1/35 2/35.
        # Shown beside it: the pistol ratio (25 x 2.0/s = 50 dps, 22 rounds, every value
        # scaling) -- the user chose the sniper.
        'pick': 'Sniper Rifle',
        'reason': 'user, step 4a 2026-10-10: the DMR as Halo 1\'s long-range precision rifle; '
                  'H1 value = H1 sniper x Reach DMR / Reach sniper (99 dps balanced against the '
                  'H1 sniper\'s 202 and pistol\'s 88). Bullet MATERIALS = the H1 sniper bullet\'s '
                  '(user: Elite shields x2, Flood combat forms x0.05 -- Flood take ~26 s, as '
                  'with the sniper), so the template is the H1 sniper rifle. Spread: the sniper '
                  'ratio inverts (Reach sniper minimum 0.08 near zero) -> the SIBLING RULE in '
                  'Reach\'s shape (user). Zoom: Reach\'s own 3x in both (user)',
        # DEFAULT = Reach's own numbers (wave rule kept for wave B, user 2026-10-10); these are
        # the BALANCED rows (Reach DMR / Reach sniper onto the H1 sniper)
        'balanced': {
            'damage': 22.09,             # 101 x 17.5/80
            'rate': 4.5,                 # 2/s x 3.0 / 1.333 (both semi-automatic: 1 / recovery)
            'magazine': 15,              # 4 x 15/4
            'rounds_total_initial': 45,  # 12 x 45/12
            'rounds_total_maximum': 75,  # 24 x 75/24 (not dual-wieldable: no carry rule)
            'reload_s': 2.48,            # 94 fr x 68/86 (reload empty; full: 83 fr x 59/72 = 68 fr)
            # SIBLING RULE (user): the maximum by its ratio, 0.5 x 2/4 = 0.25; the minimum in
            # Reach's DMR shape, 0.25 x 0.15/2 = 0.019 (the plain ratio inverts: 0.5 x 0.15/0.08 = 0.94)
            'error_deg': (0.019, 0.25),
            'velocity': 500.0,           # 1000 x 3000/6000
            'range': 500.0,              # 1000 x 250/500
            'aim': (2.81, 35.0, 6.25, 35.0),  # 1 x 2.25/0.8, 35 x 20/20; 2 x 5/1.6, 35 x 20/20
            'zoom': 3.0,                 # user: Reach's own 3x (the ratio gave 1.5x / 2.4x)
            'melee': 55.0},              # Reach shares strike_melee: x1 = the H1 sniper's
        'measured': 'h1_role_compare.py dmr',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\dmr\\dmr',
            'provisional': 'Pistol',
            'alternatives': ['Sniper Rifle'],
            'direct': None,
            'peers': ['Pistol', 'Sniper Rifle', 'Battle Rifle'],
            'why': "semi-auto magazine 15, 3x zoom, near-instant bullet: the H1 magnum's role",
            'lacks': ''}},
    # step 11: the source game's ai\generic entry (26 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\dmr\\dmr'},
)
