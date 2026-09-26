"""Locate objects inside a JSON text by position, so a key can be inserted without
re-serialising the file (halo.json is hand-formatted; json.dump would rewrite all of it).

target_spans(text) -> [(path, start, end)] for every object in a `targets` list, where
`path` is the key path of the card that owns the list and text[start] == '{'.
"""
import json

_WS = ' \t\r\n'
_dec = json.JSONDecoder()


def _skip(t, i):
    while i < len(t) and t[i] in _WS:
        i += 1
    return i


def _value(t, i, path, in_targets, out):
    i = _skip(t, i)
    c = t[i]
    if c == '{':
        start = i
        i = _skip(t, i + 1)
        # A per-game `targets` map ({"Halo 1": [...], "Halo 3": [...]}) is not a target:
        # its values are the target lists. Parse it as a container of those.
        game_map = False
        if in_targets and t[i] == '"':
            k0, _ = _dec.raw_decode(t, i)
            game_map = isinstance(k0, str) and (k0.startswith('Halo') or k0 == 'default')
        if t[i] == '}':
            end = i + 1
        else:
            while True:
                i = _skip(t, i)
                key, i = _dec.raw_decode(t, i)
                i = _skip(t, i)
                assert t[i] == ':', (i, t[i - 20:i + 20])
                i = _value(t, i + 1, path + [key] if not game_map else path,
                           key == 'targets' or game_map, out)
                i = _skip(t, i)
                if t[i] == ',':
                    i += 1
                    continue
                assert t[i] == '}', (i, t[i - 20:i + 20])
                end = i + 1
                break
        if in_targets and not game_map:
            out.append((tuple(path[:-1]) if path and path[-1] == 'targets' else tuple(path),
                        start, end))
        elif _CARDS is not None and '"targets"' in t[start:end]:
            _CARDS.append((tuple(path), start, end))
        return end
    if c == '[':
        i = _skip(t, i + 1)
        if t[i] == ']':
            return i + 1
        k = 0
        while True:
            # elements of a `targets` list are the target objects themselves
            i = _value(t, i, path, in_targets, out) if in_targets else \
                _value(t, i, path + [k], False, out)
            k += 1
            i = _skip(t, i)
            if t[i] == ',':
                i += 1
                continue
            assert t[i] == ']', (i, t[i - 20:i + 20])
            return i + 1
    _v, i = _dec.raw_decode(t, i)
    return i


_CARDS = None


def card_spans(text):
    """[(path, start, end)] for every object that holds a `targets` list somewhere
    inside it, innermost first -- filter on the path for the card level wanted."""
    global _CARDS
    _CARDS = []
    try:
        _value(text, 0, [], False, [])
        return _CARDS
    finally:
        _CARDS = None


def target_spans(text):
    out = []
    _value(text, 0, [], False, out)
    return out
