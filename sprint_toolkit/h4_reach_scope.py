r"""Halo 4 port, step 7 (scope): the port's OWN scope -- Reach's Focus Rifle scope -- in
H4EK, wired into the port's own HUD screen. Replaces the in-map Beam Rifle scope graft
(h4_map_poke.py --scope), which drew Halo 4's Beam Rifle scope.

HOW A HALO 4 SCOPE HANGS TOGETHER (read off the Beam Rifle's screens, 2026-10-02):
  * the scope is a TEMPLATE screen (beam_rifle_scope.cui_screen). The weapon's HUD screen
    lists it under `template instantiations` and carries one component row per template
    component (`template instantiation index` = that entry), parented under a
    transformation container (animation_container_br_scope) inside `scope_container`.
  * zoom: view_data_reader.prop_zoom_level -> zoom_decision.prop_if (compare long, "> 0",
    a `binding conversion long comparisons` row) -> zoom_on_off.prop_animation_name,
    which plays sniper_zoom_in / sniper_zoom_out / sniper_zoom_initial: the container's
    opacity 0 <-> 1.
  * the HUD feeds the template's meters by component name: weapon_data_reader.prop_heat
    -> shader_heat_bar.prop_current_meter_value, ... -> ammo_animator.prop_current_value
    -> shader_ammo_animated (the template's own binding).
  * `component indices` is sorted by STRING ID NUMBER (ManagedBlam GetRawData of the
    name), and rebuilt here after the rows are added.
  * THE RETICLE DRIFT (boot 21, "always moves to the right ... returns to the centre"):
    the Beam Rifle template's art sits in four parallax containers moved by
    parallax listener -> expression `0+(a*10)` -> container prop_left/prop_top bindings.
    The port's template drops those bindings, so nothing in it moves.

THE PORT'S TEMPLATE (ui\hud\weapons\covenant\focus_rifle\focus_rifle_scope.cui_screen) is
a copy of the Beam Rifle's with:
  * every parallax binding removed; every polyart widget hidden (prop_visible 0);
  * bitmap_bar_outlines -> the full-screen Reach art (h4_reach_scope_art.py scope_frame:
    lens mask, side frames, Reach reticle) at 0,0 1280x720;
  * bitmap_heat_bar -> meter_heat (right frame), bitmap_ammo_bar -> meter_batt (left
    frame) -- Reach's layout: heat right, battery left.
and the HUD binds weapon_data_reader.prop_charge (the battery, 0..1) into ammo_animator
and prop_heat into shader_heat_bar. The HUD's own reticle (reticule_container_template)
fades out while zoomed, since the Reach reticle is in the scope art.

    blender --background --python h4_reach_scope.py -- [--write]
Run AFTER h4_make_port_weapon.py (which re-copies the port's HUD screen) and after
h4_reach_scope_art.py --write (the bitmaps).
"""
import importlib
import os
import shutil
import sys

import bpy  # noqa: F401  (Blender's Python)

KEY = 'bl_ext.user_default.io_scene_foundry'
H4EK_TAGS = r'F:\SteamLibrary\steamapps\common\H4EK\tags'
B = '\\'
DONOR_DIR = B.join(['ui', 'hud', 'weapons', 'covenant', 'beam_rifle'])
OWN_DIR = B.join(['ui', 'hud', 'weapons', 'covenant', 'focus_rifle'])
DONOR_TEMPLATE = DONOR_DIR + B + 'beam_rifle_scope.cui_screen'
DONOR_HUD = DONOR_DIR + B + 'beam_rifle.cui_screen'
OWN_TEMPLATE = OWN_DIR + B + 'focus_rifle_scope.cui_screen'
OWN_HUD = OWN_DIR + B + 'focus_rifle.cui_screen'
BITMAPS = OWN_DIR + B + 'bitmap' + B
DONOR_CONTAINER = 'animation_container_br_scope'
CONTAINER = 'animation_container_fr_scope'
ZOOM = ('zoom_decision', 'zoom_on_off')
ZOOM_ANIMS = ('sniper_zoom_out', 'sniper_zoom_in', 'sniper_zoom_initial')
HUD_RETICLE = 'reticule_container_template'
#: the template's widgets: component -> (bitmap, left, top, width, height, opacity, tint argb)
#: rects from h4_reach_scope_art.py meter_rects()
WIDGETS = {
    'bitmap_bar_outlines': ('scope_frame', 0, 0, 1280, 720, 1.0, (1, 1, 1, 1)),
    'bitmap_heat_bar': ('meter_heat', 1070.4, 203.4, 105.8, 313.3, 0.85, (1, 1, 0.45, 0.2)),
    'bitmap_ammo_bar': ('meter_batt', 103.8, 203.4, 105.8, 313.3, 0.85, (1, 0.45, 0.75, 1)),
}
#: prop_alpha_blend_mode: the Beam Rifle's glowing art uses 1 (ADDITIVE -- a black mask
#: adds nothing: boot 22 showed only the frame lines); its dark vignette leaves it at the
#: default 0, alpha blend. The Reach frame carries the dark lens mask, so 0.
BLEND = {'bitmap_bar_outlines': 0}
#: HUD bindings the scope's meters need: (source comp, source prop, target comp, target prop)
METER_BINDINGS = (
    ('weapon_data_reader', 'prop_charge', 'ammo_animator', 'prop_current_value'),
    ('weapon_data_reader', 'prop_heat', 'shader_heat_bar', 'prop_current_meter_value'),
)

mb = None


def system(t):
    return t.tag.SelectField('system').Elements[0]


def name_of(e):
    return e.SelectField('name').GetStringData()


def find(block, name):
    for i in range(block.Elements.Count):
        if name_of(block.Elements[i]) == name:
            return block.Elements[i]
    return None


def props(comp, kind):
    return comp.SelectField('property values').Elements[0].SelectField(kind + ' properties')


def set_prop(t, comp, kind, prop, value):
    blk = props(comp, kind)
    e = find(blk, prop)
    if e is None:
        e = blk.AddElement()
        e.SelectField('name').SetStringData(prop)
    v = e.SelectField('value')
    if kind == 'tag reference':
        v.Path = t._TagPath_from_string(value)
    elif isinstance(value, (tuple, list)):
        v.SetStringData([str(x) for x in value])
    else:
        v.SetStringData(str(value))


def get_val(f):
    """A leaf field's value: string data, else the typed value (block index, flags)."""
    if hasattr(f, 'GetStringData'):
        return f.GetStringData()
    for a in ('Value', 'RawValue', 'Data'):
        if hasattr(f, a):
            return getattr(f, a)
    raise SystemExit('cannot read %s (%s)' % (f.FieldName, type(f).__name__))


def set_val(f, v):
    if hasattr(f, 'SetStringData'):
        f.SetStringData(v)
        return
    for a in ('Value', 'RawValue', 'Data'):
        if hasattr(f, a):
            setattr(f, a, type(getattr(f, a))(v) if not isinstance(v, type(getattr(f, a))) else v)
            return
    raise SystemExit('cannot write %s (%s)' % (f.FieldName, type(f).__name__))


def copy_flat(src, dst):
    """Copy an element's plain fields (string ids, enums, flags, numbers, block indices)."""
    sf, df = list(src.Fields), list(dst.Fields)
    for a, b in zip(sf, df):
        ft = str(a.FieldType)
        if ft in ('Pad', 'Skip', 'Explanation', 'Custom', 'Block', 'Struct', 'Reference', 'Data'):
            continue
        set_val(b, get_val(a))


def deep_copy(src, dst):
    """Copy element `src` into element `dst` field by field, blocks and structs included
    (no clipboard: ManagedBlam's CopyElement/PasteAppendElement go through the Windows
    clipboard, and one kit run failed there)."""
    for a, b in zip(list(src.Fields), list(dst.Fields)):
        ft = str(a.FieldType)
        if ft == 'Block':
            b.RemoveAllElements()
            for i in range(a.Elements.Count):
                deep_copy(a.Elements[i], b.AddElement())
        elif ft == 'Struct':
            deep_copy(a.Elements[0], b.Elements[0])
        elif ft == 'Reference':
            b.Path = a.Path
        elif ft == 'Data':
            b.SetData(a.GetData())
        elif ft in ('Pad', 'Skip', 'Explanation', 'Custom', 'UselessPad'):
            continue
        else:
            set_val(b, get_val(a))


def paste_copy(src_block, i, dst_block):
    """Append a deep copy of src_block[i] to dst_block (the blocks may be in different tags)."""
    e = dst_block.AddElement()
    deep_copy(src_block.Elements[i], e)
    return e


def index_of(block, name):
    for i in range(block.Elements.Count):
        if name_of(block.Elements[i]) == name:
            return i
    return -1


def raw_sid(field):
    return int.from_bytes(bytes(field.GetRawData())[:4], 'little')


def make_template(T, write):
    src = os.path.join(H4EK_TAGS, DONOR_TEMPLATE)
    dst = os.path.join(H4EK_TAGS, OWN_TEMPLATE)
    if write:
        shutil.copyfile(src, dst)
    with T(path=dst if write else src) as t:
        s = system(t)
        binds = s.SelectField('property bindings')
        for i in reversed(range(binds.Elements.Count)):
            e = binds.Elements[i]
            if e.SelectField('target component name').GetStringData() != 'shader_ammo_animated':
                binds.RemoveElement(i)
        print('template: %d binding(s) kept (the parallax ones are gone)' % binds.Elements.Count)
        comps = s.SelectField('components')
        ov0 = s.SelectField('overlays').Elements[0].SelectField('components')
        hidden = 0
        for i in range(comps.Elements.Count):
            c = comps.Elements[i]
            if c.SelectField('type').GetStringData() != 'polyart_widget':
                continue
            oc = find(ov0, name_of(c))
            if oc is not None:
                set_prop(t, oc, 'long', 'prop_visible', 0)
                hidden += 1
        print('template: %d polyart widget(s) hidden' % hidden)
        for comp, (bm, left, top, w, h, op, tint) in WIDGETS.items():
            oc = find(ov0, comp)
            set_prop(t, oc, 'tag reference', 'prop_bitmap_reference', BITMAPS + bm + '.bitmap')
            for p, v in (('prop_left', left), ('prop_top', top), ('prop_width', w),
                         ('prop_height', h), ('prop_opacity', op)):
                set_prop(t, oc, 'real', p, v)
            set_prop(t, oc, 'argb color', 'prop_tint_color', tint)
            if comp in BLEND:
                set_prop(t, oc, 'long', 'prop_alpha_blend_mode', BLEND[comp])
            print('template: %-20s -> %s at %s,%s %sx%s' % (comp, bm, left, top, w, h))
        t.tag_has_changes = write
    names = []
    with T(path=dst if write else src) as t:
        comps = system(t).SelectField('components')
        for i in range(comps.Elements.Count):
            c = comps.Elements[i]
            names.append((c.SelectField('type').GetStringData(), name_of(c),
                          c.SelectField('parent').GetStringData(),
                          get_val(c.SelectField('flags'))))
    return names


def wire_hud(T, template_comps, write):
    with T(path=os.path.join(H4EK_TAGS, DONOR_HUD)) as d, \
            T(path=os.path.join(H4EK_TAGS, OWN_HUD)) as t:
        ds, s = system(d), system(t)
        temps = s.SelectField('template instantiations')
        for i in range(temps.Elements.Count):
            if 'focus_rifle_scope' in t.get_path_str(
                    temps.Elements[i].SelectField('screen reference').Path):
                raise SystemExit('the HUD already carries the scope (re-run '
                                 'h4_make_port_weapon.py --write first for a fresh copy)')
        comps = s.SelectField('components')
        have = {name_of(comps.Elements[i]) for i in range(comps.Elements.Count)}
        if 'scope_container' not in have:
            raise SystemExit('the HUD has no scope_container')
        te = temps.AddElement()
        te.SelectField('screen reference').Path = t._TagPath_from_string(OWN_TEMPLATE)
        ti = temps.Elements.Count - 1
        rename = {DONOR_CONTAINER: CONTAINER}

        def add(typ, name, parent, flags, tidx):
            e = comps.AddElement()
            e.SelectField('type').SetStringData(typ)
            e.SelectField('name').SetStringData(name)
            e.SelectField('parent').SetStringData(parent)
            set_val(e.SelectField('flags'), flags)
            set_val(e.SelectField('template instantiation index'), tidx)
            have.add(name)
        add('transformation_container_widget', CONTAINER, 'scope_container', 0, -1)
        for typ, name, parent, flags in template_comps:
            new = name if name not in have else name + '_template'
            rename[name] = new
            # A TEMPLATE-INSTANCE row's "type" is the TEMPLATE COMPONENT'S NAME, not its
            # widget class (Bungie's Beam Rifle HUD, compiled: type == name sid on every
            # ti=1 row). Boot 22 wrote the class: the scope was never tied to its
            # zoom-faded container and drew all the time.
            add(name, new, rename.get(parent, parent) if parent else CONTAINER, flags, ti)
        dcomps = ds.SelectField('components')
        for z in ZOOM:
            e = comps.AddElement()
            copy_flat(find(dcomps, z), e)
            have.add(z)
        print('HUD: template %d -> %s, +%d components' % (ti, OWN_TEMPLATE,
                                                         len(template_comps) + 1 + len(ZOOM)))
        # component indices, sorted by string id number
        rows = sorted((raw_sid(comps.Elements[i].SelectField('name')), i)
                      for i in range(comps.Elements.Count))
        idx = s.SelectField('component indices')
        idx.RemoveAllElements()
        for _sid, i in rows:
            e = idx.AddElement()
            e.SelectField('name').SetStringData(name_of(comps.Elements[i]))
            set_val(e.SelectField('component definition index'), i)
        # overlays: the container's and the zoom components' rows, and the zoom animations
        dov, ov = ds.SelectField('overlays'), s.SelectField('overlays')
        for oi in range(ov.Elements.Count):
            o = ov.Elements[oi]
            key = (o.SelectField('resolution').GetStringData(), o.SelectField('theme').GetStringData())
            do = None
            for di in range(dov.Elements.Count):
                x = dov.Elements[di]
                if (x.SelectField('resolution').GetStringData(),
                        x.SelectField('theme').GetStringData()) == key:
                    do = x
            if do is None:
                continue
            dcs, ocs = do.SelectField('components'), o.SelectField('components')
            added = []
            for want in (DONOR_CONTAINER,) + ZOOM:
                i = index_of(dcs, want)
                if i < 0:
                    continue
                e = paste_copy(dcs, i, ocs)
                new = rename.get(want, want)
                e.SelectField('name').SetStringData(new)
                added.append(new)
            das, oas = do.SelectField('animations'), o.SelectField('animations')
            anims = []
            for an in ZOOM_ANIMS:
                i = index_of(das, an)
                if i < 0 or index_of(oas, an) >= 0:
                    continue
                a = paste_copy(das, i, oas)
                acs = a.SelectField('components')
                for k in range(acs.Elements.Count):
                    c = acs.Elements[k]
                    c.SelectField('name').SetStringData(rename.get(name_of(c), name_of(c)))
                if HUD_RETICLE in have and acs.Elements.Count:
                    # the HUD's own reticle: the inverse of the scope's opacity
                    r = paste_copy(acs, 0, acs)
                    r.SelectField('name').SetStringData(HUD_RETICLE)
                    for p in range(props_count(r)):
                        kf = r.SelectField('real properties').Elements[p].SelectField('real keyframes')
                        for q in range(kf.Elements.Count):
                            v = kf.Elements[q].SelectField('value')
                            v.SetStringData(str(1.0 - float(v.GetStringData())))
                anims.append(an)
            if added or anims:
                print('HUD overlay %s: +%s, animations +%s' % (key[0], added, anims))
        # bindings + the zoom comparison
        dbinds, binds = ds.SelectField('property bindings'), s.SelectField('property bindings')
        for i in range(dbinds.Elements.Count):
            x = dbinds.Elements[i]
            if x.SelectField('target component name').GetStringData() in ZOOM:
                copy_flat(x, binds.AddElement())
        for sc, sp, tc, tp in METER_BINDINGS:
            e = binds.AddElement()
            # conversion function: a new row's default, 'none'
            e.SelectField('source component name').SetStringData(sc)
            e.SelectField('source property name').SetStringData(sp)
            e.SelectField('target component name').SetStringData(rename.get(tc, tc))
            e.SelectField('target property name').SetStringData(tp)
        dcmp = ds.SelectField('binding conversion long comparisons')
        cmp = s.SelectField('binding conversion long comparisons')
        for i in range(dcmp.Elements.Count):
            x = dcmp.Elements[i]
            if x.SelectField('target component name').GetStringData() in ZOOM:
                copy_flat(x, cmp.AddElement())
        print('HUD: %d bindings, %d long comparisons' % (binds.Elements.Count, cmp.Elements.Count))
        d.tag_has_changes = False
        t.tag_has_changes = write


def props_count(track):
    return track.SelectField('real properties').Elements.Count


def main(argv):
    global mb
    write = '--write' in argv
    mb = importlib.import_module(KEY + '.managed_blam')
    if not mb.mb_active:
        mb.mb_init(os.path.join(H4EK_TAGS, 'globals', 'globals.globals'))
    if 'h4ek' not in str(mb.mb_path).lower():
        raise SystemExit('ManagedBlam is bound to %r, not H4EK' % mb.mb_path)
    for bm in ('scope_frame', 'meter_heat', 'meter_batt'):
        if not os.path.exists(os.path.join(H4EK_TAGS, BITMAPS + bm + '.bitmap')):
            raise SystemExit('missing %s.bitmap -- run h4_reach_scope_art.py --write' % bm)

    class T(mb.Tag):
        pass
    comps = make_template(T, write)
    if write:
        wire_hud(T, comps, write)
        print('REACHSCOPE OK')
    else:
        print('(dry run -- pass --write)')


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
