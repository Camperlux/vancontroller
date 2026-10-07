"""Write VanController's net classes and pattern assignments into the .kicad_pro."""
import copy
import json
import os

PRO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VanController.kicad_pro")

CLASSES = {
    # name: (track, clearance, via dia, via drill)
    "Default": (0.2, 0.15, 0.6, 0.3),
    "Power": (0.5, 0.15, 0.8, 0.4),
    "Load": (1.0, 0.2, 1.0, 0.5),
}
PATTERNS = [
    ("Power", "+3V3"), ("Power", "+5V"), ("Power", "VBUS"), ("Power", "GND"), ("Power", "/Power/SW5"),
    ("Power", "/Power/BOOT5"),
    ("Load", "+12V"), ("Load", "/Power/VBAT"), ("Load", "/Power/VIN_F"),
    ("Load", "/Relays/*/OUT_F"), ("Load", "/Relays/*/NO"), ("Load", "/Relays/*/NC_OUT"),
    ("Load", "/Dimmers/*/OUT_F"), ("Load", "/Dimmers/*/LOAD_N"),
]

with open(PRO, encoding="utf-8") as f:
    pro = json.load(f)
ns = pro["net_settings"]
base = next(c for c in ns["classes"] if c["name"] == "Default")
classes = []
for name, (tw, cl, vd, vdr) in CLASSES.items():
    c = copy.deepcopy(base)
    c.update(name=name, track_width=tw, clearance=cl, via_diameter=vd, via_drill=vdr)
    if name != "Default":
        c["priority"] = len(classes)
    classes.append(c)
ns["classes"] = classes
ns["netclass_patterns"] = [{"netclass": c, "pattern": p} for c, p in PATTERNS]
rules = pro["board"]["design_settings"]["rules"]
rules.update(min_track_width=0.15, min_clearance=0.15, min_via_diameter=0.6, min_through_hole_diameter=0.2,
             min_hole_clearance=0.15, min_resolved_spokes=1,
             min_copper_edge_clearance=0.5)
with open(PRO, "w", encoding="utf-8") as f:
    json.dump(pro, f, indent=2)
print("net classes:", ", ".join(CLASSES))
