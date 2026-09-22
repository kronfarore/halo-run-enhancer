r"""Give the Halo 3 SAW its own WORLD model -- what you see on the ground and in other
people's hands.

The first-person model is reached straight from the weapon tag; the world model is not.
It hangs off the weapon's `hlmt`, which is still the Assault Rifle's, so the SAW needs
its own model tag too:

    saw.weapon --hlmt--> saw model --mode--> the SAW's third-person render model

The third-person skeleton is the first-person one minus `switch` (gun, magazine,
ophandle, safety), so the same converter builds it from assault_rifle.render_model's XML.
Both references are 49 characters on the Assault Rifle, so both replacements are named to
that length and overwritten in place.

The model's collision, physics and animation references stay the Assault Rifle's: the SAW
is the same size and is meant to animate like one.

    python h3_saw_world_model.py [--write]
"""
import argparse, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))  # balance tables live beside the JMS converters, see the port backup on F:
sys.path.insert(0, HERE)
import h3tag                                                    # noqa: E402

B = os.sep
H3EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
TAGS = os.path.join(H3EK, 'tags')
AR = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'assault_rifle'])
SAW_DIR = B.join(['objects', 'weapons', 'rifle', 'saw'])
RENDER_DIR = B.join(['objects', 'weapons', 'rifle', 'saw_3p'])          # where tool renders
SAW_MODEL = SAW_DIR + B + 'saw_h4_original_numbers'                     # the hlmt, 49
SAW_RENDER = SAW_DIR + B + 'saw_world_model_h4_port'                    # the mode, 49
WEAPON = SAW_DIR + B + 'saw'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    print('both references are %d characters on the Assault Rifle:' % len(AR))
    for p in (SAW_MODEL, SAW_RENDER):
        print('   %-52s %d%s' % (p, len(p), '' if len(p) == len(AR) else '  <== MUST MATCH'))
    if any(len(p) != len(AR) for p in (SAW_MODEL, SAW_RENDER)):
        raise SystemExit('name lengths differ')
    if not a.write:
        print('\n(dry run -- pass --write)')
        return

    # shaders must resolve from the render folder, or tool substitutes shaders\invalid
    src_sh = os.path.join(TAGS, SAW_DIR, 'shaders')
    dst_sh = os.path.join(TAGS, RENDER_DIR, 'shaders')
    os.makedirs(dst_sh, exist_ok=True)
    for f in os.listdir(src_sh):
        shutil.copy2(os.path.join(src_sh, f), os.path.join(dst_sh, f))
    print('\nshaders copied to %s' % RENDER_DIR)

    r = subprocess.run([os.path.join(H3EK, 'tool.exe'), 'render', RENDER_DIR, 'final'],
                       cwd=H3EK, capture_output=True, text=True, errors='replace')
    out = (r.stdout or '') + (r.stderr or '')
    for line in out.splitlines():
        if 'writing out render model' in line or 'nodes and' in line:
            print('   %s' % line.strip())
    built = os.path.join(TAGS, RENDER_DIR, 'saw_3p.render_model')
    if not os.path.exists(built):
        raise SystemExit('render failed: no ' + built)
    dst = os.path.join(TAGS, SAW_RENDER + '.render_model')
    shutil.copy2(built, dst)
    print('   render model -> %s' % SAW_RENDER)

    # the model tag: the Assault Rifle's, pointed at the SAW's render model
    shutil.copy2(os.path.join(TAGS, AR + '.model'), os.path.join(TAGS, SAW_MODEL + '.model'))
    t = h3tag.Tag(os.path.join(TAGS, SAW_MODEL + '.model'))
    n = t.repoint_in_place(AR, SAW_RENDER, group='mode')
    t.save()
    print('   model %s -> render model (%d reference(s))' % (SAW_MODEL, n))

    # and the weapon, pointed at that model
    w = h3tag.Tag(os.path.join(TAGS, WEAPON + '.weapon'))
    before = len(w.data)
    n = w.repoint_in_place(AR, SAW_MODEL, group='hlmt')
    if len(w.data) != before:
        raise SystemExit('file size changed -- not an in-place overwrite')
    w.save()
    print('   weapon -> model (%d reference(s))' % n)
    print('\nNow rebuild 010_jungle.')


if __name__ == '__main__':
    main()
