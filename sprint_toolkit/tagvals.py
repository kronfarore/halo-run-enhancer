"""Write card-field values into a loose Halo 1 tag by their Assembly plugin NAME.

The balance tables name fields as the cards do ("Damage Lower Bound", "Rounds Loaded
Maximum"); Reclaimer's tag defs use snake_case and nest them in structs, and a plugin
"X" / "X Max" pair is one Reclaimer range (from / to). This resolves a plugin name to a
(block path, attribute, range half) and sets it.

    from tagvals import set_field, read_field
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa


def _norm(s):
    return str(s).lower().replace('/', ' ').replace('-', ' ').replace('_', ' ').split()


def _walk(node, path=(), depth=0):
    """(path, attr name, parent) for every scalar / range attribute in a tag block."""
    if depth > 6:
        return
    try:
        names = [node.get_desc('NAME', i) for i in range(len(node))]
    except Exception:
        return
    for i, name in enumerate(names):
        try:
            v = node[i]
        except Exception:
            continue
        if isinstance(v, (int, float, str)) or hasattr(v, 'enum_name'):
            yield path, name, node
        elif hasattr(v, 'STEPTREE') and not hasattr(v, 'filepath'):
            # a block array: walk its elements (magazines, triggers, ...)
            try:
                elems = list(v.STEPTREE)
            except Exception:
                elems = []
            for k, el in enumerate(elems):
                yield from _walk(el, path + ('%s[%d]' % (name, k),), depth + 1)
        elif hasattr(v, 'get_desc') and not hasattr(v, 'filepath'):
            sub = []
            try:
                sub = [v.get_desc('NAME', k) for k in range(len(v))]
            except Exception:
                pass
            if sub and all(s in ('from', 'to') for s in sub):
                yield path, name, node                      # a range: from / to
            else:
                yield from _walk(v, path + (name,), depth + 1)


def _is_range(v):
    """True for a Reclaimer range block (a plugin "X" / "X Max" pair), not an enum."""
    if isinstance(v, (int, float, str)) or hasattr(v, 'enum_name'):
        return False
    try:
        return [v.get_desc('NAME', k) for k in range(len(v))] == ['from', 'to']
    except Exception:
        return False


def resolve(tagdata, plugin_name):
    """(owner block, attribute, half) for a plugin field name, or None. `half` is
    'to' when the name ends in Max and the attribute is a range."""
    want = _norm(plugin_name)
    is_max = want and want[-1] == 'max'
    base = want[:-1] if is_max else want
    best = None
    for path, name, owner in _walk(tagdata):
        n = _norm(name)
        if n == base or n == want:
            v = owner[name]
            is_range = _is_range(v)
            if n == want and not is_max:
                return owner, name, ('from' if is_range else None)
            if is_max and is_range:
                return owner, name, 'to'
            if best is None:
                best = (owner, name, 'from' if is_range else None)
    return best


def set_field(tagdata, plugin_name, value):
    hit = resolve(tagdata, plugin_name)
    if hit is None:
        return False
    owner, name, half = hit
    cur = owner[name]
    if half:
        cur[half] = value
    elif hasattr(cur, 'enum_name'):
        cur.data = int(value)          # an enum: set its value, don't replace the block
    elif isinstance(cur, float):
        owner[name] = float(value)
    else:
        owner[name] = int(round(value))      # the FIELD's type decides, not the value's
    return True


def read_field(tagdata, plugin_name):
    hit = resolve(tagdata, plugin_name)
    if hit is None:
        return None
    owner, name, half = hit
    v = owner[name]
    return v[half] if half else v
