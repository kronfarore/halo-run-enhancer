r"""Time-to-kill on LEGENDARY: the Halo 3 (MCC) collector (ttk_common's method; the shared
H3-engine code is ttk_h3family.py).

READ-ONLY: H3EK tags through ttk_common.flatten; writes only reports/ttk/ttk_halo_3.json.

    python ttk_halo3.py

Who and what (all from the H3EK tags):
  * player: objects\characters\masterchief\masterchief.biped -> masterchief.model
    (new damage info: body 45, shield 70, shield stun time 5 s), body shot = model
    material 'body' (hard_metal_thin_hum_masterchief).
  * Elite minor: objects\characters\elite\ai\elite.character (the minor; elite_major /
    elite_specops are the others). In Halo 3's campaign the Elites are mostly ALLIES
    (Arbiter, the Shipmaster's fleet from The Covenant on); measured anyway as an enemy.
    Body shot = 'armored_torso' (hard_metal_thin_cov_elite; the skinned parts resolve to
    the same hard_metal_thin armour).
  * Brute minor: objects\characters\brute\ai\brute.character, body shot 'body'
    (tough_organic_flesh_brute -> tough_organic).
  * AI weapons: a Halo 3 character names no weapon; the scenario squads give it. A census
    of every levels\solo scenario's squad fire-teams / starting locations (initial weapon,
    character palette): elite.character carries the Plasma Rifle in 14 of the 15 placements
    that name a weapon (all in 100_citadel + one in 050_floodvoi); brute.character the
    Spiker (spike_rifle) in 357 of 514 placements (Brute Shot 51, Plasma Rifle 33,
    Carbine 27, ...). The red Brute plasma rifle never appears for brute.character and
    ai\generic has no firing pattern for it.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ttk_h3family as fam  # noqa: E402

KIT = 'H3EK'
GAME = 'Halo 3'
C = r'objects\characters'
W = r'objects\weapons'

PLAYER = {
    'label': 'Player (Master Chief)',
    'biped': C + r'\masterchief\masterchief',
    'body_material': 'body',
    'explain': 'Halo 3 Spartan: shield (recharges after the shield stun time) over body '
               'vitality (no body regeneration: body recharge fraction 0).',
}
ENEMIES = [
    ('Elite minor', C + r'\elite\ai\elite.character', 'armored_torso',
     W + r'\rifle\plasma_rifle\plasma_rifle', 'Plasma Rifle (AI)',
     'from the scenario census (14 of 15 elite.character placements naming a weapon carry '
     'it); NOTE Elites are allies for most of the Halo 3 campaign'),
    ('Brute minor', C + r'\brute\ai\brute.character', 'body',
     W + r'\rifle\spike_rifle\spike_rifle', 'Spiker (AI)',
     'from the scenario census (357 of 514 brute.character placements carry it)'),
]
PLAYER_WEAPONS = [
    ('Assault Rifle', W + r'\rifle\assault_rifle\assault_rifle'),
    ('Plasma Rifle', W + r'\rifle\plasma_rifle\plasma_rifle'),
    ('Battle Rifle', W + r'\rifle\battle_rifle\battle_rifle'),
]
NOTES = [
    'AI default weapons come from a census of the squads in every levels\\solo scenario '
    '(fire-team initial weapon, overridden per starting location); Halo 3 characters carry '
    'no default weapon of their own.',
    'Halo 3 Elites fight on the player\'s side for most of the campaign; the Elite rows are '
    'measured as if hostile (Legendary enemy dials applied).',
]


def main():
    fam.run(KIT, GAME, PLAYER, ENEMIES, PLAYER_WEAPONS, NOTES)


if __name__ == '__main__':
    main()
