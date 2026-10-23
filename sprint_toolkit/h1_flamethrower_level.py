r"""The STOCK Halo 1 flamethrower made fit for enemy hands (Armed: Flamethrower, 2026-10-23).

Armed test 1 on a30 (user): 'they aim at the sky, and when any enemy fires the player's
flamethrower fires as well visually'. Both come from the kit tags:

  SKY   Bungie stored the render mesh tilted ~55 degrees up in its node's frame and put the
        inverse in the node's DEFAULT rotation (0, 0.462, 0, 0.887): on the ground the mesh is
        level, in a hand the engine places the node at the hand marker and the mesh points
        up. Only the cyborg's own 'flamethrower' class poses straightened it; the
        Grunts / Jackals / Elites hold it with the `pr` poses (h1_enemy_weapons teaching). The
        markers and the collision model are already level (muzzle x 0.457, coll x <= 0.445).
        -> the default rotation BAKED into the vertices (position, normal, binormal, tangent;
           the Xbox compressed set too) and the node rotation set to identity; the cyborg
           holds `ft` in its 'rifle' class like `pr` (h1_pickable_weapons.teach_cyborg ->
           copy_holds; user's choice: 'level the mesh'). The Flood combat forms pose every gun
           with one class, so the levelled mesh alone straightens theirs.
  GHOST fp_defoliant2 / fp_defoliant3 (weapon attachments at `spawn fire`, B_out = primary
        firing on) are particle systems flagged 'dont_draw_in_third_person': the engine draws
        them at the LOCAL player's first-person gun whenever ANY flamethrower fires.
        -> both attachments removed, `dont_draw_in_first_person` cleared on defoliant /
           defoliant2: the third-person flames draw in both views (user's choice).

Reads each tag from its `.before_ftlevel` backup when one exists (re-runnable, the original
kept), writes under the H1 kit lock. Ships with the next ten-level rebuild (h1_rebuild_all).

    python h1_flamethrower_level.py            (dry: prints what would change)
    python h1_flamethrower_level.py --write
"""
import argparse
import copy
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
import paths     # noqa: E402

TAGS = os.path.join(paths.HCEEK, 'tags')
BACKUP = '.before_ftlevel'
FT = r'weapons\flamethrower'
MODEL = FT + r'\flamethrower.gbxmodel'
WEAPON = FT + r'\flamethrower.weapon'
FP_SYSTEMS = (FT + r'\effects\fp_defoliant2', FT + r'\effects\fp_defoliant3')
TP_SYSTEMS = (FT + r'\effects\defoliant', FT + r'\effects\defoliant2')
# label -> the label whose weapon CLASS (pose set) it moves into (copy_holds)
HOLDS = {'ft': 'pr'}


def path(rel):
    return os.path.join(TAGS, rel)


def source(p):
    return p + BACKUP if os.path.exists(p + BACKUP) else p


def save(tag, p, write):
    if not write:
        return
    if not os.path.exists(p + BACKUP):
        shutil.copy2(p, p + BACKUP)
    tag.serialize(filepath=p, temp=False, backup=False)


def _qrot(q, v):
    """v rotated by the unit quaternion q = (i, j, k, w)."""
    i, j, k, w = q
    x, y, z = v
    # t = 2 * cross(q.xyz, v); v' = v + w * t + cross(q.xyz, t)
    tx, ty, tz = 2 * (j * z - k * y), 2 * (k * x - i * z), 2 * (i * y - j * x)
    return (x + w * tx + (j * tz - k * ty),
            y + w * ty + (k * tx - i * tz),
            z + w * tz + (i * ty - j * tx))


def _unpack(u):
    """A compressed vertex's 11/11/10-bit signed vector."""
    def s(val, bits):
        return (val - (1 << bits) if val & (1 << (bits - 1)) else val) / float((1 << (bits - 1)) - 1)
    return s(u & 0x7FF, 11), s((u >> 11) & 0x7FF, 11), s((u >> 22) & 0x3FF, 10)


def _pack(v):
    def q(x, bits):
        m = (1 << (bits - 1)) - 1
        return int(round(max(-1.0, min(1.0, x)) * m)) & ((1 << bits) - 1)
    return q(v[0], 11) | (q(v[1], 11) << 11) | (q(v[2], 10) << 22)


def level_model(write):
    from reclaimer.hek.defs.mod2 import mod2_def
    p = path(MODEL)
    t = mod2_def.build(filepath=source(p))
    d = t.data.tagdata
    node = d.nodes.STEPTREE[0]
    r = node.rotation
    q = (r.i, r.j, r.k, r.w)
    if abs(q[3]) > 0.99999:
        print('model: node rotation already identity -- nothing to bake')
        return
    verts = [v for g in d.geometries.STEPTREE for part in g.parts.STEPTREE
             for v in part.uncompressed_vertices.STEPTREE]
    # the Xbox copy (PC builds read the uncompressed set): rotated too, so the tag agrees
    packed = [v for g in d.geometries.STEPTREE for part in g.parts.STEPTREE
              for v in part.compressed_vertices.STEPTREE]
    # Halo stores the node's rotation as the frame -> parent transform's INVERSE in some
    # tags: take the sense that lays the mesh along the (level) collision model, +x forward
    def extent(qq):
        pts = [_qrot(qq, (v.position_x, v.position_y, v.position_z)) for v in verts]
        return max(p_[0] for p_ in pts), max(p_[2] for p_ in pts)
    conj = (-q[0], -q[1], -q[2], q[3])
    qq = q if extent(q)[0] > extent(conj)[0] else conj
    xmax, zmax = extent(qq)
    print('model: %d vertices baked by %s (mesh x max %.3f, z max %.3f; coll x max 0.445)'
          % (len(verts), 'the node rotation' if qq is q else 'its conjugate', xmax, zmax))
    for v in verts:
        for a, b, c in (('position_x', 'position_y', 'position_z'),
                        ('normal_i', 'normal_j', 'normal_k'),
                        ('binormal_i', 'binormal_j', 'binormal_k'),
                        ('tangent_i', 'tangent_j', 'tangent_k')):
            x, y, z = _qrot(qq, (getattr(v, a), getattr(v, b), getattr(v, c)))
            setattr(v, a, x)
            setattr(v, b, y)
            setattr(v, c, z)
    for v in packed:
        v.position_x, v.position_y, v.position_z = _qrot(qq, (v.position_x, v.position_y, v.position_z))
        for n in ('normal', 'binormal', 'tangent'):
            setattr(v, n, _pack(_qrot(qq, _unpack(getattr(v, n)))))
    print('model: %d compressed vertices rotated too' % len(packed))
    r.i = r.j = r.k = 0.0
    r.w = 1.0
    save(t, p, write)


def weapon_attachments(write):
    from reclaimer.hek.defs.weap import weap_def
    p = path(WEAPON)
    t = weap_def.build(filepath=source(p))
    att = t.data.tagdata.obje_attrs.attachments.STEPTREE
    drop = [i for i, a in enumerate(att) if a.type.filepath.lower() in [s.lower() for s in FP_SYSTEMS]]
    for i in reversed(drop):
        print('weapon: attachment %d %s (%s) removed' % (i, att[i].type.filepath, att[i].marker))
        del att[i]
    save(t, p, write)


def third_person_flames(write):
    from reclaimer.hek.defs.pctl import pctl_def
    for rel in TP_SYSTEMS:
        p = path(rel + '.particle_system')
        t = pctl_def.build(filepath=source(p))
        for pt in t.data.tagdata.particle_types.STEPTREE:
            print('%s: %s dont_draw_in_first_person %s -> off'
                  % (rel.rsplit('\\', 1)[-1], pt.name, bool(pt.flags.dont_draw_in_first_person)))
            pt.flags.dont_draw_in_first_person = False
        save(t, p, write)


def copy_holds(d, who):
    """A unit whose `ft` sits in a weapon CLASS of its own (the cyborg's 'flamethrower':
    poses tilted to straighten the old mesh) holds it in the class of its `pr` instead (the
    cyborg's 'rifle'): a copy of the `pr` weapon type labelled `ft` there, the old type
    relabelled `ft-` (no weapon uses it). An antr tag's tagdata, in place; teach_cyborg calls
    it. A class that holds `ft` AND `pr` (the Flood combat forms' one 'pistol' class for every
    gun) already poses both alike -- the levelled mesh alone straightens it, left as it is."""
    done = []
    for u in d.units.STEPTREE:
        classes = list(u.weapons.STEPTREE)
        for new, donor in HOLDS.items():
            home = next((wc for wc in classes if new in [x.label for x in wc.weapon_types.STEPTREE]), None)
            hold = next((wc for wc in classes if donor in [x.label for x in wc.weapon_types.STEPTREE]), None)
            if home is None or hold is None or home is hold:
                continue
            wt = hold.weapon_types.STEPTREE
            e = copy.deepcopy(wt[[x.label for x in wt].index(donor)])
            e.label = new
            wt.append(e)
            for x in home.weapon_types.STEPTREE:
                if x.label == new:
                    x.label = new + '-'
            done.append('%s/%s -> %s' % (u.label, home.name, hold.name))
    print('%s: %s held like %s in %d unit(s): %s'
          % (who, ', '.join(HOLDS), ', '.join(HOLDS.values()), len(done), ', '.join(done)))
    return done


def status():
    """What in the kit is NOT refitted yet ([] = all done)."""
    from reclaimer.hek.defs.mod2 import mod2_def
    from reclaimer.hek.defs.weap import weap_def
    from reclaimer.hek.defs.pctl import pctl_def
    from reclaimer.hek.defs.antr import antr_def
    todo = []
    if mod2_def.build(filepath=path(MODEL)).data.tagdata.nodes.STEPTREE[0].rotation.w < 0.99999:
        todo.append('model')
    att = weap_def.build(filepath=path(WEAPON)).data.tagdata.obje_attrs.attachments.STEPTREE
    if any(a.type.filepath.lower() in [s.lower() for s in FP_SYSTEMS] for a in att):
        todo.append('weapon')
    if any(pt.flags.dont_draw_in_first_person
           for rel in TP_SYSTEMS
           for pt in pctl_def.build(filepath=path(rel + '.particle_system')).data.tagdata.particle_types.STEPTREE):
        todo.append('flames')
    d = antr_def.build(filepath=path(r'characters\cyborg\cyborg.model_animations')).data.tagdata
    if any(x.label == 'ft' and 'pr' not in [y.label for y in wc.weapon_types.STEPTREE]
           for u in d.units.STEPTREE for wc in u.weapons.STEPTREE for x in wc.weapon_types.STEPTREE):
        todo.append('cyborg')
    return todo


def ensure():
    """h1_rebuild_all's first step (inside its kit lock): refit whatever a kit restore or an
    old tag copy put back; nothing to do on a refitted kit."""
    todo = status()
    if not todo:
        print('flamethrower refit: kit tags already refitted')
        return
    print('flamethrower refit: re-applying (%s)' % ', '.join(todo))
    apply(True)


def apply(write):
    level_model(write)
    weapon_attachments(write)
    third_person_flames(write)
    # the cyborg's holds: teach_cyborg rebuilds its antr from its own backup every run
    import h1_pickable_weapons
    h1_pickable_weapons.teach_cyborg(write)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--status', action='store_true', help='print what is not refitted, write nothing')
    a = ap.parse_args()
    if a.status:
        print(status() or 'all refitted')
        return
    apply(a.write)
    if not a.write:
        print('\n(dry run -- --write to save)')


if __name__ == '__main__':
    import kit_lock   # the shared-kit lock (H1_PORT_PLAN.md)
    with kit_lock.script('h1_flamethrower_level'):
        main()
