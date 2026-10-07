VanController rev0.3 - PCB fabrication + turnkey assembly order
=============================================================

Files
-----
01_Gerbers_*.zip          Gerber RS-274X + Excellon drill (KiCad 10). Layers: F.Cu, In1.Cu, In2.Cu, B.Cu,
                          mask, paste, silkscreen (top/bottom), Edge.Cuts, drill map.
02_BOM_*.xlsx             Bill of materials with manufacturer part numbers, fit/DNP and loose items.
03_PickPlace_*.csv        Centroid file, mm, origin = bottom-left corner of the board, KiCad rotation convention.
04_Assembly_Drawing_*.pdf Top-side assembly drawing with reference designators.
05_Schematic_*.pdf        Full schematic.
06_3D_*.png, 07_*.step    3D views / model for reference.
08_Enclosure_*            OPTIONAL separate 3D-printing order: enclosure base + lid STL and print notes.

PCB fabrication
---------------
Size:                230.0 x 135.0 mm, rectangular
Layers:              4 (stack-up: F.Cu signal / In1.Cu GND plane / In2.Cu +12V plane / B.Cu signal)
Material / Tg:       FR-4, Tg 150 or higher
Thickness:           1.6 mm
Outer copper:        1 oz (35 um). (2 oz is not usable: the design has 0.15 mm spacing at fine-pitch ICs)
Inner copper:        1 oz (35 um)
Min track/space:     0.15 / 0.15 mm
Min hole:            0.2 mm (ESP32 module thermal vias), standard vias 0.3 mm
Surface finish:      ENIG
Solder mask:         Green (any colour acceptable), white silkscreen
Via treatment:       Tented
Impedance control:   Not required
Quantity:            [your choice, e.g. 5 boards]

Assembly
--------
Type:                Turnkey (please source all parts), top side only
Parts per board:     200 SMD placements (200 centroid entries). Through-hole: 0 soldered.
Quantity:            [your choice, e.g. 2 or 3 boards assembled]
Through-hole parts:  DO NOT SOLDER. Please source them (BOM, Fit = "Ship loose") and ship them loose with
                     the boards: relays K1-K6, terminal headers J5-J18, J21-J22, fuse holders F1-F13,
                     pin headers J4, J20, JP1-JP10 (47 parts per board). Customer solders them.
DNP (do not fit):    J1, J2 (M5 stud pads - bolts fitted by customer), H1-H4 (mounting holes).
Do not fit fuses:    fuse holders only; no blade fuses in F1-F13.
Do not fit shunts:   JP1-JP10 jumper shunts shipped loose, not fitted.
Ship loose:          8 x Phoenix 1757022, 8 x Phoenix 1757019 plugs, 10 x jumper shunts per board.

Polarity and orientation
------------------------
- LEDs D4, D5, D12-D17, D40; diodes D1-D3, D6-D11, D24-D29: orientation per assembly drawing/silkscreen.
  D1 (SMDJ26CA) is bidirectional.
- C2 is a polarised aluminium electrolytic: + marking per silkscreen.
- U4 ESP32-S3-WROOM-1-N16: antenna end overhangs/faces the right board edge; keep the antenna area free.
  Variant must be N16 (no PSRAM) - do NOT substitute R8/R16V octal-PSRAM variants.
- U9 LIS3DH (LGA-16 3x3 mm, hidden joints): X-ray inspection requested. U10/U11: AOI is sufficient.
- Fine-pitch ICs have 0.15 mm pad gaps: no solder-mask dams needed; open the mask across those pad areas.

Testing
-------
No functional test required; please report any DFM issues before production.

Substitutions
-------------
Resistors and ceramic capacitors: any equivalent to the stated value, tolerance, voltage and dielectric.
All other parts: please ask before substituting.
