r"""Which bitmap each Halo 3 weapon HUD widget draws, and which sprite of it.

The pairing is not in one place: the bitmap a widget uses is a tag REFERENCE, which the
Assembly plugin skips entirely, while the Sequence Index is a plugin field readable from
the map. So the references are read from the Editing Kit tag in widget order and zipped
with the sequence indices read from the map in the same order.

This is what the ammo meter question needs. `ui\chud\bitmaps\ballistic_meters` is a
1024x512 sheet of 20 sprites, all about 308 px wide but between 28 and 128 px tall --
different TICK LAYOUTS, not different widths. So which sprite a weapon picks is what
decides how many rounds its meter can show, and a port that clones the Assault Rifle's
chud inherits the Assault Rifle's.

    python h3_chud_widgets.py [--map 010_jungle]
"""
import argparse, contextlib, io, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
sys.path.insert(0, HERE)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402
import h3tag                    # noqa: E402

B = os.sep
GAME = 'Halo 3'
EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
WEAPONS = ('assault_rifle', 'smg', 'battle_rifle', 'sniper_rifle', 'shotgun',
           'needler', 'rocket_launcher', 'magnum', 'saw')
MAGAZINE = {'assault_rifle': 32, 'smg': 60, 'battle_rifle': 36, 'sniper_rifle': 4,
            'shotgun': 12, 'needler': 22, 'rocket_launcher': 2, 'magnum': 12,
            'saw': 72}


def bitmaps_in_order(name):
    """The bitmap each bitmap-widget references, in widget order, from the EK tag."""
    p = os.path.join(EK, 'tags', 'ui', 'chud', name + '.chud_definition')
    if not os.path.exists(p):
        return []
    t = h3tag.Tag(p)
    out = []

    def rec(n):
        if n.marker == 'tgrf':
            grp = bytes(t.data[n.payload_at:n.payload_at + 4])[::-1].decode('latin1')
            if grp.strip() == 'bitm':
                out.append(bytes(t.data[n.payload_at + 4:n.payload_at + n.length])
                           .decode('latin1').rsplit(B, 1)[-1])
            return
        for c in n.children:
            rec(c)
    for n in t.nodes():
        if n.parent is None:
            rec(n)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', default='010_jungle')
    a = ap.parse_args()
    he.load_settings()
    src = he.baseline_source(hp.default_map_path(he.mcc_root(), 'halo3', a.map), GAME)
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(src, GAME)
    reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                            he.CONFIG.get('plugin_subdirs_by_game', {}).get(GAME, []))
    p = reg.get('chdt')
    seq = p.find('Sequence Index', 'Widget Collections/Bitmap Widgets')

    print('%-16s %-4s %s' % ('weapon', 'mag', 'widget -> bitmap (sprite)'))
    for name in WEAPONS:
        tag = B.join(['ui', 'chud', name])
        tags = m.find_tags('chdt', tag)
        if not tags:
            continue
        base = tags[0][1]
        idx = [m.data[e + seq['offset']] for e in
               m.follow_all(base, seq['block_offsets'], seq.get('block_sizes'), 'all')]
        bm = bitmaps_in_order(name)
        pairs = []
        for i, s in enumerate(idx):
            b = bm[i] if i < len(bm) else '?'
            if b in ('ballistic_meters', 'weapon_scematics'):
                pairs.append('%s#%d' % (b.replace('weapon_scematics', 'schematic')
                                         .replace('ballistic_meters', 'meter'), s))
        print('%-16s %-4s %s' % (name, MAGAZINE.get(name, '?'), '  '.join(pairs)))


if __name__ == '__main__':
    main()
