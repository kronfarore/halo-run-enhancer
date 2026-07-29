r"""Idempotent installer for sprint.hsc into HCEEK's global_scripts.hsc.

tool.exe compiles data\global_scripts.hsc into EVERY level, so that's where the
sprint logic has to live. The README's one-time "append sprint.hsc" step works for
a first install, but appending again after sprint.hsc changes would leave TWO copies
of the sprint scripts in the file (a compile error / undefined behaviour). This
module makes the install repeatable: it keeps the sprint block between sentinel
markers and rewrites just that block, so building always carries the current
sprint.hsc and re-running never duplicates.

Used automatically by sprint_build.py / batch_build.py before each build; also
runnable directly:  python install_script.py
"""
import os
import shutil

BEGIN = ';>>> SPRINT TOOLKIT (auto-managed) — do not edit between these markers >>>'
END = ';<<< SPRINT TOOLKIT <<<'

# A line that only the sprint script contains — used to detect a pre-existing
# unmarked copy (installed before markers existed) so we don't silently duplicate it.
SIGNATURE = '(script continuous sprint_control'

# The toolkit's own banner title. An unmarked block carrying this was written by an
# earlier version of the toolkit (which appended sprint.hsc verbatim, always at the
# end of the file) and can be migrated automatically; anything else is left to the
# user. Match the title regardless of the version suffix after it.
BANNER_TITLE = 'SPRINT PROTOTYPE'


def _read(path):
    with open(path, 'r', encoding='utf-8', errors='replace', newline='') as f:
        return f.read()


def _strip_toolkit_block(existing):
    """Remove an unmarked, toolkit-authored sprint block from `existing` and return
    the cleaned text, or None if the block isn't clearly ours to remove. The old
    toolkit appended sprint.hsc at the end of the file behind a `;===` / `; SPRINT
    PROTOTYPE` banner, so the block runs from that banner to EOF."""
    lines = existing.splitlines()
    title = next((i for i, ln in enumerate(lines) if BANNER_TITLE in ln), None)
    if title is None:
        return None
    # Walk back over the contiguous run of comment lines that form the banner so the
    # leading `;===` divider goes too.
    start = title
    while start > 0 and lines[start - 1].lstrip().startswith(';'):
        start -= 1
    return '\n'.join(lines[:start]).rstrip('\r\n')


def install(global_scripts=None, sprint_hsc=None, quiet=False):
    """Ensure global_scripts.hsc contains exactly the current sprint.hsc, wrapped in
    sentinel markers. Returns True if the file was changed. Idempotent: a second call
    with an unchanged sprint.hsc rewrites nothing.

    An unmarked block written by an earlier toolkit version (recognised by its
    banner) is migrated in place automatically. A RuntimeError is raised only if an
    unmarked sprint block is found that ISN'T ours — a hand-written one whose extent
    we can't safely guess.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    if sprint_hsc is None:
        sprint_hsc = os.path.join(here, 'sprint.hsc')
    if global_scripts is None:
        import paths
        global_scripts = paths.GLOBAL_SCRIPTS

    body = _read(sprint_hsc).rstrip('\r\n')
    block = '%s\n%s\n%s\n' % (BEGIN, body, END)

    existing = _read(global_scripts) if os.path.exists(global_scripts) else ''

    if BEGIN in existing and END in existing:
        # Replace the managed block in place, keeping the same framing an append
        # would produce (two blank lines before, none injected when it's at the top
        # or bottom) so a follow-up install with unchanged sprint.hsc is a no-op.
        pre, rest = existing.split(BEGIN, 1)
        _, post = rest.split(END, 1)
        pre = pre.rstrip('\r\n')
        post = post.lstrip('\r\n')
        new = (pre + '\n\n' if pre else '') + block + post
    else:
        head = existing.rstrip('\r\n')
        if SIGNATURE in existing:
            cleaned = _strip_toolkit_block(existing)
            if cleaned is None:
                raise RuntimeError(
                    'global_scripts.hsc already contains an unmarked sprint block '
                    "that the toolkit didn't write (no recognisable banner). Remove "
                    'that block by hand once, then re-run — after that installs are '
                    'automatic.')
            if not quiet:
                print('migrating an older unmarked sprint block into managed markers')
            head = cleaned
        # Same two-blank-line framing the replace branch produces, so a follow-up
        # install with an unchanged sprint.hsc is a true no-op.
        new = (head + '\n\n' if head else '') + block

    if new == existing:
        if not quiet:
            print('sprint.hsc already current in global_scripts.hsc')
        return False

    if os.path.exists(global_scripts):
        bak = global_scripts + '.presprint'
        if not os.path.exists(bak):
            shutil.copy2(global_scripts, bak)
            if not quiet:
                print('backed up global_scripts.hsc ->', os.path.basename(bak))
    else:
        os.makedirs(os.path.dirname(global_scripts), exist_ok=True)

    with open(global_scripts, 'w', encoding='utf-8', newline='') as f:
        f.write(new)
    if not quiet:
        print('installed current sprint.hsc into', os.path.basename(global_scripts))
    return True


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        install()
    except RuntimeError as e:
        print('ERROR:', e)
        sys.exit(1)
