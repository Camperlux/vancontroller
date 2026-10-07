"""Hand fixes after autorouting.

1. Reverse-polarity MOSFET gate link: route Q1 gate -> Q2 gate through the free B.Cu corridor between the
   VIN_F and +12V copper areas, so no GATE_RP track cuts the VIN_F area on F.Cu.
2. Connect stranded plane-net SMD pads (listed below) to the inner plane with a short stub and a via.

Usage (KiCad Python):  python.exe tools/patch_pcb.py <board.kicad_pcb>
"""
import math
import sys

import pcbnew

PCB = sys.argv[1]
OX, OY = 40.0, 40.0
MM = pcbnew.FromMM
board = pcbnew.LoadBoard(PCB)


def P(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))


def mm(v, o):
    return pcbnew.ToMM(v) - o


def net(name):
    return board.FindNet(name)


def add_track(n, pts, width, layer):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(P(x1, y1))
        t.SetEnd(P(x2, y2))
        t.SetWidth(MM(width))
        t.SetLayer(layer)
        t.SetNet(n)
        t.SetLocked(True)
        board.Add(t)


def add_via(n, x, y, d=0.6, drill=0.3):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(P(x, y))
    v.SetWidth(MM(d))
    v.SetDrill(MM(drill))
    v.SetNet(n)
    v.SetLocked(True)
    board.Add(v)


# ---- 1. MOSFET gate link -----------------------------------------------------------------------------------
gate = net("/Power/GATE_RP")
q = {r: board.FindFootprintByReference(r) for r in ("Q1", "Q2")}
gpos = {}
for r, fp in q.items():
    for p in fp.Pads():
        if p.GetNetname() == "/Power/GATE_RP":
            gpos[r] = (mm(p.GetPosition().x, OX), mm(p.GetPosition().y, OY))
# remove router GATE_RP segments that run inside the VIN_F area (x < 38.75 between the two gates)
removed = 0
for t in list(board.GetTracks()):
    if t.Type() == pcbnew.PCB_TRACE_T and t.GetNetname() == "/Power/GATE_RP" and t.GetLayer() == pcbnew.F_Cu:
        xs = (mm(t.GetStart().x, OX), mm(t.GetEnd().x, OX))
        ys = (mm(t.GetStart().y, OY), mm(t.GetEnd().y, OY))
        if min(xs) < 37.9 and min(ys) > gpos["Q1"][1] - 0.5 and max(ys) < gpos["Q2"][1] + 0.5:
            board.Delete(t)
            removed += 1
g1x, g1y = gpos["Q1"]
g2x, g2y = gpos["Q2"]
via1 = (g1x + 0.3, g1y + 1.5)          # between the Q1 source finger and the Q2 source finger
via2 = (g2x + 0.77, g2y + 0.76)        # below the Q2 gate, outside the VIN_F area
add_track(gate, [(g1x, g1y), via1], 0.25, pcbnew.F_Cu)
add_via(gate, *via1)
add_track(gate, [via1, via2], 0.25, pcbnew.B_Cu)
add_via(gate, *via2)
add_track(gate, [(g2x, g2y), via2], 0.25, pcbnew.F_Cu)
print(f"gate link: removed {removed} router segments, added B.Cu link via {via1} -> {via2}")

# ---- 2. stranded plane pads -----------------------------------------------------------------------------------
STRANDED = [("U9", "10"), ("U9", "12"), ("U10", "3"), ("U11", "21"), ("U9", "5")]

obst = []  # (x, y, hw, hh, net, layers) ; layers: set of layer ids or None for all
for fp in board.GetFootprints():
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        ls = None if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else {pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu}
        obst.append((mm(bb.GetCenter().x, OX), mm(bb.GetCenter().y, OY), pcbnew.ToMM(bb.GetWidth()) / 2,
                     pcbnew.ToMM(bb.GetHeight()) / 2, p.GetNetname(), ls))
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_TRACE_T:
        s, e = t.GetStart(), t.GetEnd()
        n = max(2, int(t.GetLength() / MM(0.2)))
        hw = pcbnew.ToMM(t.GetWidth()) / 2
        for k in range(n + 1):
            obst.append((mm(s.x + (e.x - s.x) * k / n, OX), mm(s.y + (e.y - s.y) * k / n, OY), hw, hw,
                         t.GetNetname(), {t.GetLayer()}))
    else:
        r = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2
        obst.append((mm(t.GetPosition().x, OX), mm(t.GetPosition().y, OY), r, r, t.GetNetname(), None))


def clear(x, y, r, netname, layers, clearance=0.2):
    for ox, oy, hw, hh, on, ls in obst:
        if on == netname:
            continue
        if ls is not None and layers is not None and not (ls & layers):
            continue
        dx = max(abs(x - ox) - hw, 0)
        dy = max(abs(y - oy) - hh, 0)
        if math.hypot(dx, dy) < r + clearance:
            return False
    return True


for ref, num in STRANDED:
    fp = board.FindFootprintByReference(ref)
    pad = next(p for p in fp.Pads() if p.GetNumber() == num)
    n = pad.GetNet()
    px, py = mm(pad.GetPosition().x, OX), mm(pad.GetPosition().y, OY)
    fx, fy = mm(fp.GetPosition().x, OX), mm(fp.GetPosition().y, OY)
    base = math.atan2(py - fy, px - fx)
    done = False
    for dist in (0.8, 1.0, 1.2, 1.5, 1.8, 2.2, 2.6, 3.0):
        for step in range(-12, 13):
            ang = base + step * math.pi / 24
            vx, vy = px + math.cos(ang) * dist, py + math.sin(ang) * dist
            if not clear(vx, vy, 0.3, n.GetNetname(), None):
                continue
            ok = all(clear(px + (vx - px) * f, py + (vy - py) * f, 0.1, n.GetNetname(), {pcbnew.F_Cu})
                     for f in (0.25, 0.4, 0.55, 0.7, 0.85, 1.0))
            if ok:
                add_track(n, [(px, py), (vx, vy)], 0.2, pcbnew.F_Cu)
                add_via(n, vx, vy)
                obst.append((vx, vy, 0.3, 0.3, n.GetNetname(), None))
                print(f"{ref} pad {num}: via at ({vx:.2f}, {vy:.2f}), stub {dist:.1f} mm")
                done = True
                break
        if done:
            break
    if not done:
        print(f"{ref} pad {num}: NO free spot found")

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("saved")
