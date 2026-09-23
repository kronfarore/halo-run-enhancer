"""What the live Halo 3 map actually holds for the SAW port, and for its donor."""
import contextlib, io, os, sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he
import halo_patch as hp
import halo3_reload as hr

B = os.sep
he.load_settings()
live = os.path.join(he.mcc_root(), 'halo3', 'maps', '010_jungle.map')
with contextlib.redirect_stdout(io.StringIO()):
    m = hp.open_map(live, 'Halo 3')
reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                        he.CONFIG.get('plugin_subdirs_by_game', {}).get('Halo 3', []))
w, c, pr = reg.get('weap'), reg.get('chdt'), reg.get('proj')
SAW = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw'])
AR = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'assault_rifle'])
SAW_B = B.join(['objects', 'weapons', 'rifle', 'saw', 'projectiles',
                'saw_bullet_h4_original_numbers'])
AR_B = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'projectiles',
               'assault_rifle_bullet'])
SAW_FP = B.join(['objects', 'weapons', 'rifle', 'saw', 'fp', 'fp_saw_*'])
AR_FP = B.join(['objects', 'characters', '*', 'fp', 'weapons', 'rifle',
                'fp_assault_rifle', 'fp_assault_rifle'])

rows = [
    ('icon', hex(int(m.read_first('weap', SAW, 'Private Use Font Icon', w, None))),
     hex(int(m.read_first('weap', AR, 'Private Use Font Icon', w, None)))),
    ('magazine', m.read_first('weap', SAW, 'Rounds Loaded Maximum', w, 'Magazines'),
     m.read_first('weap', AR, 'Rounds Loaded Maximum', w, 'Magazines')),
    ('low-ammo warning',
     m.read_first('chdt', B.join(['ui', 'chud', 'saw']),
                  'Low Ammo Loaded Threshold', c, None),
     m.read_first('chdt', B.join(['ui', 'chud', 'assault_rifle']),
                  'Low Ammo Loaded Threshold', c, None)),
    ('bullet velocity', m.read_first('proj', SAW_B, 'Initial Velocity', pr, None),
     m.read_first('proj', AR_B, 'Initial Velocity', pr, None)),
    ('reload frames',
     [f for _x, f in hr.reload_frames(m, SAW_FP, game='Halo 3', match=('reload',))],
     [f for _x, f in hr.reload_frames(m, AR_FP, game='Halo 3', match=('reload',))]),
    ('ready frames',
     [f for _x, f in hr.reload_frames(m, SAW_FP, game='Halo 3', match=('ready',))],
     [f for _x, f in hr.reload_frames(m, AR_FP, game='Halo 3', match=('ready',))]),
]
print('%-20s %-24s %s' % ('', 'SAW (ported)', 'Assault Rifle (donor)'))
for name, a, b in rows:
    print('%-20s %-24s %s' % (name, a, b))
