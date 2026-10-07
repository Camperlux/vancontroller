"""Fusion 360 script: two-part 3D-printable enclosure for the VanController PCB (rev 0.3, 230 x 135 mm).

Builds a Base (walls, floor, PCB standoffs, corner lid columns, connector windows, cable-gland holes,
mounting ears) and a Lid (plate + locating lip), imports the PCB STEP into place for a fit check, and
exports STL/STEP files for printing to VanController/enclosure/.

All dimensions below are in mm. World axes: X along the board's long side, Y towards the relay/dimmer
terminal edge, Z up. Board coordinates (KiCad, y down from the terminal edge) map to world as
X = BX0 + x, Y = BY1 - y.
"""
import os
import traceback

import adsk.core
import adsk.fusion

OUTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the enclosure/ folder; set explicitly if you run a copy from Fusion's Scripts folder
PCB_STEP = os.path.join(OUTDIR, "VanController_pcb.step")

# ---------------------------------------------------------------- parameters (mm)
BOARD_W, BOARD_D, BOARD_T = 230.0, 135.0, 1.6
GAP_X, GAP_Y = 8.0, 1.0          # cavity clearance around the board (X leaves room for the corner columns)
WALL, FLOOR = 2.5, 2.5
STANDOFF_H = 6.0                 # floor top to PCB underside
STANDOFF_D = 7.0
INSERT_D, INSERT_DEPTH = 4.0, 6.0   # M3 heat-set insert (e.g. M3 x 5.7)
CLEAR_ABOVE = 22.0               # PCB top to underside of lid plate (G5LE relay is 15.7 mm tall)
LID_T = 3.0
LIP_H, LIP_T, LIP_GAP = 2.0, 1.6, 0.3
COLUMN_D, COLUMN_INSERT_D = 7.0, 4.0
LID_SCREW_D, LID_CBORE_D, LID_CBORE_DEPTH = 3.4, 6.5, 1.8
TERM_WIN_ABOVE = 12.5            # terminal window height above the PCB top (MSTBA 2,5 header ~12 mm)
TERM_WIN_BELOW = 0.3
GLAND_D = 16.2                   # M16 cable gland
EAR_W, EAR_L, EAR_T, EAR_SLOT = 14.0, 11.0, 4.0, 5.2

CAV_W = BOARD_W + 2 * GAP_X
CAV_D = BOARD_D + 2 * GAP_Y
OUT_W = CAV_W + 2 * WALL
OUT_D = CAV_D + 2 * WALL
BX0 = GAP_X                      # board left edge in world X
BY1 = GAP_Y + BOARD_D            # board terminal edge in world Y
PCB_Z0 = FLOOR + STANDOFF_H      # board underside
PCB_Z1 = PCB_Z0 + BOARD_T        # board top
WALL_TOP = PCB_Z1 + CLEAR_ABOVE  # top of base walls = underside of lid plate

# board features (KiCad board coordinates, mm, from courtyards)
HOLES = [(4.5, 20.0), (225.5, 20.0), (4.5, 130.5), (166.0, 130.5)]
TOP_TERMINALS = [  # (x0, x1) of each relay/dimmer terminal on the y=0 edge
    (7.33, 25.67), (28.33, 46.67), (49.33, 67.67), (70.33, 88.66), (91.32, 109.66), (112.32, 130.66),
    (133.37, 146.62), (148.37, 161.62), (163.37, 176.62), (178.37, 191.62), (193.37, 206.62), (208.37, 221.62),
]
BOTTOM_TERMINALS = [(73.92, 92.25), (93.91, 112.25), (117.91, 131.18), (132.91, 146.18)]  # CAN, RS485, W1, W2
USB_X, USB_W, USB_H, USB_ZC = 188.0, 13.0, 7.5, 1.6       # window sized for a moulded USB-C plug
SMA_X, SMA_Z, SMA_D = 157.0, 12.0, 6.6                     # GPS antenna SMA bulkhead (front wall)
GLAND_Y_BOARD = [78.0, 118.0]                # left wall, near the +12V / GND studs
GLAND_Z = 12.0                                             # above PCB top
EAR_Y = [25.0, OUT_D - 25.0]

app = adsk.core.Application.get()
ui = app.userInterface
tbm = adsk.fusion.TemporaryBRepManager.get()
CM = 0.1


def P(x, y, z):
    return adsk.core.Point3D.create(x * CM, y * CM, z * CM)


def box(x0, y0, z0, x1, y1, z1):
    c = P((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    obb = adsk.core.OrientedBoundingBox3D.create(c, adsk.core.Vector3D.create(1, 0, 0),
                                                 adsk.core.Vector3D.create(0, 1, 0),
                                                 abs(x1 - x0) * CM, abs(y1 - y0) * CM, abs(z1 - z0) * CM)
    return tbm.createBox(obb)


def cyl(a, b, d):
    return tbm.createCylinderOrCone(P(*a), d / 2 * CM, P(*b), d / 2 * CM)


def union(t, *tools):
    for x in tools:
        tbm.booleanOperation(t, x, adsk.fusion.BooleanTypes.UnionBooleanType)
    return t


def cut(t, *tools):
    for x in tools:
        tbm.booleanOperation(t, x, adsk.fusion.BooleanTypes.DifferenceBooleanType)
    return t


def wx(x):
    return BX0 + x


def wy(y):
    return BY1 - y


def column_centres():
    r = COLUMN_D / 2
    return [(WALL + r, WALL + r), (OUT_W - WALL - r, WALL + r),
            (WALL + r, OUT_D - WALL - r), (OUT_W - WALL - r, OUT_D - WALL - r)]


def build_base():
    W0 = WALL  # cavity starts at x = WALL in world (outer box starts at 0)
    body = box(0, 0, 0, OUT_W, OUT_D, WALL_TOP)
    cut(body, box(WALL, WALL, FLOOR, OUT_W - WALL, OUT_D - WALL, WALL_TOP + 1))
    # corner columns for the lid screws
    for cx, cy in column_centres():
        union(body, cyl((cx, cy, FLOOR - 0.1), (cx, cy, WALL_TOP), COLUMN_D))
        cut(body, cyl((cx, cy, WALL_TOP - INSERT_DEPTH), (cx, cy, WALL_TOP + 1), COLUMN_INSERT_D))
    # PCB standoffs with heat-set insert holes
    for hx, hy in HOLES:
        x, y = W0 + wx(hx), W0 + wy(hy)
        union(body, cyl((x, y, FLOOR - 0.1), (x, y, PCB_Z0), STANDOFF_D))
        cut(body, cyl((x, y, PCB_Z0 - INSERT_DEPTH), (x, y, PCB_Z0 + 1), INSERT_D))
    z0, z1 = PCB_Z1 - TERM_WIN_BELOW, PCB_Z1 + TERM_WIN_ABOVE
    # back wall (Y max): relay + dimmer terminals
    for x0, x1 in TOP_TERMINALS:
        cut(body, box(W0 + wx(x0), OUT_D - WALL - 1, z0, W0 + wx(x1), OUT_D + 1, z1))
    # front wall (Y = 0): CAN, RS485, water terminals
    for x0, x1 in BOTTOM_TERMINALS:
        cut(body, box(W0 + wx(x0), -1, z0, W0 + wx(x1), WALL + 1, z1))
    # USB-C
    ux = W0 + wx(USB_X)
    uz = PCB_Z1 + USB_ZC
    cut(body, box(ux - USB_W / 2, -1, uz - USB_H / 2, ux + USB_W / 2, WALL + 1, uz + USB_H / 2))
    # GPS SMA bulkhead
    sx = W0 + wx(SMA_X)
    cut(body, cyl((sx, -1, PCB_Z1 + SMA_Z), (sx, WALL + 1, PCB_Z1 + SMA_Z), SMA_D))
    # cable glands for the 12 V input, left wall
    for gy in GLAND_Y_BOARD:
        y = W0 + wy(gy)
        cut(body, cyl((-1, y, PCB_Z1 + GLAND_Z), (WALL + 1, y, PCB_Z1 + GLAND_Z), GLAND_D))
    # mounting ears on the left and right ends
    for y in EAR_Y:
        for x0, x1, sx_ in ((-EAR_L, 0.5, -EAR_L / 2 - 0.5), (OUT_W - 0.5, OUT_W + EAR_L, OUT_W + EAR_L / 2 + 0.5)):
            union(body, box(x0, y - EAR_W / 2, 0, x1, y + EAR_W / 2, EAR_T))
            cut(body, cyl((sx_, y, -1), (sx_, y, EAR_T + 1), EAR_SLOT))
    return body


def build_lid():
    lid = box(0, 0, WALL_TOP, OUT_W, OUT_D, WALL_TOP + LID_T)
    # locating lip that drops inside the walls
    o0x, o0y = WALL + LIP_GAP, WALL + LIP_GAP
    o1x, o1y = OUT_W - WALL - LIP_GAP, OUT_D - WALL - LIP_GAP
    lip = box(o0x, o0y, WALL_TOP - LIP_H, o1x, o1y, WALL_TOP + 0.1)
    cut(lip, box(o0x + LIP_T, o0y + LIP_T, WALL_TOP - LIP_H - 1, o1x - LIP_T, o1y - LIP_T, WALL_TOP + 1))
    for cx, cy in column_centres():
        cut(lip, cyl((cx, cy, WALL_TOP - LIP_H - 1), (cx, cy, WALL_TOP + 1), COLUMN_D + 2 * LIP_GAP + 0.4))
    union(lid, lip)
    for cx, cy in column_centres():
        cut(lid, cyl((cx, cy, WALL_TOP - 1), (cx, cy, WALL_TOP + LID_T + 1), LID_SCREW_D))
        cut(lid, cyl((cx, cy, WALL_TOP + LID_T - LID_CBORE_DEPTH), (cx, cy, WALL_TOP + LID_T + 1), LID_CBORE_D))
    return lid


def run(context):
    try:
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        root = design.rootComponent

        results = {}
        for name, builder, colour in (("Base", build_base, None), ("Lid", build_lid, None)):
            occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            occ.component.name = name
            body = occ.component.bRepBodies.add(builder())
            body.name = name
            results[name] = (occ, body)

        # PCB fit check: KiCad STEP has the board corner at the origin, board spanning X 0..230, Y -135..0
        pcb_msg = "PCB STEP not found"
        if os.path.exists(PCB_STEP):
            before = root.occurrences.count
            opts = app.importManager.createSTEPImportOptions(PCB_STEP)
            app.importManager.importToTarget(opts, root)
            if root.occurrences.count > before:
                pcb = root.occurrences.item(root.occurrences.count - 1)
                m = adsk.core.Matrix3D.create()
                m.translation = adsk.core.Vector3D.create((WALL + BX0) * CM, (WALL + BY1) * CM, PCB_Z0 * CM)
                pcb.transform = m
                pcb.component.name = "VanController PCB"
                pcb_msg = "PCB imported and positioned"

        # exports for printing
        em = design.exportManager
        for name, (occ, body) in results.items():
            stl = em.createSTLExportOptions(body, os.path.join(OUTDIR, f"VanController_{name.lower()}.stl"))
            stl.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
            em.execute(stl)
        em.execute(em.createSTEPExportOptions(os.path.join(OUTDIR, "VanController_enclosure_assembly.step"), root))
        em.execute(em.createFusionArchiveExportOptions(os.path.join(OUTDIR, "VanController_enclosure.f3d"), root))

        app.activeViewport.fit()
        ui.messageBox(
            f"VanController enclosure built.\n\nOutside: {OUT_W:.1f} x {OUT_D:.1f} x {WALL_TOP + LID_T:.1f} mm "
            f"(+{EAR_L:.0f} mm mounting ears each end)\n{pcb_msg}.\n\nExported to:\n{OUTDIR}")
    except Exception:
        ui.messageBox("Enclosure script failed:\n" + traceback.format_exc())
