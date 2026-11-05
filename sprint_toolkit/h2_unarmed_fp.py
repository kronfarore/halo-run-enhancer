r"""A first-person model and graphs for the Halo 2 sprint token, so the flashlight holds still
while sprinting (user 2026-11-03: 'flashlight anchor without weapon is weird').

WHY. Sprint hands the player objects\weapons\melee\unarmed\unarmed (h2_sprint.py), whose
`first person` block is EMPTY: no first-person model, no graph. In first person the engine hangs
the flashlight on the first-person model's `flashlight` marker -- the arms' fp.render_model carry
it on node `base` (Chief stock; the Arbiter's since h2_arbiter_flashlight) -- and with no
first-person graph there are no first-person arms, so the light fell through to the 3P marker
(Chief b_head, Arbiter neck) and swung with the run cycle.

WHAT. Three new tags and one edit, all in the kit:
  * objects\weapons\melee\unarmed\fp_unarmed\fp_unarmed.render_model -- one node `frame gun`,
    one 0.01-unit triangle on Bungie's invisible shader, behind the camera;
  * objects\characters\{masterchief,dervish}\fp\weapons\melee\fp_unarmed\fp_unarmed
    .model_animation_graph -- idle / ready / put_away, every frame the arms' bind with every node
    but `base` moved PARK behind the camera (nothing shows), `base` at its bind (the light's anchor,
    as Bungie's graphs keep it), camera_control at identity;
  * unarmed.weapon's `first person` block: two elements (masterchief, dervish) pointing at them.
    The block is spliced from scratch (an empty block emits no chunk -- memory
    halo2-loose-tag-format) and the place PROVED by tool's own XML: the block must read back
    and every other line of the export must equal the original's, else the tag is restored.

    python h2_unarmed_fp.py --check
    python h2_unarmed_fp.py --write          (H2 kit lock; backups <tag>.prefp)

CONFIRMED in game 2026-11-05 (06b Arbiter, 03b Chief): the light holds still while sprinting,
nothing shows, sprint timing and melee unchanged, partner view fine.

The levels carry it after a rebuild (unarmed is in every level: h2_rebuild_all / test maps).
"""
import argparse
import difflib
import os
import re
import shutil
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h2_jms  # noqa: E402
import h2_port_fp_anims as fa  # noqa: E402

H2EK = fa.H2EK
TAGS = os.path.join(H2EK, 'tags')
DATA = os.path.join(H2EK, 'data')
WEAPON = r'objects\weapons\melee\unarmed\unarmed'
FP_DIR = r'objects\weapons\melee\unarmed\fp_unarmed'
FP_MODEL = FP_DIR + r'\fp_unarmed'
SHADER_SRC = r'scenarios\objects\special\shaders\invisible.shader'
SHADER = r'objects\weapons\melee\unarmed\shaders\invisible.shader'
SPECIES = {
    'masterchief': (DATA + r'\!extracted\fp_arms_masterchief\fp_arms.jms',
                    r'objects\characters\masterchief\fp\weapons\melee\fp_unarmed'),
    'dervish': (DATA + r'\!extracted\fp_arms_dervish\dervish_fp_arms.jms',
                r'objects\characters\dervish\fp\weapons\melee\fp_unarmed'),
}
#: wu added to every arm / weapon node: a metre-and-a-half behind the camera (it looks along +x)
PARK = (-0.5, 0.0, 0.0)
#: (animation, frames written; tool drops the last). Short ready / put_away: the token was instant
ANIMS = [('first_person:idle', 3), ('first_person:ready', 3), ('first_person:put_away', 3)]

FP_FIELD = 0x50 + 0x3C0         # weap root: the `first person` tagblock (count, address, definition)
FP_ELEM = 0x20                  # mode tagref + jmad tagref


def graph(sp):
    return SPECIES[sp][1] + '\\' + os.path.basename(SPECIES[sp][1])


# --- the invisible weapon model -----------------------------------------------------------
def write_model():
    os.makedirs(os.path.dirname(os.path.join(TAGS, SHADER)), exist_ok=True)
    if not os.path.exists(os.path.join(TAGS, SHADER)):
        shutil.copy(os.path.join(TAGS, SHADER_SRC), os.path.join(TAGS, SHADER))
    m = h2_jms.Model()
    m.nodes.append(h2_jms.Node('frame gun', -1, (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0)))
    m.materials.append(h2_jms.Material('invisible', '(1) standard standard'))
    x = PARK[0] * fa.UNITS
    for p in ((x, 0.0, 0.0), (x, 0.01, 0.0), (x, 0.0, 0.01)):
        m.verts.append(h2_jms.Vertex(p, (1.0, 0.0, 0.0), [(0, 1.0)], [(0.0, 0.0)]))
    m.tris.append((0, (0, 1, 2)))
    path = os.path.join(DATA, FP_DIR, 'render', 'fp_unarmed.jms')
    h2_jms.write(path, m)
    p = subprocess.run([os.path.join(H2EK, 'tool.exe'), 'render', FP_DIR], cwd=H2EK,
                       capture_output=True, text=True, errors='replace')
    text = ((p.stdout or '') + (p.stderr or '')).replace('\r', '\n')
    print('   tool render %s: %s' % (FP_DIR, '; '.join(
        ln.strip() for ln in text.split('\n') if 'triangle' in ln.lower() or 'error' in ln.lower())
        or 'done'))
    if not os.path.exists(os.path.join(TAGS, FP_MODEL + '.render_model')):
        raise SystemExit('tool render wrote no %s.render_model:\n%s' % (FP_MODEL, text[-1500:]))


# --- the graphs ---------------------------------------------------------------------------
def frames(arms):
    """[(name, parent)], the one parked frame [(q (w,x,y,z), t wu)] in that order."""
    jm = h2_jms.read(arms)
    names = [fa.h1_key(n.name) for n in jm.nodes] + ['gun', 'camera_control']
    nodes = [(names[i], n.parent) for i, n in enumerate(jm.nodes)]
    nodes += [('gun', 0), ('camera_control', 0)]
    fr = []
    for n in jm.nodes:
        q = (n.rot[3], n.rot[0], n.rot[1], n.rot[2])
        t = tuple(c / fa.UNITS for c in n.pos)
        if fa.h1_key(n.name) != 'base':
            t = tuple(a + b for a, b in zip(t, PARK))
        fr.append((q, t))
    fr.append(((1.0, 0.0, 0.0, 0.0), PARK))
    fr.append(((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
    return nodes, fr


def write_graph(sp):
    arms, source = SPECIES[sp]
    nodes, fr = frames(arms)
    src = os.path.join(DATA, source, 'animations')
    if os.path.isdir(src):
        shutil.rmtree(src)
    names = [fa.jma_name(n, {'gun'}) for n, _p in nodes]
    # tool keeps no node of a pose that never moves ('Failed to find any animated nodes'): the parked
    # gun drifts 0.0001 wu a frame (well under a millimetre), so every frame is stored
    gi = [n for n, _p in nodes].index('gun')
    for name, n in ANIMS:
        rows = []
        for k in range(n):
            f = list(fr)
            q, t = f[gi]
            f[gi] = (q, (t[0], t[1], t[2] + 0.0001 * k))
            rows.append(f)
        fa.write_jma(os.path.join(src, fa.file_name(name, {}) + '.jmm'), nodes, names, rows)
    cfg = {'species': {sp: {'arms': arms, 'source': source}}, 'weapon_dir': FP_DIR}
    fa.tool_import(cfg, sp)                 # a from-scratch graph is imported twice by tool_import
    if not os.path.exists(os.path.join(TAGS, graph(sp) + '.model_animation_graph')):
        raise SystemExit('%s: tool wrote no graph' % sp)
    print('   %s: %d nodes, %s' % (sp, len(nodes), ', '.join(a for a, _n in ANIMS)))


# --- the weapon's first person block ------------------------------------------------------
def export(path):
    out = os.path.join(os.environ.get('TEMP', HERE), '_unarmed_fp.xml')
    if os.path.exists(out):
        os.remove(out)
    subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-tag-to-xml', path, out], cwd=H2EK,
                   capture_output=True, timeout=300)
    return open(out, encoding='utf-8', errors='replace').read() if os.path.exists(out) else ''


def fp_rows(xml):
    """[(first person model, first person animations)] as tool reads the block."""
    i = xml.find('<block name="first person"')
    if i < 0:
        return []
    seg = xml[i:xml.index('</block>', i)]
    return re.findall(r'name="first person model" type="mode">([^<]*)<.*?'
                      r'name="first person animations" type="jmad">([^<]*)<', seg, re.S)


def without_fp(xml):
    i = xml.find('<block name="first person"')
    if i >= 0:
        xml = xml[:i] + xml[xml.index('</block>', i) + len('</block>'):]
    return [ln for ln in xml.splitlines() if ln.strip()]


def chunk(want):
    data, pool = b'', b''
    for model, anims in want:
        for cls, path in ((b'edom', model), (b'damj', anims)):
            data += cls + struct.pack('<III', 0, len(path), 0xFFFFFFFF)
            pool += path.encode('latin-1') + b'\0'
    return b'dfbt' + struct.pack('<III', 0, len(want), FP_ELEM) + data + pool


def write_block():
    tag = os.path.join(TAGS, WEAPON + '.weapon')
    bak = tag + '.prefp'
    if not os.path.exists(bak):
        shutil.copy2(tag, bak)
    original = open(bak, 'rb').read()
    want = [(FP_MODEL, graph('masterchief')), (FP_MODEL, graph('dervish'))]
    open(tag, 'wb').write(original)
    base = export(tag)                  # tool reads only a .weapon: the stock bytes, back in place
    if not base:
        raise SystemExit('tool could not export the stock unarmed.weapon')
    if fp_rows(base):
        raise SystemExit('the backup already has a first person block -- not the stock tag')
    ref = without_fp(base)
    count = struct.unpack_from('<I', original, FP_FIELD)[0]
    if count:
        raise SystemExit('unarmed first person count is %d, expected 0' % count)
    # child data runs in FIELD order, tagref paths and block chunks alike: the block goes where the
    # Battle Rifle has its own -- just before the next field's path (`new hud interface`, ui\hud\
    # unarmed). Every later chunk start and the end of the file are tried after it
    hud = original.rfind(b'ui\\hud\\')
    places = ([hud] if hud > 0 else []) + [m.start() for m in re.finditer(b'dfbt', original)
                                         if m.start() > 0x40] + [len(original)]
    for at in places:
        d = bytearray(original[:at] + chunk(want) + original[at:])
        struct.pack_into('<I', d, FP_FIELD, len(want))
        open(tag, 'wb').write(d)
        xml = export(tag)
        got = [tuple(r) for r in fp_rows(xml)]
        same = without_fp(xml)[1:] == ref[1:]
        print('   place %#x: block %s, rest %s' % (at, got or '-', 'equal' if same else
                                                   '%d lines differ' % sum(
                                                       1 for ln in difflib.unified_diff(ref, without_fp(xml))
                                                       if ln[:1] in '+-')))
        if got == want and same:
            print('unarmed.weapon: first person block written at %#x (backup %s)' % (at, bak))
            return
    open(tag, 'wb').write(original)
    raise SystemExit('no place read back clean -- unarmed.weapon restored')


def check():
    tag = os.path.join(TAGS, WEAPON + '.weapon')
    print('fp model  %s: %s' % (FP_MODEL, os.path.exists(os.path.join(TAGS, FP_MODEL + '.render_model'))))
    for sp in SPECIES:
        print('graph     %s: %s' % (graph(sp), os.path.exists(os.path.join(TAGS, graph(sp) + '.model_animation_graph'))))
    print('unarmed.weapon first person: %s' % (fp_rows(export(tag)) or 'EMPTY (stock)'))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args(argv)
    if a.write:
        import kit_lock
        with kit_lock.held('h2_unarmed_fp --write', owner='unarmed_fp', kit='h2'):
            write_model()
            for sp in SPECIES:
                write_graph(sp)
            write_block()
    check()


if __name__ == '__main__':
    main()
