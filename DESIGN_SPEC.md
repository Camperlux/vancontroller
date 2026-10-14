# VanController: Design Spec and GPIO Map

Status: rev 0.3a (rev 0.3 + dry-contact solder jumpers SJ1-SJ6, 2026-10-14). Schematic complete (ERC: 0 violations). 4-layer board fully routed (DRC: 0 errors, 0 unconnected; only the ESP32 silkscreen touching the board edge is flagged). Prototype order (5 PCBs, 2 SMD-assembled) submitted to PCBWay for review on 2026-10-06; see [docs/ORDER_LOG.md](docs/ORDER_LOG.md). Not yet verified on a physical build. Section 7 lists the open design checks.

## 1. Requirements and design decisions

| Block | Requirement | Decision |
|---|---|---|
| MCU | ESP32-S3, native USB | ESP32-S3-WROOM-1, USB-C with USBLC6 ESD |
| Supply | 12 V vehicle, reverse polarity and load dump | 30 A ATO main fuse, SMDJ26CA bidirectional TVS, LM74700-Q1 ideal diode with 2 × CSD18540Q5B |
| Relays | 6, fused, COM/NO/NC terminals; optionally dry contacts | Omron G5LE (10 A), 10 A mini blade fuse per channel. COM is fed with fused +12 V by default; each channel converts to a dry contact (remove the fuse, cut solder jumper SJ) |
| Dimmers | 6 low-side PWM, fused | BUK9M12-60EX (60 V logic-level), 5 A mini blade fuse, SS54 freewheel diode |
| Comms | CAN + RS485 with switchable termination | TJA1051T/3 (3.3 V I/O); THVD1450 with termination and fail-safe bias jumpers |
| Sensors | GPS, accelerometer, water level | MAX-M10S + u.FL active antenna; LIS3DH; ADS1115 with 2 jumper-selectable water inputs |
| Load currents | Chosen 2026-10-05 | 10 A per relay, 5 A per dimmer, 30 A total |
| Board | ~160 × 120 mm, no enclosure limit; enlarged on request | **230 × 135 mm**, 4 layers, 1 oz copper (2 oz outer is not manufacturable with the 0.15 mm fine-pitch spacing). All 12 output terminals on the top edge |

## 2. Module choice

Use **ESP32-S3-WROOM-1-N16** (no PSRAM) or **-N8R2** (quad PSRAM). Do not use the **R8 / R16V** (octal PSRAM) variants, because they take GPIO 35-37, which this map uses.

## 3. GPIO map

Not used: GPIO 26-32 (internal flash), 19/20 (USB D-/D+), 43/44 (UART0 debug header), 2 (unconnected), 3/45/46 (strapping, left at defaults). GPIO 0 is the BOOT button.

| GPIO | Net | Function | Notes |
|---|---|---|---|
| 1 | VIN_SENSE | ADC1_CH0 | +12V via 120k/10k + 100 nF (14.4 V → 1.11 V) |
| 4, 5, 6, 7, 15, 16 | RLY1-6 | Relay drivers | AO3400A, 100 Ω gate, 100k pull-down |
| 8 / 9 | I2C_SDA / I2C_SCL | I2C | 4.7k pull-ups |
| 10, 11, 12, 13, 14, 21 | DIM1-6 | LEDC PWM | 47 Ω gate, 100k pull-down. ~20 kHz for LEDs |
| 17 / 18 | CAN_TX / CAN_RX | TWAI | TJA1051T/3 |
| 39 / 40 / 41 | RS485_TX / RX / DE | UART1 | DE and /RE tied, 10k pull-down (receive by default) |
| 37 / 38 / 42 | GPS_TX / GPS_RX / GPS_PPS | UART2 | MAX-M10S, 9600 baud default |
| 35 | ACC_INT1 | LIS3DH INT1 | Wake on motion |
| 36 | ADC_ALERT | ADS1115 ALERT/RDY | 10k pull-up |
| 47 | EXP_INT | TCA9535 /INT | 10k pull-up |
| 48 | LED_STAT | Status LED (blue) | |
| 0 | BOOT | Boot button | 10k pull-up |
| EN | EN | Reset button | 10k pull-up + 1 µF |

### I2C devices

| Address | Device | Use |
|---|---|---|
| 0x19 | LIS3DH | Accelerometer (SDO/SA0 pulled high) |
| 0x48 | ADS1115 | AIN0 water 1, AIN1 water 2, AIN2/AIN3 on the AUX ADC header |
| **0x21** | TCA9535 | P00-P05 relay fuse sense, P10-P15 dimmer fuse sense, P06 yellow LED, P07 GPS reset. A0 is tied high (changed during routing) |

Fuse sense: each output is tapped after its fuse through 33k/10k (12 V → 2.8 V, above the TCA9535 VIH of 2.31 V) with a BAT54S clamp to +3V3. **A blown fuse (or a missing fuse) reads low.**

## 4. Terminals

| Terminal | Pins (left to right as printed) |
|---|---|
| Relay 1-6 (top edge) | NC / COM / NO. By default COM is fused +12 V, so NO switches +12 V to the load. In dry-contact mode COM/NO/NC are free contacts (see below) |
| Dimmer 1-6 (top edge, right of the relays) | LOAD- (MOSFET drain) / LOAD+ (fused +12 V) |
| Power input | M5 studs: +12V and GND |
| CAN | CANH / CANL / GND. Jumper CAN TERM fits the split 120 Ω termination |
| RS485 | A / B / GND. Jumpers: 485 TERM (120 Ω), 485 BIAS+ and BIAS- (680 Ω fail-safe) |
| Water 1-2 | SIG / GND. Fit ONE jumper per input: RESISTIVE (470 Ω pull-up), 4-20mA (150 Ω shunt) or 0-5V (10k/15k divider). No jumper = 0-3.3 V direct |

All signal and load terminals are Phoenix MSTBA 2,5 headers (5.08 mm) with MSTB 2,5/x-ST-5,08 plugs.

### Dry-contact mode (per relay channel)

Each relay channel can switch a circuit that is not the van's 12 V, such as another battery bank, a signal input on other equipment or a separately fused supply:

1. **Remove the channel's blade fuse** (F2-F7 for relays 1-6). This disconnects COM from the board's +12 V.
2. **Cut solder jumper SJ1-SJ6** (marked SJn, between the relay and its fuse) with a sharp knife, across the thin copper link between its two pads. This disconnects the fuse-sense resistor from COM.

COM, NO and NC then connect only to the relay contacts. The relay coil-to-contact isolation separates them from the board. To restore the default, bridge the SJ pads with solder and refit the fuse.

- The firmware sees the channel's fuse-sense input low (as for a blown fuse). Treat it as dry-contact mode in configuration.
- Fuse the external circuit externally: the board's channel fuse is out of circuit.
- **Low voltage only (≤ 30 V DC).** The board's copper spacing is not designed for mains, so do not switch mains through the relays.

## 5. Schematic structure

`VanController.kicad_sch` (root) → Power, MCU, Relays (6 × `relay_channel.kicad_sch`), Dimmers (6 × `dimmer_channel.kicad_sch`), Comms, Sensors. Edit a channel file once to change all six channels.

## 6. PCB

- 230 × 135 mm, 4 layers: F.Cu signals + power, **In1.Cu solid GND**, **In2.Cu solid +12V**, B.Cu signals + GND pour.
- High-current paths are fixed 2.5 mm tracks on both outer layers (relay NO/COM/NC) or F.Cu (dimmer LOAD-), dimmer LOAD+ on both layers, plus copper areas for the 30 A input (stud → fuse → MOSFETs) with via fields into the +12 V plane.
- Net classes: Default 0.2/0.15 mm, Power 0.5 mm, Load 1.0 mm (track/clearance).
- No copper under the ESP32 antenna (right edge, rule area).
- Routing: SMD pads on GND/+12V are fanned out to the planes with short stubs and vias, the inner layers are set as power planes (no signal routing), signals are autorouted on F.Cu/B.Cu with Freerouting 1.9.0, then hand-fixed (`tools/patch_pcb.py`, plus local fixes around the LIS3DH).
- The reverse-polarity MOSFET gate link runs on B.Cu between the VIN_F and +12V copper areas, so it never splits the VIN_F area (an early autoroute had cut Q2's sources off from the input).
- Layout: relay columns (21 mm pitch) and dimmer columns (15 mm pitch) along the top; power input bottom-left, then comms, sensors and the MCU along the bottom.

## 7. Design checks and cautions

Items 1, 2 and 8 are still open (tracked in [docs/ORDER_LOG.md](docs/ORDER_LOG.md)). Items 3 to 6 are for the first build.

1. **TPS54360 compensation**: the buck values (RT 162k, COMP 16.9k/4.7nF/47pF, L 10 µH, 2 × 47 µF) follow TI's typical 5 V design. Confirm them in TI WEBENCH for your exact parts.
2. **MAX-M10S RF input**: confirm against the u-blox integration manual that RF_IN needs no external DC block with the VCC_RF → 10 Ω → 27 nH active-antenna bias used here.
3. **Thermals at 30 A**: the input stage and +12 V plane are sized for the 30 A fuse, not for continuous 30 A in a hot enclosure. Measure the temperature rise on the first build.
4. **Dimmer freewheel path** (SS54 diode) is routed at 1.0 mm. That is fine for LED loads, but widen it if you drive pumps or motors.
5. **Relay contacts**: the G5LE is rated 10 A resistive. Derate it for inductive or lamp loads, and size each blade fuse to its load.
6. Order with 1 oz copper and ENIG finish. On 1 oz, each relay path (2.5 mm on both outer layers) is good for about 10 A at roughly a 20 °C rise, and each dimmer LOAD- track for about 5 A. Measure on the first build, and add solder-mask openings on the high-current tracks (to build them up with solder) if they run warm.
7. Run KiCad's *Update PCB from Schematic* once. It only adds the missing `ki_fp_filters` field to each footprint (199 cosmetic parity warnings); all nets already match.
8. **Review the autorouted signal routing** in KiCad before ordering, especially the USB D+/D- pair (not length-matched), the GPS RF_IN feed (keep it short; ideally a 50 Ω coplanar line) and the buck switch node (SW5) loop.
9. ~~Add part numbers to the BOM~~ Done: `manufacturing/.../02_BOM_*.xlsx` has a manufacturer part number for every fitted line. The F1 holder part number is still to be confirmed with PCBWay.

## 8. Firmware notes

- ESP32-S3 native USB (GPIO19/20) is the programming and debug port. BOOT = GPIO0 button, RESET = EN button. UART0 is also on header J4.
- Relay and dimmer outputs default OFF at power-up (100k gate pull-downs). Drive the dimmers with LEDC at about 20 kHz.
- Fuse status: read the TCA9535 at **0x21**. A low input means a blown or missing fuse, or a relay channel set to dry-contact mode (configure which channels are dry so a low isn't reported as a fault). Its /INT on GPIO47 signals changes.
- Input voltage: GPIO1 ADC, V_in = V_adc × 13 (120k/10k divider).
- Water level: ADS1115 at 0x48, AIN0/AIN1. The scaling depends on which input jumper is fitted (see section 4).
- Accelerometer LIS3DH at 0x19, INT1 on GPIO35 for wake-on-motion.
- GPS MAX-M10S on UART2 (GPIO37 TX / GPIO38 RX, 9600 baud default), PPS on GPIO42; reset via TCA9535 P07.
- CAN via TWAI (GPIO17/18); RS485 on UART1 (GPIO39/40, DE on GPIO41, high to transmit).
