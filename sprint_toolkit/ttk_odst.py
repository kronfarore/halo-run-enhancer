r"""Time-to-kill on LEGENDARY: the Halo 3: ODST (MCC) collector (ttk_common's method; the
shared H3-engine code is ttk_h3family.py).

READ-ONLY: H3ODSTEK tags through ttk_common.flatten; writes only
reports/ttk/ttk_halo_3_odst.json.

    python ttk_odst.py

Who and what (all from the H3ODSTEK tags):
  * player: objects\characters\odst_oni_op\odst_oni_op_player.biped -> its model (new
    damage info: body 80, shield 80, shield stun time 5 s, recharge 3 s; body recharge 0).
    In ODST the "shield" is STAMINA (the red-screen pool that regenerates after the stun
    time) and the "body" is HEALTH (never regenerates; health packs restore it). Body
    material tough_organic_flesh -> armour tough_organic (a Spartan is hard_metal_thin).
    The globals' player representation (the Rookie, odst_recon.biped) has the identical
    model numbers and materials (checked at run time, see notes).
  * Brute minor: objects\characters\brute\ai\brute.character (ODST has no enemy Elites),
    body shot 'body' (tough_organic_flesh_brute -> tough_organic).
  * AI weapon: ODST squads use cells with weighted character / weapon choices; a census
    of every levels\atlas scenario (see BRUTE_WEAPON_NOTE) picks the default weapon.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ttk_h3family as fam  # noqa: E402

KIT = 'H3ODSTEK'
GAME = 'Halo 3: ODST'
C = r'objects\characters'
W = r'objects\weapons'

PLAYER = {
    'label': 'Player (ODST)',
    'biped': C + r'\odst_oni_op\odst_oni_op_player',
    'body_material': 'body',
    'explain': 'ODST: shield pool = STAMINA (regenerates after the shield stun time over the '
               'shield recharge time), body pool = HEALTH (body recharge time / fraction 0: '
               'never regenerates, health packs only). Both 80.',
}
GLOBALS_PLAYER = C + r'\odst_recon\odst_recon'
BRUTE_WEAPON_NOTE = (
    'census of every levels\\atlas scenario\'s squad cells (normal diff count x character '
    'choice chance x initial-weapon choice chance): brute.character expects 376.5 placements -- '
    'Spiker 166.3 (44%), Brute Plasma Rifle (plasma_rifle_red) 122.2 (32%), Brute Shot 34.2, '
    'no weapon named 17.0, Plasma Pistol 13.7, Carbine 9.5, Needler 8.3, Mauler 5.2. The '
    'Spiker is the default; the Brute Plasma Rifle is measured as a second AI row.')
ENEMIES = [
    ('Brute minor', C + r'\brute\ai\brute.character', 'body',
     W + r'\rifle\spike_rifle\spike_rifle', 'Spiker (AI)', BRUTE_WEAPON_NOTE),
    ('Brute minor', C + r'\brute\ai\brute.character', 'body',
     W + r'\rifle\plasma_rifle_red\plasma_rifle_red', 'Brute Plasma Rifle (AI, 2nd most common)',
     BRUTE_WEAPON_NOTE, True),
]
PLAYER_WEAPONS = [
    ('Silenced SMG', W + r'\rifle\smg_silenced\smg_silenced'),
    ('Plasma Rifle', W + r'\rifle\plasma_rifle\plasma_rifle'),
    ('Magnum (automag)', W + r'\pistol\automag\automag'),
]


def main():
    log = {}
    keys = ('maximum vitality', 'maximum shield vitality', 'global shield material name',
            'body material', 'shield stun time (recharge delay)', 'shield recharge time')
    a = fam.model_damage_info(KIT, fam.biped_model(KIT, PLAYER['biped'], log), log, 'body')
    b = fam.model_damage_info(KIT, fam.biped_model(KIT, GLOBALS_PLAYER, log), log, 'body')
    same = all(a[k] == b[k] for k in keys)
    notes = [
        'Player biped %s (as asked); the globals player representation uses %s, whose model '
        'reads %s.' % (PLAYER['biped'], GLOBALS_PLAYER,
                       'IDENTICAL (%s)' % ', '.join('%s %s' % (k, a[k]) for k in keys) if same
                       else 'DIFFERENT: %s' % {k: (a[k], b[k]) for k in keys if a[k] != b[k]}),
        'ODST stamina vs health: the model\'s shield block is the stamina bar (energy shield '
        'material energy_shield_thin_hum_recon -> armour energy_shield_thin, regenerates after '
        'the stun time), the body block is health (tough_organic armour, no regeneration).',
        'ODST has no enemy Elites; only the Brute minor is measured.',
        'AI weapon: %s' % BRUTE_WEAPON_NOTE,
    ]
    fam.run(KIT, GAME, PLAYER, ENEMIES, PLAYER_WEAPONS, notes)


if __name__ == '__main__':
    main()
