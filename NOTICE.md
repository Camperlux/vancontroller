# Licences and credits

## VanController

Copyright (c) 2026 Camperlux (https://camperlux.co.uk).

- **The hardware design and documentation**, meaning the KiCad project (`*.kicad_pro`, `*.kicad_sch`, `*.kicad_pcb`), the fabrication and manufacturing files (`fab/`, `manufacturing/`), the enclosure models (`enclosure/*.stl`, `*.step`), `docs/` and all Markdown files, are under [Creative Commons Attribution-NonCommercial-ShareAlike 4.0](LICENSE-docs.txt).
  - You may build, study, change and share the design for any **non-commercial** purpose: your own van, hobby builds, research and teaching. Credit Camperlux and share changes under the same licence.
- **The software**, meaning the scripts in `tools/` and the Fusion 360 script in `enclosure/VanControllerEnclosure/`, is under the [PolyForm Noncommercial License 1.0.0](LICENSE.md).
- **Commercial use is not allowed** under either licence. That includes selling boards, kits, enclosures, installations or products based on this design, or using it in a business. For a commercial licence, contact Camperlux through [camperlux.co.uk](https://camperlux.co.uk).

## Parts from others

Their own licences apply to these, not the ones above.

| Part | Where | Licence |
|---|---|---|
| KiCad symbol, footprint and 3D-model libraries (embedded in the schematic, board and STEP files) | `*.kicad_sch`, `*.kicad_pcb`, `*.step` | CC BY-SA 4.0 with the KiCad library exception (designs and generated files that use the libraries are not affected by its share-alike terms) |
| Freerouting (the autorouter, not included; see README) | `tools/freerouting/` | GPL-3.0 |

## Trademarks

ESP32 and Espressif (Espressif Systems), u-blox, Omron, Phoenix Contact, Littelfuse, Keystone, Texas Instruments, NXP, STMicroelectronics, Nexperia, Fusion 360 / Autodesk, KiCad and PCBWay are trademarks of their owners. This project is not affiliated with them.
