r"""Halo 4 port, step 8 (text): the port's OWN pickup messages, in H4EK.

The recipe of h3_port_messages.py (see halo-port-own-messages): no hijacking -- the port
gets its own lines, cloned from a donor's, and the weapon's five message ids point at them.

HALO 4, measured 2026-10-02:
  * the lines live in ui\strings\ingame (NOT a hud_messages list); the weapon names five
    ids (pickup / swap / picked up / switch-to / switch-to from ai). The Sentinel-based
    port carried the BEAM RIFLE's be_* set -- so it said "Beam Rifle".
  * a prompt line is text + an ICON MACRO on its own line:
        be_pickup = "Hold &button_action_weapon_primary to pick up Beam Rifle\r\n&beam_rifle"
    and unlike Halo 3, Halo 4's PROMPT lines NAME the weapon. A translated name cannot be
    swapped safely, so every other language gets the ENGLISH lines ("Focus Rifle" is a
    name; the H3 ports already fall back to English for named lines).
  * the icon: Halo 4 has no Focus Rifle / Sentinel Beam macro. Interim: the Beam Rifle's
    &beam_rifle (a Covenant sniper silhouette). A real glyph needs Halo 4's icon font,
    which is not the 0xC000-block format h3_font_repack.py writes.
  * THE CRLF TRAP (Halo 3): the extracted source is CRLF; it is read and written with
    newline='' so `tool` sees every line.
  * `tool strings <dir>` imports EVERY .txt in the folder, so only ingame.txt may sit
    there; stray extracts are moved aside first.

    python h4_port_messages.py            # dry run
    python h4_port_messages.py --write    # lines, all languages, import
then h4_make_port_weapon.py points the weapon at fr_* (MESSAGES there).
"""
import argparse
import glob
import io
import os
import re
import shutil
import subprocess

H4EK = r'F:\SteamLibrary\steamapps\common\H4EK'
B = '\\'
LIST = B.join(['ui', 'strings', 'ingame'])
SRC = os.path.join(H4EK, 'data', 'ui', 'strings', 'ingame.txt')
DONOR, PORT = 'be_', 'fr_'
DONOR_NAME, PORT_NAME = 'Beam Rifle', 'Focus Rifle'
DONOR_ICON, PORT_ICON = '&beam_rifle', '&beam_rifle'      # interim icon, see above
IDS = ('pickup', 'swap', 'picked_up', 'switch_to', 'swap_ai')


def run(verb, *args):
    r = subprocess.run([os.path.join(H4EK, 'tool.exe'), verb] + list(args), cwd=H4EK,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout + r.stderr


def read(path):
    return io.open(path, encoding='utf-16', newline='').read()


def entries(s, prefix):
    out = {}
    for m in re.finditer(r'^(%s[a-z_]+) = (.*?)\r?$' % re.escape(prefix), s, re.M):
        out[m.group(1)] = m.group(2)
    return out


def port_lines(english):
    src = entries(english, DONOR)
    out = []
    for k in IDS:
        v = src.get(DONOR + k)
        if v is None:
            raise SystemExit('the donor has no %s%s' % (DONOR, k))
        out.append('%s%s = %s' % (PORT, k, v.replace(DONOR_NAME, PORT_NAME)
                                           .replace(DONOR_ICON, PORT_ICON)))
    return out


def add_lines(path, lines, write):
    s = read(path)
    new = [l for l in lines if not re.search(r'^%s = ' % re.escape(l.split(' = ')[0]), s, re.M)]
    if new and write:
        body = s.rstrip('\r\n') + '\r\n' + '\r\n'.join(new) + '\r\n'
        if body.count('\n') != body.count('\r\n'):
            raise SystemExit('%s: mixed line endings' % path)
        io.open(path, 'w', encoding='utf-16', newline='').write(body)
    return new


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    if not os.path.exists(SRC):
        print(run('extract-unicode-strings', LIST).strip()[-200:])
    lines = port_lines(read(SRC))
    for l in lines:
        print('   ' + l[:110])
    folder = os.path.dirname(SRC)
    if a.write:
        aside = os.path.join(H4EK, 'temp', 'strings_aside')
        for f in glob.glob(os.path.join(folder, '*.txt')):
            if os.path.basename(f) != 'ingame.txt':
                os.makedirs(aside, exist_ok=True)
                shutil.move(f, os.path.join(aside, os.path.basename(f)))
                print('   moved stray %s aside' % os.path.basename(f))
        tag = os.path.join(H4EK, 'tags', LIST + '.multilingual_unicode_string_list')
        keep = tag + '.before_focus'
        if not os.path.exists(keep):
            shutil.copy2(tag, keep)
    print('english: +%d' % len(add_lines(SRC, lines, a.write)))
    langs = sorted(glob.glob(os.path.join(H4EK, 'data_*', 'ui', 'strings', 'ingame.txt')))
    for p in langs:
        n = add_lines(p, lines, a.write)
        print('   %-10s +%d (English lines)' % (p.split(os.sep)[-4], len(n)))
    if not a.write:
        print('(dry run -- pass --write)')
        return
    out = run('strings', B.join(['ui', 'strings']))
    out += run('strings-localized', B.join(['ui', 'strings']))
    for line in out.splitlines():
        if any(w in line for w in ('WARNING', 'ERROR', 'english', 'strings')):
            print('   tool: ' + line.strip()[:110])
    d = open(os.path.join(H4EK, 'tags', LIST + '.multilingual_unicode_string_list'), 'rb').read()
    print('ids in the tag: %s' % [PORT + k for k in IDS if (PORT + k).encode() in d])


if __name__ == '__main__':
    main()
