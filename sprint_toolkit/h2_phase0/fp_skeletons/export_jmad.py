"""Export H2 FP animation graphs to XML (tool export-tag-to-xml) and list their skeleton nodes."""
import os, re, subprocess, sys
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'
OUT = r'C:\Users\kron1\AppData\Local\Temp'
jobs = sys.argv[1:]  # relative tag paths under tags\
for rel in jobs:
    tag = os.path.join(H2EK, 'tags', rel)
    out = os.path.join(OUT, 'h2fp_' + rel.replace('\\', '_').replace('/', '_') + '.xml')
    if not os.path.exists(out) or not os.path.getsize(out):
        subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-tag-to-xml', tag, out],
                       cwd=H2EK, capture_output=True)
    x = open(out, encoding='utf-8', errors='replace').read() if os.path.exists(out) else ''
    print('=== %s (%d bytes)' % (rel, len(x)))
    i = x.find('<block name="skeleton nodes"')
    if i < 0:
        print('  no skeleton nodes block'); continue
    j = x.find('<block name="', i + 10)
    seg = x[i:j]
    els = re.split(r'<element index="\d+">', seg)[1:]
    print('  %d nodes' % len(els))
    for k, e in enumerate(els):
        nm = re.search(r'name="name"[^>]*>([^<]*)<', e).group(1)
        par = re.search(r'type="parent node index" index="(-?\d+)"', e).group(1)
        fl = re.search(r'name="model flags"[^>]*>(.*?)</field>', e, re.S).group(1).split()
        print('   %2d %-26s parent=%-3s flags=%s' % (k, nm, par, ' '.join(fl[1:])))
    anims = re.findall(r'<block name="animations".*?</block>', x, re.S)
