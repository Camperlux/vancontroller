"""Post-route cleanup: fix via drills, delete dangling track tails (found via a JSON DRC report), refill zones.

Usage (KiCad Python):  python.exe tools/fix_pcb.py <board.kicad_pcb>
"""
import json
import os
import subprocess
import sys
import tempfile

import pcbnew

CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
PCB = sys.argv[1]
MM = pcbnew.FromMM


def drc_items(kind):
    rpt = os.path.join(tempfile.gettempdir(), "vc_fix_drc.json")
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "-o", rpt, PCB], check=True, capture_output=True)
    with open(rpt, encoding="utf-8") as f:
        data = json.load(f)
    out = []
    for v in data.get("violations", []):
        if v.get("type") == kind:
            out.append(v)
    return out


board = pcbnew.LoadBoard(PCB)
fixed = 0
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        d, dr = t.GetWidth(pcbnew.F_Cu), t.GetDrillValue()
        if d - dr < MM(0.25):
            t.SetDrill(d - MM(0.3))
            fixed += 1
pcbnew.SaveBoard(PCB, board)
print(f"vias with a thin annular ring fixed: {fixed}")

removed = 0
for _ in range(6):
    dangling = drc_items("track_dangling")
    if not dangling:
        break
    uuids = {it["uuid"] for v in dangling for it in v.get("items", [])}
    board = pcbnew.LoadBoard(PCB)
    for t in list(board.GetTracks()):
        if t.m_Uuid.AsString() in uuids and t.Type() == pcbnew.PCB_TRACE_T and not t.IsLocked():
            board.Delete(t)
            removed += 1
    pcbnew.SaveBoard(PCB, board)
print(f"dangling track tails removed: {removed}")

board = pcbnew.LoadBoard(PCB)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("zones refilled")
