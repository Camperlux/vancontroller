"""Produce fabrication and assembly outputs in fab/ and documentation PDFs in docs/ using kicad-cli.

Usage:  python tools/make_fab.py
"""
import datetime
import glob
import os
import re
import subprocess
import zipfile

PRJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
SCH = os.path.join(PRJ, "VanController.kicad_sch")
PCB = os.path.join(PRJ, "VanController.kicad_pcb")
FAB = os.path.join(PRJ, "fab")
GERB = os.path.join(FAB, "gerbers")
DOCS = os.path.join(PRJ, "docs")
LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"


def run(*args):
    print(">", " ".join(args[:3]), "...")
    subprocess.run([CLI, *args], check=True)


os.makedirs(GERB, exist_ok=True)
os.makedirs(DOCS, exist_ok=True)
run("pcb", "export", "gerbers", "--layers", LAYERS, "--subtract-soldermask", "-o", GERB + os.sep, PCB)
run("pcb", "export", "drill", "--format", "excellon", "--generate-map", "--map-format", "pdf", "-o", GERB + os.sep, PCB)
run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "--use-drill-file-origin",
    "-o", os.path.join(FAB, "positions.csv"), PCB)
run("sch", "export", "bom", "--fields", "Reference,Value,Footprint,MPN,${QUANTITY}",
    "--labels", "Designators,Value,Footprint,MPN,Qty", "--group-by", "Value,Footprint,MPN",
    "--exclude-dnp", "-o", os.path.join(FAB, "bom.csv"), SCH)
run("pcb", "export", "step", "--subst-models", "-f", "-o", os.path.join(FAB, "VanController.step"), PCB)
run("sch", "export", "pdf", "-o", os.path.join(DOCS, "VanController_schematic.pdf"), SCH)
run("pcb", "export", "pdf", "--layers", "F.Cu,F.SilkS,F.Fab,Edge.Cuts", "--mode-single",
    "-o", os.path.join(DOCS, "VanController_assembly_top.pdf"), PCB)


# normalise creation timestamps to UTC (no local timezone in published files) and zip the Gerbers
def _utc(m):
    return datetime.datetime.fromisoformat(m.group(0)).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


for f in glob.glob(os.path.join(GERB, "*")):
    if f.endswith(".pdf"):
        continue
    b = open(f, "rb").read().decode("latin-1")
    b2 = re.sub(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d", _utc, b)
    if b2 != b:
        open(f, "wb").write(b2.encode("latin-1"))
with zipfile.ZipFile(os.path.join(FAB, "VanController_gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(glob.glob(os.path.join(GERB, "*"))):
        z.write(f, os.path.basename(f))
print("done")
