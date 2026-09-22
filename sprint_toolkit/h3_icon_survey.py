r"""Which pickup icon each Halo 3 weapon uses, and which icons nobody has claimed.

Halo 3 does NOT do what Halo 1 does. Halo 1 draws the "Hold E to pick up <icon>" symbol
from a bitmap SHEET, and giving a port its own icon meant rendering a new sprite and
appending a sequence (scratch make_icon.py / add_msg_icon.py). Halo 3 instead stores a
single Unicode Private Use codepoint in the WEAPON tag -- `Private Use Font Icon`, u32 --
and the HUD renders that character from maps\fonts\font_package_icon.bin. So a port's
icon is one field, not an art pipeline, PROVIDED a glyph exists at the codepoint.

The namespace is tidy:
    0xE068..0xE073   the small dual-wield icons (only dual-wieldable weapons have them)
    0xE112..0xE132   weapons, with eight unclaimed gaps inside the block
    0xE146..0xE150   equipment
The font declares 144 glyphs up to 0xE151, and the campaign claims 42 codepoints, so
there are glyphs nothing points at -- what they DRAW is the open question, since reading
them needs font_package_icon.bin decoded (and its x2 / x3 variants kept in step).

    python h3_icon_survey.py [--map 010_jungle] [--all]
"""
import argparse, contextlib, io, os, sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402

B = os.sep
GAME = 'Halo 3'
FIELDS = ('Private Use Font Icon', 'Private Use Font Icon (Dual)')
CLASSES = ('weap', 'eqip')
# what the font package's own header declares for icon\fixedsys-hud
FONT_GLYPHS, FONT_MAX_CP = 144, 0xE151


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', default='010_jungle')
    ap.add_argument('--all', action='store_true', help='every campaign mission')
    a = ap.parse_args()
    he.load_settings()

    reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                            he.CONFIG.get('plugin_subdirs_by_game', {}).get(GAME, []))
    missions = (he.CONFIG.get('h3_campaign_maps') or [a.map]) if a.all else [a.map]
    used = {}
    seen = 0
    for mission in missions:
        src = he.baseline_source(hp.default_map_path(he.mcc_root(), 'halo3', mission), GAME)
        if not os.path.exists(src):
            continue
        seen += 1
        with contextlib.redirect_stdout(io.StringIO()):
            m = hp.open_map(src, GAME)
        for cls in CLASSES:
            plugin = reg.get(cls)
            if plugin is None or plugin.find(FIELDS[0], None) is None:
                continue
            for path, _meta in m.find_tags(cls, '*'):
                for field in FIELDS:
                    try:
                        v = m.read_first(cls, path, field, plugin, None)
                    except Exception:
                        continue
                    if isinstance(v, int) and v:
                        used.setdefault(v, set()).add(path.rsplit(B, 1)[-1])
        del m

    print('%d mission(s), %d codepoint(s) claimed\n' % (seen, len(used)))
    for cp in sorted(used):
        print('   %#06x  %s' % (cp, ', '.join(sorted(used[cp]))[:64]))

    lo = min(used) if used else 0xE000
    free = [c for c in range(0xE112, FONT_MAX_CP + 1) if c not in used]
    print('\nunclaimed between the first weapon icon and the font\'s last glyph:')
    print('   inside the weapon block 0xE112..0xE132: %s'
          % ' '.join('%#06x' % c for c in free if c <= 0xE132))
    print('   above it, below equipment:              %s'
          % ' '.join('%#06x' % c for c in free if 0xE132 < c < 0xE146))
    print('\nthe font declares %d glyphs up to %#06x; %d codepoints are claimed here, so '
          'unclaimed\nglyphs exist -- but what they draw needs the font package decoded.'
          % (FONT_GLYPHS, FONT_MAX_CP, len(used)))


if __name__ == '__main__':
    main()
