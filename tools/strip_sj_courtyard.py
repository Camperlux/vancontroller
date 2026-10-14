"""Remove the courtyard outline from the SJ (dry-contact solder jumper) footprints in the board file.

A solder jumper is bare copper with no component body, so its courtyard only triggers false overlap errors.
"""
import os
import re

PCB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VanController.kicad_pcb")


def block_end(s, i):
    depth = 0
    in_str = False
    while True:
        c = s[i]
        if in_str:
            if c == "\\":
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1


s = open(PCB, encoding="utf-8").read()
out, pos, removed = [], 0, 0
for m in re.finditer(r'\(footprint "Jumper:SolderJumper-2_P1\.3mm_Bridged', s):
    a = m.start()
    if a < pos:
        continue
    b = block_end(s, a)
    fp = s[a:b]
    # drop every graphic child block that lives on a courtyard layer
    keep, j = [], 0
    for g in re.finditer(r'\n\t+\((fp_line|fp_rect|fp_poly|fp_circle|fp_arc)\b', fp):
        if g.start() < j:
            continue
        e = block_end(fp, g.start() + g.group(0).index("("))
        if '"F.CrtYd"' in fp[g.start():e] or '"B.CrtYd"' in fp[g.start():e]:
            keep.append(fp[j:g.start()])
            j = e
            removed += 1
    keep.append(fp[j:])
    out.append(s[pos:a])
    out.append("".join(keep))
    pos = b
out.append(s[pos:])
open(PCB, "w", encoding="utf-8", newline="\n").write("".join(out))
print("courtyard items removed:", removed)
