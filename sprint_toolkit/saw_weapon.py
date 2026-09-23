"""Halo 1 SAW weapon tag: a copy of the Assault Rifle's with the SAW models.

    python saw_weapon.py --refs     # list the AR weapon's tag references
    python saw_weapon.py            # write tags\\weapons\\saw\\saw.weapon
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa
from reclaimer.hek.defs.weap import weap_def
from ammo_meter import step as ammo_step

TAGS = r'F:\SteamLibrary\steamapps\common\HCEEK\tags'
AR = os.path.join(TAGS, 'weapons', 'assault rifle', 'assault rifle.weapon')
OUT = os.path.join(TAGS, 'weapons', 'saw', 'saw.weapon')
B = os.sep
MAGAZINE = 72
AMMO_BITMAP = 'weapons' + B + 'saw' + B + 'bitmaps' + B + 'saw_ammo'   # ammo_meter.py
ICON_SEQUENCE = 25          # hud_msg_icons sequence of the SAW icon (add_msg_icon.py)


def walk_refs(node, path=''):
    """(path, tagref node) for every tag reference in a parsed tag."""
    try:
        name = node.NAME
    except AttributeError:
        return
    if hasattr(node, 'filepath') and hasattr(node, 'tag_class'):
        yield path + '.' + name, node
        return
    try:
        children = list(enumerate(node))
    except TypeError:
        return
    for i, ch in children:
        if hasattr(ch, 'NAME'):
            yield from walk_refs(ch, path + '.' + name)
    steptree = getattr(node, 'STEPTREE', None)
    if steptree is not None and not isinstance(steptree, (str, bytes)):
        for i, ch in enumerate(steptree):
            yield from walk_refs(ch, path + '.' + name + '[%d]' % i)


def main():
    t = weap_def.build(filepath=AR)
    d = t.data.tagdata
    d.obje_attrs.model.filepath = 'weapons' + B + 'saw' + B + 'saw'
    d.weap_attrs.interface.first_person_model.filepath = 'weapons' + B + 'saw' + B + 'fp' + B + 'fp'
    # The SAW's own first-person animation set (saw_anims.py: the AR's, retimed to the
    # SAW's reload / swap identity). Same skeleton, so the models still bind.
    d.weap_attrs.interface.first_person_animations.filepath = ('weapons' + B + 'saw' + B
                                                               + 'fp' + B + 'fp')
    mags = d.weap_attrs.magazines.STEPTREE
    if len(mags):
        m = mags[0]
        print('AR magazine:', m.rounds_recharged, m.rounds_total_initial, m.rounds_total_maximum,
              m.rounds_loaded_maximum)
        m.rounds_loaded_maximum = MAGAZINE    # the H4 SAW's belt box
        # One reload must insert the whole box: left at the AR's 60 the weapon reloads
        # twice for a 72 box (halo1-ammo-hud-shelved memory).
        m.rounds_reloaded = MAGAZINE
        m.rounds_total_initial = max(m.rounds_total_initial, 216)
        m.rounds_total_maximum = max(m.rounds_total_maximum, 432)
    # Own HUD interface: the AR's, but its pickup-prompt icon (messaging sequence into
    # the shared hud_msg_icons sheet) is the SAW's -- sequence 25, added by add_msg_icon.py.
    from reclaimer.hek.defs.wphi import wphi_def
    h = wphi_def.build(filepath=AR.replace('.weapon', '.weapon_hud_interface'))
    h.data.tagdata.messaging_information.sequence_index = ICON_SEQUENCE
    # Magazine readout: the AR's two loaded-ammo elements (tick silhouettes + threshold
    # meter) drawn for 60; ammo_meter.py builds a MAGAZINE-tick pair of our own.
    hd = h.data.tagdata
    for el, field in ((hd.static_elements.STEPTREE, 'interface_bitmap'),
                      (hd.meter_elements.STEPTREE, 'meter_bitmap')):
        for e in el:
            if e.state_attached_to.enum_name == 'loaded_ammo':
                getattr(e, field).filepath = AMMO_BITMAP + ('_alphas' if field == 'interface_bitmap' else '_meters')
                e.sequence_index = 0
                if field == 'meter_bitmap':
                    # A tick shows while threshold <= fill * alpha_multiplier / 4 + alpha_bias
                    # (fits all three in-game tests, 2026-09-19): the AR's bias 2 lit a tick
                    # ~2 units early (one at empty, doubles, full at 71 of 72); multiplier 64
                    # ran the meter 16x fast. So keep 4, drop the bias.
                    # A tick shows while threshold <= rounds * alpha_multiplier + bias
                    # (fitted to three in-game tests). ammo_meter spaces the thresholds by
                    # step(N) = 255 // N, so the multiplier is that same step: one tick per
                    # round for any magazine up to 255. N=60 gives the AR's stock 4.
                    e.alpha_multiplier = ammo_step(MAGAZINE)
                    # bias 1: the comparison is STRICT (threshold < rounds * multiplier +
                    # bias), so with bias 0 the first round lit nothing (in game, 2026-09-21).
                    e.alpha_bias = 1
                    e.value_scale = 0
    # low-ammo flash thresholds scale with the magazine (AR: 10 of 60 loaded)
    fc = hd.flash_cutoffs
    fc.loaded_ammo_cutoff = round(fc.loaded_ammo_cutoff * MAGAZINE / 60.0)
    h.filepath = OUT.replace('.weapon', '.weapon_hud_interface')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    h.serialize(temp=False, backup=False)
    d.weap_attrs.interface.hud_interface.filepath = 'weapons' + B + 'saw' + B + 'saw'
    t.filepath = OUT
    t.serialize(temp=False, backup=False)
    print('wrote', OUT, '| model', d.obje_attrs.model.filepath, '| fp',
          d.weap_attrs.interface.first_person_model.filepath, '| fp anims',
          d.weap_attrs.interface.first_person_animations.filepath)


if __name__ == '__main__':
    main()
