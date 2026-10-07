"""Import the Freerouting session, add outer-layer GND pours, fill all zones and save.

Run with KiCad's Python after Freerouting has written build\\vc.ses.
"""
import os
import sys

import pcbnew

PRJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
PCB = args[0] if args else os.path.join(PRJ, "VanController.kicad_pcb")
SES = args[1] if len(args) > 1 else os.path.join(PRJ, "build", "vc.ses")
MM = pcbnew.FromMM

board = pcbnew.LoadBoard(PCB)
if "--no-import" not in sys.argv:
    if not pcbnew.ImportSpecctraSES(board, SES):
        raise SystemExit("SES import failed")

# outer-layer GND pours (lowest priority, below the power zones)
outline = pcbnew.SHAPE_POLY_SET()
board.GetBoardPolygonOutlines(outline, True)
bb = outline.BBox()
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    if any(board.GetArea(i).GetZoneName() == "GND_POUR" and board.GetArea(i).GetLayer() == layer
           for i in range(board.GetAreaCount())):
        continue
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNetCode(board.FindNet("GND").GetNetCode())
    ol = z.Outline()
    ol.NewOutline()
    inset = MM(0.3)
    for x, y in ((bb.GetX() + inset, bb.GetY() + inset), (bb.GetRight() - inset, bb.GetY() + inset),
                 (bb.GetRight() - inset, bb.GetBottom() - inset), (bb.GetX() + inset, bb.GetBottom() - inset)):
        ol.Append(x, y)
    z.SetAssignedPriority(1)
    z.SetLocalClearance(MM(0.3))
    z.SetMinThickness(MM(0.25))
    z.SetZoneName("GND_POUR")
    board.Add(z)

# silkscreen: keep reference designators on silk only for parts a person handles or identifies on the board;
# small passives/transistors carry theirs on F.Fab (assembly drawing) to avoid unreadable overlaps
SMALL = ("R_0603", "C_0603", "C_0805", "LED_0603", "L_0603", "SOT-23", "SOD-123", "SOT-23-6")
for fp in board.GetFootprints():
    name = fp.GetFPID().GetLibItemName().wx_str()
    ref = fp.Reference()
    if name.startswith(SMALL) and name != "SOT-223-3_TabPin2":
        ref.SetLayer(pcbnew.F_Fab)
    else:
        ref.SetTextSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0)))
        ref.SetTextThickness(MM(0.15))

# drop zero-length leftovers from the session import
for t in list(board.GetTracks()):
    if t.Type() == pcbnew.PCB_TRACE_T and t.GetLength() < MM(0.05):
        board.Delete(t)

filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
tracks = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T]
vias = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
print(f"saved: {len(tracks)} track segments, {len(vias)} vias, {board.GetAreaCount()} zones")
