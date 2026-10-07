r"""Constants and helpers the per-weapon configs share."""
B = '\\'

# Halo 3 (H3EK) first-person animation graphs of the Master Chief
H3_FP_GRAPHS = r'objects\characters\masterchief\fp\weapons'

# stock Halo 1 sounds the port sounds copy their playback fields from (h1_port_sounds)
ANIMS = B.join(['sound', 'sfx', 'weapons', 'weapon_anims'])
IMPACTS = B.join(['sound', 'sfx', 'impulse', 'melee'])
PR_SOUNDS = B.join(['sound', 'sfx', 'weapons', 'plasma rifle'])


def row(cls, tag, field, value, original, card, block=None):
    """One catalog balance row (Assembly Halo1 plugin units; a range field as `<field>`
    + `<field> Max`). 'card' is a label only; the enhancer never reads it."""
    return {'class': cls, 'tag': tag, 'field': field, 'block': block, 'value': value,
            'card': card, 'original': original}


def reserved(order, wave, name, source, messages, icon, reticle, label, teach_from,
             sound_dir, weapon_dir, yardstick, firing_profile=None, notes=''):
    """A phase-0 STUB: what a port session starts from. Everything a session adds
    (model / retarget / pickable / sounds / catalog / test) goes into the same dict."""
    return {
        'order': order, 'wave': wave, 'name': name, 'source': source, 'status': 'reserved',
        'reservations': {'messages': messages, 'icon': icon, 'reticle': reticle,
                         'label': label, 'teach_from': teach_from, 'sound_dir': sound_dir,
                         'weapon_dir': weapon_dir},
        'yardstick': yardstick,
        'firing_profile': firing_profile,
        'notes': notes,
    }
