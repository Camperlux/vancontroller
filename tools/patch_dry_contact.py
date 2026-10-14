"""Rev 0.3a: add the dry-contact solder jumpers SJ1-SJ6 to the routed board.

For each relay channel the fuse-sense resistor (33k) is moved from OUT_F (fused COM) onto a new net SENSE_TAP,
reached through a bridged solder jumper whose pad 1 sits on the fat COM track between the relay and the fuse.
Cutting the jumper and removing the fuse leaves COM/NO/NC connected only to the relay contacts.

Usage (KiCad Python, after exporting build/vc.net from the updated schematic):
    python.exe tools/patch_dry_contact.py
    python tools/strip_sj_courtyard.py   (copper-only jumpers: drop their courtyards)
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(__file__))
import kilib as k  # noqa: E402

PRJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(PRJ, "VanController.kicad_pcb")
NET = os.path.join(PRJ, "build", "vc.net")
FPLIB = r"C:\Program Files\KiCad\10.0\share\kicad\footprints\Jumper.pretty"
FPNAME = "SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm"
OX, OY = 40.0, 40.0
MM = pcbnew.FromMM
RELAY_X0, PITCH = 16.5, 21.0


def P(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))


def mm(v, o):
    return round(pcbnew.ToMM(v) - o, 3)


tree = k.parse(open(NET, encoding="utf-8").read())
comps = {}
for c in k.find(k.first(tree, "components"), "comp"):
    sp = k.first(c, "sheetpath")
    comps[k.first(c, "ref")[1]] = dict(value=k.first(c, "value")[1], sheet=k.first(sp, "names")[1],
                                        path=k.first(sp, "tstamps")[1] + k.first(c, "tstamps")[1])

board = pcbnew.LoadBoard(PCB)


def add_track(net, pts, width, layer):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(P(x1, y1))
        t.SetEnd(P(x2, y2))
        t.SetWidth(MM(width))
        t.SetLayer(layer)
        t.SetNet(net)
        t.SetLocked(True)
        board.Add(t)


def add_via(net, x, y):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(P(x, y))
    v.SetWidth(pcbnew.F_Cu, MM(0.6))
    v.SetDrill(MM(0.3))
    v.SetNet(net)
    v.SetLocked(True)
    board.Add(v)


for i in range(6):
    sheet = f"/Relays/Relay{i + 1}/"
    cx = RELAY_X0 + PITCH * i
    sj = next(r for r, c in comps.items() if r.startswith("SJ") and c["sheet"] == sheet)
    if board.FindFootprintByReference(sj):
        print(f"{sj}: already on the board, skipped")
        continue
    rsense = next(fp for fp in board.GetFootprints()
                  if fp.GetSheetname() == f"Relay{i + 1}" and fp.GetValue() == "33k")
    out_f = board.FindNet(sheet + "OUT_F")

    # 1. keep the autorouted sense branch, except its first segment that leaves the fat COM track
    branch = [t for t in board.GetTracks() if t.GetNetname() == sheet + "OUT_F" and not t.IsLocked()]
    first = [t for t in branch if t.Type() == pcbnew.PCB_TRACE_T
             and min(mm(t.GetStart().y, OY), mm(t.GetEnd().y, OY)) < 53.0]
    assert len(first) == 1, (sheet, len(first))
    f0 = first[0]
    s0, e0 = f0.GetStart(), f0.GetEnd()
    qpt = s0 if pcbnew.ToMM(s0.y) > pcbnew.ToMM(e0.y) else e0
    qx, qy = mm(qpt.x, OX), mm(qpt.y, OY)
    board.Delete(f0)
    branch.remove(f0)
    removed = 1

    # 2. new net, resistor pad moved onto it
    tap = pcbnew.NETINFO_ITEM(board, sheet + "SENSE_TAP")
    board.Add(tap)
    rpad = next(p for p in rsense.Pads() if p.GetNetname() == sheet + "OUT_F")
    rpad.SetNet(tap)
    for t in branch:
        t.SetNet(tap)
    rx, ry = mm(rpad.GetPosition().x, OX), mm(rpad.GetPosition().y, OY)

    # 3. solder jumper: pad 1 overlaps the fat COM track just below the relay
    fp = pcbnew.FootprintLoad(FPLIB, FPNAME)
    fp.SetFPID(pcbnew.LIB_ID("Jumper", FPNAME))
    fp.SetReference(sj)
    fp.SetValue(comps[sj]["value"])
    fp.SetPath(pcbnew.KIID_PATH(comps[sj]["path"]))
    fp.SetSheetname(f"Relay{i + 1}")
    fp.SetSheetfile("relay_channel.kicad_sch")
    fp.SetPosition(P(cx + 2.8, 51.8))
    board.Add(fp)
    for p in fp.Pads():
        p.SetNet(out_f if p.GetNumber() == "1" else tap)
    fp.Reference().SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
    fp.Reference().SetTextThickness(MM(0.12))
    fp.Reference().SetPosition(P(cx + 6.2, 51.8))
    p2 = next(p for p in fp.Pads() if p.GetNumber() == "2")
    sx, sy = mm(p2.GetPosition().x, OX), mm(p2.GetPosition().y, OY)

    # 4. jumper pad 2 -> via -> start of the kept branch on B.Cu
    add_track(tap, [(sx, sy), (qx, 53.6)], 0.25, pcbnew.F_Cu)
    add_via(tap, qx, 53.6)
    add_track(tap, [(qx, 53.6), (qx, qy)], 0.25, pcbnew.B_Cu)
    print(f"{sj}: placed at ({cx + 2.8:.2f}, 51.80); kept {len(branch)} branch items, joined at ({qx}, {qy}); "
          f"{rsense.GetReference()} pad at ({rx}, {ry})")

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("saved")
