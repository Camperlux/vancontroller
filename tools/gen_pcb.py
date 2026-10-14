"""Build VanController.kicad_pcb from the schematic netlist: footprints, nets, outline, placement, silkscreen.

Run with KiCad's Python:  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" tools\\gen_pcb.py
Requires the netlist:     kicad-cli sch export netlist --format kicadsexpr -o build\\vc.net VanController.kicad_sch
Running this OVERWRITES VanController.kicad_pcb (placement, tracks and zones are lost).
"""
import os
import re
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(__file__))
import kilib as k  # noqa: E402

PRJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPROOT = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"
NETFILE = os.path.join(PRJ, "build", "vc.net")
PCBFILE = os.path.join(PRJ, "VanController.kicad_pcb")

W, H = 230.0, 135.0          # board size (mm)
OX, OY = 40.0, 40.0          # board origin on the page
MM = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))


# --------------------------------------------------------------------------- netlist
def read_netlist():
    with open(NETFILE, encoding="utf-8") as f:
        tree = k.parse(f.read())
    comps = {}
    for c in k.find(k.first(tree, "components"), "comp"):
        sp = k.first(c, "sheetpath")
        comps[k.first(c, "ref")[1]] = {
            "value": k.first(c, "value")[1],
            "fp": k.first(c, "footprint")[1] if k.first(c, "footprint") else "",
            "sheet": k.first(sp, "names")[1],
            "path": k.first(sp, "tstamps")[1] + k.first(c, "tstamps")[1],
            "props": [(k.first(p, "name")[1], k.first(p, "value")[1] if k.first(p, "value") else "")
                      for p in k.find(c, "property")],
            "fields": [(k.first(fl, "name")[1], fl[2] if len(fl) > 2 else "")
                       for fl in k.find(k.first(c, "fields") or [], "field")],
        }
    nets = {}
    for n in k.find(k.first(tree, "nets"), "net"):
        name = k.first(n, "name")[1]
        nets[name] = [(k.first(nd, "ref")[1], k.first(nd, "pin")[1]) for nd in k.find(n, "node")]
    return comps, nets


# --------------------------------------------------------------------------- board helpers
board = pcbnew.NewBoard(PCBFILE)
board.SetCopperLayerCount(4)
board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)  # planes only: keeps the autorouter off the inner layers
board.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)
FPS = {}
CHANNELS = []
RELAY_X0 = 16.5
DIM_PITCH = 15.0
RELAY_PITCH = 21.0
DIM_X0 = 140.0
GAP = 1.2


def load_fp(ref, info):
    lib, name = info["fp"].split(":")
    fp = pcbnew.FootprintLoad(os.path.join(FPROOT, lib + ".pretty"), name)
    if fp is None:
        raise SystemExit(f"footprint not found: {info['fp']}")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetReference(ref)
    fp.SetValue(info["value"])
    fp.SetPath(pcbnew.KIID_PATH(info["path"]))
    sheet = info["sheet"].strip("/").split("/")[-1] if info["sheet"] != "/" else ""
    fp.SetSheetname(sheet)
    fp.SetSheetfile(info.get("sheetfile", ""))
    for name, val in info["fields"] + info["props"]:
        if name in ("Reference", "Value", "Footprint", "Sheetname", "Sheetfile"):
            continue
        fp.SetField(name, val)
        f = fp.GetField(name)
        if f:
            f.SetVisible(False)
    if ref.startswith("J"):
        fp.SetExcludedFromBOM(False)
    board.Add(fp)
    FPS[ref] = fp
    return fp


def place(ref, x, y, rot=0.0):
    fp = FPS[ref]
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(P(x, y))


def courtyard_box(fp):
    fp.BuildCourtyardCaches()
    poly = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = poly.BBox() if poly.OutlineCount() else fp.GetBoundingBox(False)
    return (pcbnew.ToMM(bb.GetX()) - OX, pcbnew.ToMM(bb.GetY()) - OY,
            pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY)


def pack(refs, regions, gap=0.5, label=""):
    """Shelf-pack footprints (rotation 0) into regions (x0, y0, x1, y1), then spread the shelves and the parts
    within each shelf evenly over the region so the router gets uniform channels."""
    sizes = {}
    for ref in refs:
        place(ref, 0, 0)
        bx0, by0, bx1, by1 = courtyard_box(FPS[ref])
        sizes[ref] = (bx1 - bx0, by1 - by0, bx0, by0)
    todo = list(refs)
    for ri, (x0, y0, x1, y1) in enumerate(regions):
        shelves, row, roww, rowh, used_h = [], [], 0.0, 0.0, 0.0
        while todo:
            w, h = sizes[todo[0]][:2]
            if row and roww + gap + w > x1 - x0 + 1e-6:
                shelves.append((row, roww, rowh))
                used_h += rowh + gap
                row, roww, rowh = [], 0.0, 0.0
            if used_h + max(rowh, h) > y1 - y0 + 1e-6:
                break
            row.append(todo.pop(0))
            roww += (gap if len(row) > 1 else 0) + w
            rowh = max(rowh, h)
        if row:
            shelves.append((row, roww, rowh))
        if not shelves:
            continue
        total_h = sum(sh[2] for sh in shelves)
        vgap = (y1 - y0 - total_h) / max(len(shelves), 1)
        y = y0 + vgap / 2
        for row, roww, rowh in shelves:
            raw = sum(sizes[r][0] for r in row)
            hgap = (x1 - x0 - raw) / len(row)
            x = x0 + hgap / 2
            for r in row:
                w, h, bx0, by0 = sizes[r]
                place(r, x - bx0, y + (rowh - h) / 2 - by0)
                x += w + hgap
            y += rowh + vgap
    for r in todo:
        print(f"  WARNING {label}: {r} does not fit")


def silk(text, x, y, size=1.5, rot=0.0, layer=pcbnew.F_SilkS, bold=True):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(P(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(size * 0.15))
    t.SetBold(bold)
    t.SetTextAngleDegrees(rot)
    board.Add(t)


def edge_rect(x0, y0, x1, y1):
    sh = pcbnew.PCB_SHAPE(board)
    sh.SetShape(pcbnew.SHAPE_T_RECT)
    sh.SetStart(P(x0, y0))
    sh.SetEnd(P(x1, y1))
    sh.SetLayer(pcbnew.Edge_Cuts)
    sh.SetWidth(MM(0.1))
    board.Add(sh)


# --------------------------------------------------------------------------- build
def main():
    comps, nets = read_netlist()
    for ref, info in comps.items():
        if info["fp"]:
            load_fp(ref, info)
    netinfo = {}
    for name, nodes in nets.items():
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
        for ref, pin in nodes:
            if ref in FPS:
                for pad in FPS[ref].Pads():
                    if pad.GetNumber() == pin:
                        pad.SetNet(ni)
    print(f"{len(FPS)} footprints, {len(nets)} nets")

    by_sheet = {}
    for ref, info in comps.items():
        if ref in FPS:
            by_sheet.setdefault(info["sheet"], []).append(ref)

    def refkey(r):
        m = re.match(r"([A-Z#]+)(\d+)", r)
        return (m.group(1), int(m.group(2)))

    def take(sheet, pred):
        out = [r for r in by_sheet[sheet] if pred(r, comps[r])]
        for r in out:
            by_sheet[sheet].remove(r)
        return sorted(out, key=refkey)

    def one(sheet, pred):
        r = take(sheet, pred)
        assert len(r) == 1, (sheet, r)
        return r[0]

    edge_rect(0, 0, W, H)

    # ---- relay channels: columns along the top edge.
    # Terminal (rot 180): pin1 NO at cx+5.08, pin2 COM at cx, pin3 NC at cx-5.08, all at y=11.5.
    # Relay (rot 180) NO/NC sit straight below their terminal pins; fuse below the relay feeds COM.
    for i in range(6):
        sh = f"/Relays/Relay{i + 1}/"
        cx = RELAY_X0 + RELAY_PITCH * i
        j = one(sh, lambda r, c: r.startswith("J"))
        f = one(sh, lambda r, c: r.startswith("F"))
        kk = one(sh, lambda r, c: r.startswith("K"))
        place(j, cx + 5.08, 11.5, 180)
        place(kk, cx, 48.0, 180)
        place(f, cx - 1.7, 66.0, 90)
        pack(sorted(by_sheet[sh], key=refkey), [(cx - 10.3, 69.6, cx + 10.3, 79.2), (cx + 4.2, 52.5, cx + 10.3, 69.0)], gap=0.4, label=sh)
        silk(f"RELAY {i + 1}", cx, 17.0, 1.3)
        silk("NC  COM  NO", cx, 19.2, 1.0, bold=False)
        CHANNELS.append(("relay", i, cx))

    # ---- dimmer channels: columns along the top edge, right of the relays.
    # Terminal (rot 180): pin1 LOAD+ at cx+2.54, pin2 LOAD- at cx-2.54. Fuse below LOAD+, MOSFET below LOAD-.
    for j_ in range(6):
        sh = f"/Dimmers/Dimmer{j_ + 1}/"
        cx = DIM_X0 + DIM_PITCH * j_
        j = one(sh, lambda r, c: r.startswith("J"))
        f = one(sh, lambda r, c: r.startswith("F"))
        q = one(sh, lambda r, c: r.startswith("Q"))
        d = one(sh, lambda r, c: c["value"] == "SS54")
        place(j, cx + 2.54, 11.5, 180)
        place(f, cx + 0.84, 38.0, 90)
        place(q, cx - 3.6, 47.0, 0)
        place(d, cx + 3.5, 50.0, 90)
        pack(sorted(by_sheet[sh], key=refkey), [(cx - 7.3, 56.0, cx + 7.3, 68.0)], gap=1.0, label=sh)
        silk(f"DIM {j_ + 1}", cx, 17.0, 1.3)
        silk("-    +", cx, 19.2, 1.0, bold=False)
        CHANNELS.append(("dimmer", j_, cx))

    # ---- mounting holes
    holes = take("/Power/", lambda r, c: r.startswith("H"))
    for h, (x, y) in zip(holes, [(4.5, 20.0), (W - 4.5, 20.0), (4.5, 130.5), (166.0, 130.5)]):
        place(h, x, y)

    # ---- power: input studs on the left edge, then fuse, protection and buck
    sh = "/Power/"
    j_in = take(sh, lambda r, c: c["value"].startswith("+12V IN"))[0]
    j_gnd = take(sh, lambda r, c: c["value"].startswith("GND IN"))[0]
    place(j_in, 8.0, 92.0)
    place(j_gnd, 8.0, 110.0)
    silk("+12V", 8.0, 99.0, 1.5)
    silk("GND", 8.0, 117.0, 1.5)
    f1 = one(sh, lambda r, c: c["value"] == "30A ATO")
    place(f1, 17.0, 82.0, 0)
    d_tvs = one(sh, lambda r, c: c["value"] == "SMDJ26CA")
    qs = take(sh, lambda r, c: c["value"] == "CSD18540Q5B")
    place(d_tvs, 26.0, 93.0, 270)
    place(qs[0], 41.0, 83.0, 0)
    place(qs[1], 41.0, 90.0, 0)
    u_rp = one(sh, lambda r, c: c["value"].startswith("LM74700"))
    place(u_rp, 44.0, 97.5, 0)
    pack(sorted(by_sheet[sh], key=lambda r: (-courtyard_area(r), refkey(r))),
         [(50.5, 81.0, 70.0, 100.0), (31.0, 100.5, 70.0, 134.0), (14.0, 99.0, 31.0, 134.0)], gap=GAP, label=sh)

    # ---- comms: terminals on the bottom edge
    sh = "/Comms/"
    terms = take(sh, lambda r, c: r.startswith("J") and c["value"] in ("CANH / CANL / GND", "A / B / GND"))
    for t in terms:
        x0 = 78.0 if comps[t]["value"].startswith("CAN") else 98.0
        place(t, x0, 124.0, 0)
        silk("CANH CANL GND" if x0 < 90 else "A    B    GND", x0 + 5.08, 119.2, 1.0, bold=False)
    pack(sorted(by_sheet[sh], key=lambda r: (-courtyard_area(r), refkey(r))), [(73.0, 81.0, 113.0, 118.0)],
         gap=GAP, label=sh)

    # ---- sensors: water terminals on the bottom edge, GPS and front ends above
    sh = "/Sensors/"
    wts = take(sh, lambda r, c: c["value"].startswith("WATER"))
    for n, t in enumerate(sorted(wts, key=refkey)):
        x0 = 122.0 + 15.0 * n
        place(t, x0, 124.0, 0)
        silk(f"W{n + 1} SIG GND", x0 + 2.54, 119.2, 1.0, bold=False)
    pack(sorted(by_sheet[sh], key=lambda r: (-courtyard_area(r), refkey(r))), [(116.0, 81.0, 163.0, 118.0)],
         gap=GAP, label=sh)

    # ---- MCU: module bottom-right, antenna at the right edge
    sh = "/MCU/"
    esp = one(sh, lambda r, c: c["value"].startswith("ESP32"))
    usb = one(sh, lambda r, c: c["value"] == "USB-C")
    place(esp, W - 12.75, 110.0, 270)
    place(usb, 188.0, H - 4.0, 0)
    pack(sorted(by_sheet[sh], key=lambda r: (-courtyard_area(r), refkey(r))),
         [(170.0, 81.0, 222.5, 99.5), (170.0, 99.5, 203.0, 125.9)], gap=GAP, label=sh)

    left = {s: v for s, v in by_sheet.items() if v}
    print("unplaced:", left or "none")

    # ---- silkscreen title
    silk("VanController rev 0.3a", 209.0, 131.0, 1.5)

    copper()
    pcbnew.SaveBoard(PCBFILE, board)
    print("saved", PCBFILE)


def netcode(name):
    return board.FindNet(name).GetNetCode()


def track(net, pts, width, layers=(pcbnew.F_Cu, pcbnew.B_Cu)):
    for layer in layers:
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(P(x1, y1))
            t.SetEnd(P(x2, y2))
            t.SetWidth(MM(width))
            t.SetLayer(layer)
            t.SetNetCode(netcode(net))
            t.SetLocked(True)
            board.Add(t)


def via(net, x, y, d=0.8, drill=0.4):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(P(x, y))
    v.SetWidth(MM(d))
    v.SetDrill(MM(drill))
    v.SetNetCode(netcode(net))
    v.SetLocked(True)
    board.Add(v)


def zone(net, layer, pts, priority=0, full=False, clearance=0.4, name=""):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    if net:
        z.SetNetCode(netcode(net))
    ol = z.Outline()
    ol.NewOutline()
    for x, y in pts:
        ol.Append(MM(OX + x), MM(OY + y))
    z.SetAssignedPriority(priority)
    z.SetLocalClearance(MM(clearance))
    z.SetMinThickness(MM(0.25))
    if full:
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    if name:
        z.SetZoneName(name)
    board.Add(z)
    return z


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def copper():
    """Pre-routed high-current copper (locked) and planes. Freerouting routes everything else."""
    F, B = pcbnew.F_Cu, pcbnew.B_Cu
    for kind, i, c in CHANNELS:
        if kind == "relay":
            cx, n = c, f"/Relays/Relay{i + 1}/"
            track(n + "OUT_F", [(cx, 11.5), (cx, 48.0)], 2.5)
            track(n + "OUT_F", [(cx, 48.0), (cx - 1.7, 56.08)], 2.5)
            track(n + "OUT_F", [(cx, 48.0), (cx + 1.7, 56.08)], 2.5)
            track(n + "NO", [(cx + 6.0, 33.8), (cx + 5.08, 32.88), (cx + 5.08, 11.5)], 2.5)
            track(n + "NC_OUT", [(cx - 6.0, 33.8), (cx - 5.08, 32.88), (cx - 5.08, 11.5)], 2.5)
        else:
            cx, n = c, f"/Dimmers/Dimmer{i + 1}/"
            track(n + "OUT_F", [(cx + 2.54, 11.5), (cx + 2.54, 28.08)], 2.5)
            track(n + "OUT_F", [(cx + 0.84, 28.08), (cx + 4.24, 28.08)], 2.5)
            track(n + "LOAD_N", [(cx - 2.54, 11.5), (cx - 3.2, 14.0), (cx - 3.2, 47.0)], 2.0, layers=(F,))

    # 30 A input path: stud -> ATO fuse (VBAT), fuse -> TVS + MOSFET sources (VIN_F), drains -> +12V plane
    for layer in (F, B):
        zone("/Power/VBAT", layer, rect(3.0, 79.6, 22.2, 97.5), priority=10, full=True, name="VBAT")
    zone("/Power/VIN_F", F, [(24.6, 79.6), (37.2, 79.6), (37.2, 80.6), (38.75, 80.6), (38.75, 84.05), (37.2, 84.05),
                             (37.2, 87.6), (38.75, 87.6), (38.75, 91.05), (37.2, 91.05), (37.2, 92.3), (24.6, 92.3)],
         priority=10, full=True, name="VIN_F")
    zone("/Power/VIN_F", B, rect(24.6, 79.6, 37.2, 92.3), priority=10, full=True, name="VIN_F")
    for x in (31.6, 33.2, 34.8, 36.4):
        for y in (80.6, 82.2, 83.8, 85.4, 87.0, 88.6, 90.2, 91.5):
            via("/Power/VIN_F", x, y)
    for y0 in (80.0, 87.0):
        for layer in (F, B):
            zone("+12V", layer, rect(39.4, y0, 49.0, y0 + 5.9), priority=10, full=True, name="+12V_FET")
        for x in (45.3, 46.4, 47.5, 48.4):
            for k_ in range(5):
                via("+12V", x, y0 + 0.6 + k_ * 1.15)

    # inner planes: In1 = GND, In2 = +12V
    zone("GND", pcbnew.In1_Cu, rect(0.3, 0.3, W - 0.3, H - 0.3), priority=0, clearance=0.3, name="GND_PLANE")
    z12 = zone("+12V", pcbnew.In2_Cu, rect(0.3, 0.3, W - 0.3, H - 0.3), priority=0, full=True, clearance=0.4,
               name="+12V_PLANE")

    # no copper under the ESP32 antenna (module end is at the bottom edge)
    ka = pcbnew.ZONE(board)
    ka.SetIsRuleArea(True)
    ka.SetLayerSet(pcbnew.LSET.AllCuMask())
    ka.SetDoNotAllowTracks(True)
    ka.SetDoNotAllowVias(True)
    ka.SetDoNotAllowZoneFills(True)
    ka.SetDoNotAllowPads(False)
    ka.SetDoNotAllowFootprints(False)
    ol = ka.Outline()
    ol.NewOutline()
    for x, y in rect(W - 6.8, 100.0, W, 120.0):
        ol.Append(MM(OX + x), MM(OY + y))
    ka.SetZoneName("ANTENNA_KEEPOUT")
    board.Add(ka)

    fanout()


def fanout(nets=("GND", "+12V"), via_d=0.6, drill=0.3, clearance=0.25):
    """Give every SMD pad on a plane net a short stub and a via, so the autorouter only routes signals.
    Pads already covered by a copper zone of their own net (e.g. the input MOSFET drains) are skipped."""
    import math
    obstacles = []  # (x, y, half_w, half_h, netname) in board mm (axis-aligned pad boxes)
    for fp in board.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            obstacles.append((pcbnew.ToMM(bb.GetCenter().x) - OX, pcbnew.ToMM(bb.GetCenter().y) - OY,
                              pcbnew.ToMM(bb.GetWidth()) / 2, pcbnew.ToMM(bb.GetHeight()) / 2, p.GetNetname()))
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_TRACE_T:
            s, e = t.GetStart(), t.GetEnd()
            n = max(2, int(t.GetLength() / MM(0.5)))
            hw = pcbnew.ToMM(t.GetWidth()) / 2
            for k_ in range(n + 1):
                x = pcbnew.ToMM(s.x + (e.x - s.x) * k_ / n) - OX
                y = pcbnew.ToMM(s.y + (e.y - s.y) * k_ / n) - OY
                obstacles.append((x, y, hw, hw, t.GetNetname()))
        else:
            obstacles.append((pcbnew.ToMM(t.GetPosition().x) - OX, pcbnew.ToMM(t.GetPosition().y) - OY,
                              pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2, pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2, t.GetNetname()))
    grid = {}
    for o in obstacles:
        x, y, hw, hh, _ = o
        for gx in range(int((x - hw) // 2) - 1, int((x + hw) // 2) + 2):
            for gy in range(int((y - hh) // 2) - 1, int((y + hh) // 2) + 2):
                grid.setdefault((gx, gy), []).append(o)

    def near(x, y):
        return grid.get((int(x // 2), int(y // 2)), [])

    allvias = [(pcbnew.ToMM(t.GetPosition().x) - OX, pcbnew.ToMM(t.GetPosition().y) - OY)
               for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    zones = [z for z in board.Zones() if not z.GetIsRuleArea()]
    keepouts = [z for z in board.Zones() if z.GetIsRuleArea()]
    keepouts += [z for fp in board.GetFootprints() for z in fp.Zones() if z.GetIsRuleArea()]
    placed = skipped = 0
    for fp in board.GetFootprints():
        fc = fp.GetPosition()
        fcx, fcy = pcbnew.ToMM(fc.x) - OX, pcbnew.ToMM(fc.y) - OY
        for p in fp.Pads():
            net = p.GetNetname()
            if net not in nets or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            pos = p.GetPosition()
            if any(z.GetNetname() == net and z.GetLayer() == pcbnew.F_Cu and z.Outline().Contains(pos) for z in zones):
                continue
            px, py = pcbnew.ToMM(pos.x) - OX, pcbnew.ToMM(pos.y) - OY
            bb = p.GetBoundingBox()
            phw, phh = pcbnew.ToMM(bb.GetWidth()) / 2, pcbnew.ToMM(bb.GetHeight()) / 2
            stub_w = min(0.4, 2 * min(phw, phh) * 0.8)
            base = math.atan2(py - fcy, px - fcx) if (px, py) != (fcx, fcy) else 0.0
            done = False
            for dist in (0.9, 1.3, 1.8, 2.4):
                for step in (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6, 7, -7, 8):
                    ang = base + step * math.pi / 8
                    vx = px + math.cos(ang) * (max(phw, phh) * abs(math.cos(ang)) + dist)
                    vy = py + math.sin(ang) * (max(phw, phh) * abs(math.sin(ang)) + dist)
                    if not (1.0 < vx < W - 1.0 and 1.0 < vy < H - 1.0):
                        continue
                    vp = P(vx, vy)
                    m = via_d / 2 + 0.3
                    if any(z.Outline().Contains(P(vx + ex, vy + ey)) for z in keepouts
                           for ex, ey in ((0, 0), (m, 0), (-m, 0), (0, m), (0, -m), (m, m), (m, -m), (-m, m), (-m, -m))):
                        continue
                    if vx > W - 9.0 and 97.0 < vy < 123.0:  # stay clear of the ESP32 antenna end
                        continue
                    # keep vias apart (any net): hole-to-hole and annular rings
                    if any(math.hypot(vx - ax, vy - ay) < via_d + 0.4 for ax, ay in allvias):
                        continue
                    ok = True
                    # sample the stub from the pad edge to the via; every point must clear other-net items
                    samples = [(px + (vx - px) * f, py + (vy - py) * f) for f in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)]
                    for ox_, oy_, hw, hh, on in near(vx, vy):
                        if on == net:
                            continue
                        dx = max(abs(vx - ox_) - hw, 0)
                        dy = max(abs(vy - oy_) - hh, 0)
                        if math.hypot(dx, dy) < via_d / 2 + clearance:
                            ok = False
                            break
                    if ok:
                        for sx, sy in samples:
                            for ox_, oy_, hw, hh, on in near(sx, sy):
                                if on == net:
                                    continue
                                dx = max(abs(sx - ox_) - hw, 0)
                                dy = max(abs(sy - oy_) - hh, 0)
                                if math.hypot(dx, dy) < stub_w / 2 + clearance:
                                    ok = False
                                    break
                            if not ok:
                                break
                    if ok:
                        t = pcbnew.PCB_TRACK(board)
                        t.SetStart(pos)
                        t.SetEnd(vp)
                        t.SetWidth(MM(stub_w))
                        t.SetLayer(pcbnew.F_Cu)
                        t.SetNetCode(p.GetNetCode())
                        t.SetLocked(True)
                        board.Add(t)
                        v = pcbnew.PCB_VIA(board)
                        v.SetPosition(vp)
                        v.SetWidth(MM(via_d))
                        v.SetDrill(MM(drill))
                        v.SetNetCode(p.GetNetCode())
                        v.SetLocked(True)
                        board.Add(v)
                        allvias.append((vx, vy))
                        o = (vx, vy, via_d / 2, via_d / 2, net)
                        for gx in range(int(vx // 2) - 1, int(vx // 2) + 2):
                            for gy in range(int(vy // 2) - 1, int(vy // 2) + 2):
                                grid.setdefault((gx, gy), []).append(o)
                        placed += 1
                        done = True
                        break
                if done:
                    break
            if not done:
                skipped += 1
    print(f"fanout: {placed} vias placed, {skipped} pads left to the router")


def courtyard_area(ref):
    fp = FPS[ref]
    old_pos, old_rot = fp.GetPosition(), fp.GetOrientationDegrees()
    x0, y0, x1, y1 = courtyard_box(fp)
    return (x1 - x0) * (y1 - y0)


if __name__ == "__main__":
    main()
