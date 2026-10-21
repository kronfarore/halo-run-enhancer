r"""The Flamethrower into Halo 2 -- a SPECIAL CASE outside the spreadsheet's 20 (user, 2026-10-21: "my
current play run uses it and I want it available before the next session, in case we make it to
Halo 2"). Halo 2 never had one. A phase-0 STUB (reservations, candidates, the proposed donor);
the port session fills the pipeline sections (ports_h2/assault_rifle.py is the complete Halo 3
-route example) and sets 'status' to 'in progress' at its start, 'done' at its end.

SOURCE, PROPOSED (the session confirms it with the user first): HALO 1, `HCEEK weapons\flamethrower`
-- a full first-person weapon (gbxmodel, fp\ model + FP animations, flame projectile, heat display).
Halo 3's `objects\weapons\turret\flamethrower` is a TURRET weapon: third-person only, no FP model or
graph, so it gives Halo 2 nothing to hold in first person. Halo 1's FP arm skeleton IS Halo 2's
masterchief (H2_PORT_PLAN 0.4: shoulders +-9.399, upper arm 10.25, forearm 10.89 -- "exactly Halo
1's numbers"), so its FP animations should carry to the Chief node-for-node as Halo 3's did for the
AR; the DERVISH has no Halo 1 source (Elite hands: 4 digits) -- the arm chain is the same, the
fingers are not (re-pose the hand, or the SAW route: a donor's H2 dervish graph retimed).
"""

PORT = {
    'order': 22,
    'wave': 'S1',
    'name': 'Flamethrower',
    'source': 'Halo 1',
    'status': 'in progress',
    'source_tag': r'weapons\flamethrower\flamethrower',      # HCEEK (Halo 1)
    'reservations': {
        'message_prefix': 'ft2',
        'glyph': 0xE153,                     # free in all eight English fonts (phase 0 checked E13E..E153)
        'weapon_dir': r'objects\weapons\support_low\flamethrower',
        'effects_dir': r'effects\objects\weapons\support_low\flamethrower',
        'fp_graph': r'weapons\support_low\fp_flamethrower\fp_flamethrower',
        'hud': r'ui\hud\flamethrower',
        'hud_bitmap_prefix': 'flamethrower_',
        'sound_dir': r'sound\weapons\flamethrower_port',
    },
    # PROPOSED: the AR's proven shape -- weapon cloned from the H2 SMG (spew, 1 magazine / 1 trigger /
    # 1 barrel; clear dual wield), world .model / HUD / collision from a two-handed donor (the BR's, as
    # the AR); the Halo 1 flamethrower also heats -- check whether its magazine or its heat is the
    # limit and pick the donor's block shape by that (the plasma rifle = heat + battery, 0 magazines)
    # STEP 0 (user, 2026-10-21): source HALO 1 -- the user's rule "if Halo 2 has no turret-style
    # 3rd-person weapons, Halo 1": H2EK's h_turret_mp_item / c_turret_mp_item sit in Bungie's weapon
    # palettes but carry 'cannot be used by player', no FP model / graph (3P class `missile`), and the
    # engine has no third-person hold. Dervish: RE-POSE (arms + wrists from the Chief's Halo 1 frames,
    # fingers = the Chief finger's curl as a delta on the Elite's own bind; middle dropped). Donor: the
    # SMG clone + Halo 2's heat fields (fuel AND heat, as Halo 1).
    'donor': {'weapon': r'objects\weapons\rifle\smg\smg', 'message_prefix': 'smg',
              'why': 'spew automatic magazine 1/1/1 (the AR route); alt plasma_rifle (pr) if heat is the limit'},
    'yardstick': {
        # step 4a WITH the user (2026-10-21; reports/h2_flamethrower_4a.md, h2_ft_ttk_4a.py)
        'pick': 'Plasma Rifle',
        'reason': 'native in both games and the only native candidate that also HEATS: carries damage '
                  'x0.77 (21.5 -> 16.5 a flame, 2 a shot), rate x0.9 (12 -> 10.8/s) and the heat model '
                  '(0.072 -> 0.135 a shot, loss 0.44 -> 1.25/s, recovery 0.30 -> 0.12; overheats after '
                  '~2.7 s held, Halo 1 ~3.6 s); fuel 100/300/600, reload 3.4 s and range 16 wu have no '
                  'Plasma Rifle counterpart -> Halo 1 raw. Damage group (user): Halo 2 own `burning` '
                  '(Halo 1 category flame) -- Elite 0.65 s, Brute 0.28, Jackal 0.19, Flood 0.28 point blank',
        'damage_group': 'burning',
        'candidates': {
            'provisional': 'Plasma Rifle (native in Halo 1 AND Halo 2: an automatic, close-mid range)',
            'alternatives': ['Shotgun (native in both: the close-range role)',
                             'Sentinel Beam (H2 pickable; Halo 1\'s is a PORT with DERIVED numbers -- a '
                             'ratio on it chains two derivations)',
                             'SMG (the donor; no Halo 1 SMG native -- Halo 1\'s is a port)'],
            'direct': 'none (Halo 2 has no flamethrower; H1 Flood carry it, H2 Flood carry the Flood weapons)',
            'peers': ['Shotgun', 'Plasma Rifle', 'Sentinel Beam', 'SMG', 'Energy Blade'],
            'why': 'continuous short-range flame (H1: flame projectile, burning damage over time, heat display); '
                   'the yardsticks must exist in Halo 1 AND Halo 2 with cards in both (halo.json)',
        },
    },
    # Halo 1's AI data is an actor variant, not ai\generic: ai_firing_profile.py --h2-port reads
    # Halo 3 / ODST / Reach / Halo 4 sources -- the session picks a Halo 2 stand-in entry (e.g. the
    # SMG's or the plasma rifle's) or teaches the reader Halo 1 (H2_PORT_PLAN 0.5b)
    'firing_profile': {'from_game': 'Halo 1', 'from_weapon': r'weapons\flamethrower\flamethrower',
                       'note': 'no ai\\generic source: a Halo 2 stand-in, decided in session',
                       'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties'},
    'test': {'level': '05a_deltaapproach', 'dervish_level': '06b_floodzone'},
    'residency': {'levels': 'all', 'placements': False},
}
