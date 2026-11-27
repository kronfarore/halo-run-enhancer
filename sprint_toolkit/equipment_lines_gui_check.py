"""Equipment upgrade lines, the GUI half of the checks (EQUIPMENT_LINES_PLAN.md section 10):

    python sprint_toolkit/equipment_lines_gui_check.py

Offscreen smoke test of the refinement round: Next level H2 -> H3 with refunds on, the
recommended step, three cards, Blacklist replacing one, two picks, the round's end.
Writes nothing (saves and the patch-log append are stubbed)."""
import contextlib
import io
import os
import sys

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
import halo_enhancer as he  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

he.load_settings()
he.save_settings = lambda: True
he.write_json_atomic = lambda *a, **k: None
he.HaloGUI.show_start_dialog = lambda self: None
he.HaloGUI._ensure_map_pools = lambda self, mid: None
he.HaloGUI._ensure_game_pools = lambda self: None
he.HaloGUI._level_patch_file = lambda self, game, mid: None
he.CONFIG.update({'equipment_lines_enabled': True, 'equipment_refund_enabled': True,
                  'equipment_refund_percent': 50, 'sprint_feature': True,
                  'remove_invincibility_invisibility': False})
FAILS = []


def check(cond, what):
    print(('  ok   ' if cond else '  FAIL ') + what)
    if not cond:
        FAILS.append(what)


app = QApplication.instance() or QApplication(sys.argv)
with contextlib.redirect_stdout(io.StringIO()):
    gui = he.HaloGUI()
rs, db = gui.run_state, gui.db
rs.phase = 'complete'
rs.player1_weapons, rs.player1_weapon = ['Assault Rifle', he.CAMO_ITEM], 'Assault Rifle'
rs.player2_weapons, rs.player2_weapon = ['Pistol'], 'Pistol'
cd = dict(next(m for m in db.positive_pool if m['name'] == 'Camo Duration'))
for _ in range(3):
    rs.rounds.append({'player1': {'weapon': 'Assault Rifle', 'mod': cd, 'gained_weapon': None},
                      'player2': {'weapon': 'Pistol', 'mod': None, 'gained_weapon': None},
                      'enemy1': None, 'enemy2': None, 'wildcard': None,
                      'boss1': None, 'boss2': None})


def game_index(name):
    return next(i for i in range(gui.game_combo.count()) if gui.game_combo.itemData(i) == name)


gui.game_combo.setCurrentIndex(game_index('Halo 2'))
gui.mission_combo.setCurrentIndex(gui.mission_combo.count() - 1)
rs.phase = 'complete'
print('on', gui._current_game(), rs.mission_id, '-> Next level')
with contextlib.redirect_stdout(io.StringIO()):
    gui.on_next_level()
print('  now', gui._current_game(), rs.mission_id, '| status:', gui.status_label.text()[-90:])
check(rs.player1_weapons == ['Assault Rifle', 'Invisibility']
      and he.refinement_pending(rs, 'Halo 3')[0][1]['picks'] == 2,
      'Next level into H3: Invisibility, 2 refund picks pending')
check(gui._rec_kind == 'refinement' and gui.rec_step_btn.isEnabled()
      and 'REFINEMENT' in gui.rec_step_btn.text(), 'recommended step: %r' % gui.rec_step_btn.text())
check(gui.refinement_btn.isEnabled() and gui.refinement_btn.text().endswith('(2)'),
      'refinement button live: %r' % gui.refinement_btn.text())

gui.on_recommended_step()
cards = list(gui.pair_cards)
titles = [c.findChildren(he.QLabel)[0].text() for c in cards]
check(len(cards) == 3 and all('refund pick 1 of 2' in t for t in titles),
      '3 cards, titled %r' % titles[0])
mods = [p['player1_mod']['name'] for p in rs.pairs]
check(len(set(mods)) == 3 and all(p['player1_mod'].get('equipment') == 'Invisibility'
                                  for p in rs.pairs), 'three distinct Invisibility cards %s' % mods)
rerolls = [b for c in cards for b in c.findChildren(QPushButton) if 'Reroll' in b.text()]
check(rerolls and not any(b.isVisibleTo(c) for c in cards for b in c.findChildren(QPushButton)
                          if 'Reroll' in b.text()), 'no Reroll button on refinement cards')
check(not gui.save_btn.isEnabled() and not gui.refinement_btn.isEnabled() is False,
      'save is off mid-round')
# Blacklist one: a replacement comes in (Invisibility has 4 cards)
p0 = rs.pairs[0]
gui.add_to_blacklist(p0['player1_mod'], p0['id'], 'player1')
mods2 = [p['player1_mod']['name'] for p in rs.pairs]
check(len(mods2) == 3 and mods[0] not in mods2 and set(mods[1:]) <= set(mods2),
      'Blacklist replaced %s: %s' % (mods[0], mods2))
p0 = rs.pairs[0]
gui.add_to_blacklist(p0['player1_mod'], p0['id'], 'player1')
mods3 = [p['player1_mod']['name'] for p in rs.pairs]
check(len(mods3) == 2, 'nothing left to replace with: the offer shrinks to %s' % mods3)
n_rounds = len(rs.rounds)
gui.on_pair_selected(rs.pairs[0]['id'])
check(len(rs.rounds) == n_rounds + 1 and rs.rounds[-1].get('kind') == 'refinement'
      and rs.rounds[-1]['player1']['mod']['name'] == mods3[0]
      and he.refinement_pending(rs, 'Halo 3')[0][1]['picks'] == 1,
      'pick 1 recorded as a refinement round; 1 pick left')
titles = [c.findChildren(he.QLabel)[0].text() for c in gui.pair_cards]
check(gui.pair_cards and all('refund pick 2 of 2' in t for t in titles),
      'next offer: %d card(s), %r' % (len(gui.pair_cards), titles[0] if titles else None))
gui.on_pair_selected(rs.pairs[0]['id'])
check(not he.refinement_pending(rs, 'Halo 3') and not gui.pair_cards
      and rs.phase == 'complete' and gui.save_btn.isEnabled(),
      'round over: nothing pending, save back on')
check(not gui.refinement_btn.isEnabled() and gui._rec_armed
      and gui._rec_kind == he.recommended_kind(gui.mission_combo.currentIndex()),
      'button off; recommended step re-armed with %r' % gui.rec_step_btn.text())
hist = gui.history_text.toPlainText()
lines = [l for l in hist.splitlines() if l.startswith(('♻', '⌛', 'Round'))]
print('  history:')
for l in lines:
    print('    ' + l[:130])
check(sum(1 for l in lines if l.startswith('♻ Refinement (Halo 3)')) == 2
      and 'Round 3:' in hist and 'Round 4:' not in hist,
      'history: 2 refinement lines, normal rounds still numbered 1-3')
check(rs.levels[-1]['rounds_total'] == 3, 'the level record counts 3 rounds')
print('\nGUI SMOKE', 'PASSED' if not FAILS else '%d FAILED' % len(FAILS))
sys.exit(1 if FAILS else 0)
