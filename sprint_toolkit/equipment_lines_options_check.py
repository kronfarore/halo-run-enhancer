"""Equipment upgrade lines, Phase 4: the Options page "Equipment lines", offscreen
(EQUIPMENT_LINES_PLAN.md section 10).

    python sprint_toolkit/equipment_lines_options_check.py

Builds the dialog with the real app stylesheet, drives the table (cell checklists, Add,
rename, Remove, Restore defaults), round-trips values() through CONFIG and renders the
page to a PNG in the temp folder for a look. Writes nothing else.
"""
import contextlib
import io
import os
import re
import sys
import tempfile

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ.setdefault('QT_QPA_FONTDIR', r'C:\Windows\Fonts')
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
import halo_enhancer as he  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402

he.load_settings()
he.save_settings = lambda: True
FAILS = []


def check(cond, what):
    print(('  ok   ' if cond else '  FAIL ') + what)
    if not cond:
        FAILS.append(what)


app = QApplication.instance() or QApplication(sys.argv)
app.setStyle('Fusion')
src = open(os.path.join(TOOL, 'halo_enhancer.py'), encoding='utf-8').read()
m = re.search(r'app\.setStyleSheet\("""(.*?)"""\)', src, re.S)
app.setStyleSheet(m.group(1))                    # the real app stylesheet

he.CONFIG.update({'equipment_lines_enabled': False, 'equipment_lines': None,
                  'equipment_refund_enabled': False, 'equipment_refund_percent': 50,
                  'remove_superflare_jammer': False})
with contextlib.redirect_stdout(io.StringIO()):
    dlg = he.OptionsDialog(None)
nav = [dlg._opt_nav.item(i).text() for i in range(dlg._opt_nav.count())]
check(nav.index('Equipment lines') == nav.index('Loadout') + 1, 'page right after Loadout')
t = dlg.el_table
nb = len(he.BUILTIN_LINES)


def cell(r, c):
    return t.cellWidget(r, c).text()


names = [t.item(r, 0).text() for r in range(t.rowCount())]
check(names == ['Sprint', 'Camo', 'Overshield', 'Regeneration', 'Shield', 'Cover', 'Mobility',
                'Decoy', 'Turret'], 'rows: %s' % names)
G = he.LINE_GAMES
col = {g: i + 1 for i, g in enumerate(G)}
check(not (t.item(0, 0).flags() & Qt.ItemIsEditable) and not t.cellWidget(1, 3).isEnabled()
      and (t.item(2, 0).flags() & Qt.ItemIsEditable) and t.cellWidget(2, 3).isEnabled(),
      'Sprint / Camo read-only and greyed; table rows editable')
check(cell(7, col['Halo 3']) == 'Jammer + Superflare', 'Decoy H3 cell: %r' % cell(7, col['Halo 3']))
check(cell(1, col['Halo 3: ODST']) == '↳ Invisibility' and cell(8, col['Halo Reach']) == '-'
      and cell(0, col['Halo 1']) == he.SPRINT_ITEM,
      'ODST follows H3 (%r); gaps read "-"; ability items shown' % cell(1, col['Halo 3: ODST']))
check(dlg.el_warn.text() == '', 'defaults: no warning')

# ---- edit cells through the checklist (its exec is driven from here) ----
plan = {}
orig_exec = QDialog.exec


def fake_exec(self_):
    if self_ is dlg:
        return orig_exec(self_)
    _d, lst, same = dlg._el_last_checklist
    want = plan['tick']
    if same is not None:
        same.setChecked(plan.get('same', False))
    plan['seen'] = {lst.item(k).data(Qt.UserRole): bool(lst.item(k).flags() & Qt.ItemIsEnabled)
                    for k in range(lst.count())}
    for k in range(lst.count()):
        it = lst.item(k)
        if it.flags() & Qt.ItemIsEnabled:
            it.setCheckState(Qt.Checked if it.data(Qt.UserRole) in want else Qt.Unchecked)
    return QDialog.Accepted


QDialog.exec = fake_exec
plan.update({'tick': ['Jet Pack', 'Thruster Pack']})
t.cellWidget(6, col['Halo 4']).click()                    # Mobility / Halo 4
check(plan['seen'].get('Active Camouflage') is False and plan['seen'].get('Thruster Pack')
      and plan['seen'].get('Jet Pack'),
      "checklist: Camo's Active Camouflage greyed, Thruster Pack free")
check(cell(6, col['Halo 4']) == 'Jet Pack + Thruster Pack', 'Mobility H4 now %r'
      % cell(6, col['Halo 4']))
plan.clear()
plan.update({'tick': [], 'same': False})
t.cellWidget(5, col['Halo 3: ODST']).click()              # Cover / ODST: own, empty
check(cell(5, col['Halo 3: ODST']) == '-', 'Cover ODST edited to a gap: %r'
      % cell(5, col['Halo 3: ODST']))
plan.clear()
plan.update({'tick': [], 'same': True})
t.cellWidget(5, col['Halo 3: ODST']).click()              # back to following Halo 3
check(cell(5, col['Halo 3: ODST']) == '↳ Instant Cover', 'Same as Halo 3 restores the follow')
QDialog.exec = orig_exec

# ---- add / rename / warnings ----
dlg._el_add()
check(t.rowCount() == 10 and 'New line' in dlg.el_warn.text(),
      'Add line: an empty row and a warning: %r' % dlg.el_warn.text())
t.item(2, 0).setText('Camo')                              # Overshield renamed to a built-in name
check('renamed to "Camo (2)"' in dlg.el_warn.text(), 'name taken -> warning')
vals = dlg.values()
lines = {ln['name']: ln for ln in vals['equipment_lines']}
check('New line' not in lines and 'Camo (2)' in lines
      and lines['Mobility']['stages']['Halo 4'] == ['Jet Pack', 'Thruster Pack']
      and 'Halo 3: ODST' not in lines['Cover']['stages'],
      'values(): empty line dropped, rename applied, cells as edited')
dlg.el_enabled_cb.setChecked(True)
dlg.el_refund_cb.setChecked(True)
dlg.el_refund_pct.setValue(35)
vals = dlg.values()
check(vals['equipment_lines_enabled'] and vals['equipment_refund_enabled']
      and vals['equipment_refund_percent'] == 40, 'switches + share 35 -> 40 (steps of 10)')
check(set(vals) >= {'equipment_lines_enabled', 'equipment_lines', 'equipment_refund_enabled',
                    'equipment_refund_percent'} and 'target_difficulty' in vals,
      'values() carries the four keys beside the rest')

# ---- round trip through CONFIG ----
for k, v in vals.items():
    he.CONFIG[k] = v
with contextlib.redirect_stdout(io.StringIO()):
    dlg2 = he.OptionsDialog(None)
names2 = [dlg2.el_table.item(r, 0).text() for r in range(dlg2.el_table.rowCount())]
check(names2[2] == 'Camo (2)' and 'New line' not in names2 and dlg2.el_warn.text() == ''
      and dlg2.el_enabled_cb.isChecked() and dlg2.el_refund_pct.value() == 40
      and dlg2.values()['equipment_lines'] == vals['equipment_lines'],
      'reopened: the saved table, no warning, switches and share kept')
check([ln['name'] for ln in he.active_lines(dlg2._el_db())][:4]
      == ['Sprint', 'Camo', 'Camo (2)', 'Regeneration'], 'active_lines follows the saved table')
he.CONFIG['equipment_lines'] = [{'name': 'Bad', 'stages': {'Halo 3': ['Plasma Pistol']}}]
with contextlib.redirect_stdout(io.StringIO()):
    dlg3 = he.OptionsDialog(None)
check('When loaded' in dlg3.el_warn.text() and dlg3.el_table.rowCount() == nb,
      'a bad saved table: dropped on load, with a warning')
dlg3._el_restore()
check(dlg3.values()['equipment_lines'] == he.default_equipment_lines()
      and dlg3.el_warn.text() == '', 'Restore defaults')
dlg3._el_remove()                     # nothing selected -> row 0 is built in
check('built in' in dlg3.el_warn.text(), 'Remove on a built-in row refuses')
dlg3.el_table.selectRow(nb + 1)       # Regeneration
dlg3._el_remove()
check([ln['name'] for ln in dlg3.values()['equipment_lines']]
      == ['Overshield', 'Shield', 'Cover', 'Mobility', 'Decoy', 'Turret'],
      'Remove line on a selected row')

# ---- render for a look (the dark-theme trap) ----
dlg2.resize(1250, 900)
dlg2._opt_nav.setCurrentRow(nav.index('Equipment lines'))
dlg2.show()
app.processEvents()
png = os.path.join(tempfile.gettempdir(), 'equipment_lines_page.png')
dlg2.grab().save(png)
print('  rendered', png)
print()
print('OPTIONS CHECK', 'PASSED' if not FAILS else '%d FAILED' % len(FAILS))
sys.exit(1 if FAILS else 0)
