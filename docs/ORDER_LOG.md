# VanController manufacturing and order log

## Rev 0.3: PCBWay prototype order

| Date | Event |
|---|---|
| 2026-10-05 | Rev 0.3 board finished: routed, DRC clean, fab outputs generated. |
| 2026-10-06 | Order package built (`tools/make_order_package.py` → `manufacturing/VanController_rev0.3_PCBWay/`). Quote configured on pcbway.com, saved to cart, files uploaded and submitted for engineering review. |
| 2026-10-07 | PCBWay engineering questions received: solder-mask dams and X-ray (see below). |

### Cart items (submitted for review 2026-10-06; order numbers kept in the PCBWay account)

| Item | PCBWay number | Spec | Quoted |
|---|---|---|---|
| PCB | (PCBWay PCB order no.) | 4 layers, 230 × 135 mm, 1.6 mm, FR-4 S1000H TG150, 1 oz inner and outer copper, ENIG, green mask, white silkscreen, tented vias, 6/6 mil, 0.2 mm minimum hole, 5 boards, 4-5 day build | $141.44 |
| Assembly | (PCBWay assembly order no.) | Turnkey (PCBWay sources all parts), top side, **SMD only**, 2 boards. 71 unique parts, 200 SMD placements. Through-hole parts sourced but shipped loose | $88.00 + components (to be quoted after BOM review) |
| Shipping | | DHL, 2-4 days | $42.52 |
| Discount | | Automatic order discount | −$30.00 |

Quote total before components, import VAT and courier handling: **$241.96**.

Files uploaded: `01_Gerbers_VanController_rev0.3.zip`, `02_BOM_VanController_rev0.3.xlsx`, `03_PickPlace_VanController_rev0.3.csv` and `VanController_rev0.3_assembly_docs.zip` (order notes, assembly drawing, schematic, 3D view).

### Decisions made while quoting

| Decision | Why |
|---|---|
| **1 oz outer copper, not 2 oz** | 2 oz forced PCBWay's minimum track/space up to 8 mil, but the design has 0.15 mm (6 mil) gaps at the fine-pitch ICs, so 2 oz would not pass review. It also cost $388 against $141 for the bare boards and doubled the build time. On 1 oz, each relay path (2.5 mm tracks on both outer layers) carries about 10 A at a roughly 20 °C rise. |
| **ENIG, not HASL** | HASL saves about $22, but its uneven solder coating is risky on the LIS3DH 0.5 mm-pitch LGA and the TSSOP parts. |
| **Through-hole parts fitted by the owner** | Relays, terminal headers, fuse holders and pin headers (47 per board) are shipped loose. This saved about $13 of assembly labour and allows a terminal fit check against the enclosure before soldering. |
| **5 boards made, 2 assembled** | 5 is the minimum quantity; 2 assembled prototypes plus 3 spare bare boards. |
| **Fuses and jumper shunts not fitted** | Blade fuses are sized per load by the owner. Jumper shunts and the 16 Phoenix mating plugs are shipped loose. |

### PCBWay engineering questions (2026-10-07)

| Question | Reply (recommended; to be sent by the owner) |
|---|---|
| IC pad spacing is 0.15 mm, below their 0.19 mm minimum for a solder-mask bridge (dam) between pads | **Proceed without solder bridges**: open the mask across the fine-pitch IC pad areas. The spacing comes from standard footprints (LIS3DH 0.5 mm pitch LGA); gang mask openings are normal at this pitch. |
| X-ray inspection for U9/U10/U11 (from the order notes) | **X-ray U9 (LIS3DH, LGA, hidden joints) only.** U10/U11 have visible leads, so AOI is enough. PCBWay asked to update the quote. |

Lesson for the next revision: the order notes should state optional inspection requests as optional, and the design could use 0.19 mm or larger pad gaps where the footprint allows, to keep the mask dams.

### Open items with PCBWay

- **F1 fuse holder:** full Littelfuse part number for the ATO holder (footprint FLR 178.6165) not confirmed. PCBWay was asked to confirm or quote an equivalent.
- **Components quote:** pending their BOM review.
- **Checkout:** once both items reach *Awaiting Payment*. DHL (DTP) settles import duties up front if preferred.

### Owner's assembly notes (through-hole parts)

47 parts per board: relays K1-K6, terminal headers J5-J18 / J21-J22, fuse holders F1-F13, pin headers J4, J20, JP1-JP10. The relay contacts, F1 and the output terminal pins connect to large copper areas. Use a 60-80 W iron with a large chisel tip, and allow each joint time to heat through.

### Pre-order design checks (from DESIGN_SPEC.md section 7)

These are design checks the manufacturer does not do. Record the outcome here:

| Check | Status |
|---|---|
| TPS54360 compensation confirmed in TI WEBENCH | Open |
| MAX-M10S RF_IN DC block confirmed against the u-blox integration manual | Open |
| Autorouted signals reviewed in KiCad (USB pair, GPS RF feed, buck switch loop) | Open |
| Temperature rise measured at full load on the first build | After delivery |
