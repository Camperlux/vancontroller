"""Generate the complete VanController schematic (all sheets) from the circuit definitions below.

Every component pin is joined to its net by a short wire stub and a net label, hierarchical label
or power symbol. UUIDs are deterministic (uuid5), so re-running keeps symbol identities stable for
the PCB. Running this OVERWRITES all .kicad_sch files in the project.
"""
import copy
import math
import os
import uuid

import kilib as k
from kilib import Sym

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = "VanController"
DATE = "2026-10-05"
REV = "0.2"
G = 2.54
NS = uuid.UUID("8d3c4a8e-2f0b-4c55-9a51-6f0e3c7b9d10")
NC = None
POWER = {"GND": "power:GND", "+3V3": "power:+3V3", "+5V": "power:+5V", "+12V": "power:+12V",
         "VBUS": "power:VBUS"}


def U(*key):
    return str(uuid.uuid5(NS, "/".join(key)))


# --------------------------------------------------------------------------- footprints
FP = {
    "R": "Resistor_SMD:R_0603_1608Metric",
    "C": "Capacitor_SMD:C_0603_1608Metric",
    "C0805": "Capacitor_SMD:C_0805_2012Metric",
    "C1210": "Capacitor_SMD:C_1210_3225Metric",
    "CP": "Capacitor_SMD:CP_Elec_8x10",
    "LED": "LED_SMD:LED_0603_1608Metric",
    "SOD123": "Diode_SMD:D_SOD-123",
    "SMA": "Diode_SMD:D_SMA",
    "SMC": "Diode_SMD:D_SMC",
    "JMP": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    "T2": "Connector_Phoenix_MSTB:PhoenixContact_MSTBA_2,5_2-G-5,08_1x02_P5.08mm_Horizontal",
    "T3": "Connector_Phoenix_MSTB:PhoenixContact_MSTBA_2,5_3-G-5,08_1x03_P5.08mm_Horizontal",
    "MINIFUSE": "Fuse:Fuseholder_Blade_Mini_Keystone_3568",
    "BTN": "Button_Switch_SMD:SW_SPST_B3U-1000P",
}


class Part:
    def __init__(self, ref, lib_id, value, fp, pins, mpn="", note=""):
        self.ref, self.lib_id, self.value, self.fp = ref, lib_id, value, fp
        self.pins, self.mpn, self.note = pins, mpn, note


def R(v, a, b, fp="R"):
    return Part("R", "Device:R", v, FP[fp], {"1": a, "2": b})


def C(v, a, b="GND", fp="C"):
    return Part("C", "Device:C", v, FP[fp], {"1": a, "2": b})


def CP(v, a, b="GND"):
    return Part("C", "Device:C_Polarized", v, FP["CP"], {"1": a, "2": b})


def LED(color, a, kk="GND"):
    return Part("D", "Device:LED", color, FP["LED"], {"1": kk, "2": a})


def D(lib, v, fp, kk, a):
    return Part("D", lib, v, FP.get(fp, fp), {"1": kk, "2": a})


def JMP(a, b, label):
    return Part("JP", "Jumper:Jumper_2_Open", label, FP["JMP"], {"1": a, "2": b})


def TERM(n, nets, label):
    return Part("J", f"Connector:Screw_Terminal_01x0{n}", label, FP[f"T{n}"],
                {str(i + 1): x for i, x in enumerate(nets)}, mpn=f"Phoenix MSTBA 2,5/{n}-G-5,08 + MSTB 2,5/{n}-ST-5,08")


def BAT54S(node):
    return Part("D", "Diode:BAT54S", "BAT54S", "Package_TO_SOT_SMD:SOT-23", {"1": "GND", "2": "+3V3", "3": node})


def FLAG(net):
    return Part("#FLG", "power:PWR_FLAG", "PWR_FLAG", "", {"1": net})


# --------------------------------------------------------------------------- circuits
def power_sheet():
    groups = []
    groups.append([
        Part("J", "Connector_Generic:Conn_01x01", "+12V IN (M5 stud)", "MountingHole:MountingHole_5.3mm_M5_DIN965_Pad",
             {"1": "VBAT"}),
        Part("J", "Connector_Generic:Conn_01x01", "GND IN (M5 stud)", "MountingHole:MountingHole_5.3mm_M5_DIN965_Pad",
             {"1": "GND"}),
        Part("F", "Device:Fuse", "30A ATO", "Fuse:FuseHolder_Blade_ATO_Littelfuse_FLR_178.6165",
             {"1": "VBAT", "2": "VIN_F"}, mpn="Littelfuse FLR 178.6165 + 30 A ATO fuse"),
        Part("D", "Device:D_TVS", "SMDJ26CA", FP["SMC"], {"1": "VIN_F", "2": "GND"},
             note="Bidirectional 3 kW load-dump TVS (bidirectional so a reversed battery does not blow F1 via the TVS)"),
        FLAG("VIN_F"),
    ])
    groups.append([
        Part("U", "Power_Management:LM74700", "LM74700QDBVRQ1", "Package_TO_SOT_SMD:SOT-23-6",
             {"1": "VCAP_RP", "2": "GND", "3": "VIN_F", "4": "+12V", "5": "GATE_RP", "6": "VIN_F"}),
        C("100nF", "VCAP_RP", "VIN_F"),
        Part("Q", "Transistor_FET:CSD18540Q5B", "CSD18540Q5B", "Package_TO_SOT_SMD:TDSON-8-1",
             {"1": "VIN_F", "2": "VIN_F", "3": "VIN_F", "4": "GATE_RP", "5": "+12V"}),
        Part("Q", "Transistor_FET:CSD18540Q5B", "CSD18540Q5B", "Package_TO_SOT_SMD:TDSON-8-1",
             {"1": "VIN_F", "2": "VIN_F", "3": "VIN_F", "4": "GATE_RP", "5": "+12V"}),
        CP("100uF 35V", "+12V"),
        C("4.7uF 50V", "+12V", fp="C1210"),
        FLAG("+12V"), FLAG("GND"),
    ])
    groups.append([
        Part("U", "Regulator_Switching:TPS54360DDA", "TPS54360DDA", "Package_SO:TI_SO-PowerPAD-8_ThermalVias",
             {"1": "BOOT5", "2": "+12V", "3": NC, "4": "RT5", "5": "FB5", "6": "COMP5", "7": "GND", "8": "SW5",
              "9": "GND"}, note="12 V -> 5 V / 2 A, 600 kHz. EN left open (internal pull-up)."),
        C("4.7uF 100V", "+12V", fp="C1210"), C("4.7uF 100V", "+12V", fp="C1210"), C("100nF 100V", "+12V"),
        C("100nF", "BOOT5", "SW5"),
        R("162k", "RT5", "GND"),
        R("16.9k", "COMP5", "COMP5B"), C("4.7nF", "COMP5B"), C("47pF", "COMP5"),
        D("Device:D_Schottky", "B360A", "SMA", "SW5", "GND"),
        Part("L", "Device:L", "10uH 6A", "Inductor_SMD:L_Bourns_SRP1038C_10.0x10.0mm", {"1": "SW5", "2": "+5V"},
             mpn="Bourns SRP1038C-100M"),
        R("53.6k", "+5V", "FB5"), R("10.2k", "FB5", "GND"),
        C("47uF 10V", "+5V", fp="C1210"), C("47uF 10V", "+5V", fp="C1210"),
        FLAG("+5V"),
    ])
    groups.append([
        D("Device:D_Schottky", "B5819W", "SOD123", "+5V", "VBUS"),
        FLAG("VBUS"),
        Part("U", "Regulator_Linear:AMS1117-3.3", "AMS1117-3.3", "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
             {"1": "GND", "2": "+3V3", "3": "+5V"}),
        C("22uF", "+5V", fp="C0805"), C("22uF", "+3V3", fp="C0805"),
        R("120k", "+12V", "VIN_SENSE"), R("10k", "VIN_SENSE", "GND"), C("100nF", "VIN_SENSE"),
        R("1k", "+3V3", "LED_PWR"), LED("Green", "LED_PWR"),
    ])
    groups.append([Part("H", "Mechanical:MountingHole_Pad", "M3", "MountingHole:MountingHole_3.2mm_M3_Pad_Via",
                        {"1": "GND"}) for _ in range(4)])
    notes = ("Power: 12 V in -> 30 A ATO main fuse -> bidirectional load-dump TVS -> LM74700 ideal diode "
             "with 2 x CSD18540Q5B in parallel (reverse polarity) -> +12V.\n"
             "TPS54360 buck 12 V -> 5 V (2 A, 600 kHz, values per TI datasheet example; verify with WEBENCH). "
             "USB VBUS ORed into +5V via B5819W. AMS1117-3.3 -> +3V3.")
    return groups, notes


def mcu_sheet():
    esp = {"1": "GND", "40": "GND", "41": "GND", "2": "+3V3", "3": "EN",
           "4": "RLY1", "5": "RLY2", "6": "RLY3", "7": "RLY4", "8": "RLY5", "9": "RLY6",
           "10": "CAN_TX", "11": "CAN_RX", "12": "I2C_SDA", "13": "USB_DN", "14": "USB_DP",
           "15": NC, "16": NC, "17": "I2C_SCL",
           "18": "DIM1", "19": "DIM2", "20": "DIM3", "21": "DIM4", "22": "DIM5", "23": "DIM6",
           "24": "EXP_INT", "25": "LED_STAT", "26": NC, "27": "BOOT",
           "28": "ACC_INT1", "29": "ADC_ALERT", "30": "GPS_TX", "31": "GPS_RX",
           "32": "RS485_TX", "33": "RS485_RX", "34": "RS485_DE", "35": "GPS_PPS",
           "36": "U0RXD", "37": "U0TXD", "38": NC, "39": "VIN_SENSE"}
    groups = [
        [Part("U", "RF_Module:ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1-N16", "RF_Module:ESP32-S3-WROOM-1", esp,
              note="Use N16 or N8R2. NOT the octal-PSRAM R8 variants (they use GPIO35-37).")],
        [C("22uF", "+3V3", fp="C0805"), C("100nF", "+3V3"),
         R("10k", "+3V3", "EN"), C("1uF", "EN"),
         Part("SW", "Switch:SW_Push", "RESET", FP["BTN"], {"1": "EN", "2": "GND"}),
         R("10k", "+3V3", "BOOT"),
         Part("SW", "Switch:SW_Push", "BOOT", FP["BTN"], {"1": "BOOT", "2": "GND"}),
         R("4.7k", "+3V3", "I2C_SDA"), R("4.7k", "+3V3", "I2C_SCL"),
         R("1k", "LED_STAT", "LED_STAT_A"), LED("Blue", "LED_STAT_A")],
        [Part("J", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C",
              "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
              {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "SH": "GND",
               "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
               "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN",
               "A8": NC, "B8": NC}),
         R("5.1k", "CC1", "GND"), R("5.1k", "CC2", "GND"),
         Part("U", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
              {"1": "USB_DP", "6": "USB_DP", "3": "USB_DN", "4": "USB_DN", "5": "VBUS", "2": "GND"}),
         Part("J", "Connector_Generic:Conn_01x04", "UART0 debug", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
              {"1": "GND", "2": "U0TXD", "3": "U0RXD", "4": "+3V3"})],
    ]
    notes = ("MCU: ESP32-S3-WROOM-1. Strapping pins GPIO0 (BOOT button), 3, 45, 46 left at defaults. "
             "Place the module at the board edge with the antenna overhanging or over a copper keep-out on all layers.")
    return groups, notes


def relay_channel():
    groups = [
        [R("100", "CTRL", "GATE"), R("100k", "GATE", "GND"),
         Part("Q", "Transistor_FET:AO3400A", "AO3400A", "Package_TO_SOT_SMD:SOT-23",
              {"1": "GATE", "2": "GND", "3": "COIL_LO"}),
         D("Device:D", "1N4148W", "SOD123", "+12V", "COIL_LO"),
         R("2.2k", "+12V", "LED_A"), LED("Red", "LED_A", "COIL_LO")],
        [Part("F", "Device:Fuse", "10A mini", FP["MINIFUSE"], {"1": "+12V", "2": "OUT_F"},
              mpn="Keystone 3568 + mini blade fuse (size to load)"),
         Part("K", "Relay:G5LE-1", "G5LE-1-E DC12", "Relay_THT:Relay_SPDT_Omron-G5LE-1",
              {"5": "+12V", "2": "COIL_LO", "1": "OUT_F", "3": "NO", "4": "NC_OUT"}),
         TERM(3, ["NO", "OUT_F", "NC_OUT"], "NO / COM / NC")],
        [R("33k", "SENSE_TAP", "FUSE_SENSE"), R("10k", "FUSE_SENSE", "GND"), C("10nF", "FUSE_SENSE"),
         BAT54S("FUSE_SENSE"),
         Part("SJ", "Jumper:SolderJumper_2_Bridged", "DRY (cut)",
              "Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm", {"1": "OUT_F", "2": "SENSE_TAP"},
              note="Bridged by default. Cut it (and remove the fuse) to make COM/NO/NC a dry contact.")],
    ]
    notes = ("Relay channel. COM is fed from +12V through the channel fuse, so NO gives switched, fused +12 V. "
             "FUSE_SENSE is high (~2.8 V at 12 V) while the fuse is intact; BAT54S clamps transients to +3V3. "
             "DRY CONTACT: remove the fuse and cut solder jumper SJ (DRY). COM/NO/NC then connect only to the relay "
             "contacts; FUSE_SENSE reads low (firmware: treat as dry-contact mode). Not rated for mains.")
    return groups, notes


def dimmer_channel():
    groups = [
        [R("47", "CTRL", "GATE"), R("100k", "GATE", "GND"),
         Part("Q", "Transistor_FET:BUK9M12-60EX", "BUK9M12-60EX", "Package_TO_SOT_SMD:LFPAK33",
              {"1": "GND", "2": "GND", "3": "GND", "4": "GATE", "5": "LOAD_N"}),
         D("Device:D_Schottky", "SS54", "SMC", "OUT_F", "LOAD_N")],
        [Part("F", "Device:Fuse", "5A mini", FP["MINIFUSE"], {"1": "+12V", "2": "OUT_F"},
              mpn="Keystone 3568 + mini blade fuse (size to load)"),
         TERM(2, ["OUT_F", "LOAD_N"], "LOAD+ / LOAD-")],
        [R("33k", "OUT_F", "FUSE_SENSE"), R("10k", "FUSE_SENSE", "GND"), C("10nF", "FUSE_SENSE"),
         BAT54S("FUSE_SENSE")],
    ]
    notes = ("Dimmer channel, low-side PWM (LEDC, ~20 kHz). LOAD+ is fused +12 V, LOAD- is the MOSFET drain. "
             "SS54 freewheels inductive loads.")
    return groups, notes


def comms_sheet():
    groups = [
        [Part("U", "Interface_CAN_LIN:TJA1051T-3", "TJA1051T/3", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
              {"1": "CAN_TX", "2": "GND", "3": "+5V", "4": "CAN_RX", "5": "+3V3", "6": "CANL", "7": "CANH",
               "8": "GND"}),
         C("100nF", "+5V"), C("100nF", "+3V3"),
         JMP("CANH", "CANH_T", "CAN TERM"), R("60.4", "CANH_T", "CAN_MID"), R("60.4", "CAN_MID", "CANL"),
         C("4.7nF", "CAN_MID"),
         Part("D", "Power_Protection:NUP2105L", "NUP2105L", "Package_TO_SOT_SMD:SOT-23",
              {"1": "CANH", "2": "CANL", "3": "GND"}),
         TERM(3, ["CANH", "CANL", "GND"], "CANH / CANL / GND")],
        [Part("U", "Interface_UART:THVD1450D", "THVD1450D", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
              {"1": "RS485_RX", "2": "RS485_DE", "3": "RS485_DE", "4": "RS485_TX", "5": "GND", "6": "RS_A",
               "7": "RS_B", "8": "+3V3"}),
         C("100nF", "+3V3"), R("10k", "RS485_DE", "GND"),
         JMP("RS_A", "RS_AT", "485 TERM"), R("120", "RS_AT", "RS_B"),
         JMP("+3V3", "BIAS_A", "485 BIAS+"), R("680", "BIAS_A", "RS_A"),
         R("680", "RS_B", "BIAS_B"), JMP("BIAS_B", "GND", "485 BIAS-"),
         Part("D", "Diode:SM712_SOT23", "SM712", "Package_TO_SOT_SMD:SOT-23", {"1": "RS_A", "2": "RS_B", "3": "GND"}),
         TERM(3, ["RS_A", "RS_B", "GND"], "A / B / GND")],
    ]
    notes = ("Comms. CAN: TJA1051T/3 (5 V bus side, 3.3 V I/O), split termination on jumper CAN TERM. "
             "RS485: THVD1450 at 3.3 V, DE and /RE tied (receive by default), 120 R termination and 680 R fail-safe "
             "bias on jumpers.")
    return groups, notes


def sensors_sheet():
    groups = [
        [Part("U", "RF_GPS:MAX-M10S", "MAX-M10S", "RF_GPS:ublox_MAX",
              {"1": "GND", "10": "GND", "12": "GND", "2": "GPS_RX", "3": "GPS_TX", "4": "GPS_PPS", "5": NC,
               "6": "+3V3", "7": "+3V3", "8": "+3V3", "9": "GPS_RESET", "11": "RF_IN", "13": NC,
               "14": "VCC_RF", "15": NC, "16": NC, "17": NC, "18": NC},
              note="VIO_SEL open = 3.3 V I/O. Verify RF_IN DC blocking against the MAX-M10S integration manual."),
         C("10uF", "+3V3", fp="C0805"), C("100nF", "+3V3"),
         R("10", "VCC_RF", "VCC_RF_R"),
         Part("L", "Device:L", "27nH", "Inductor_SMD:L_0603_1608Metric", {"1": "VCC_RF_R", "2": "RF_IN"}),
         C("10nF", "VCC_RF_R"),
         Part("J", "Connector:Conn_Coaxial", "GPS ANT (u.FL)", "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical",
              {"1": "RF_IN", "2": "GND"})],
        [Part("U", "Sensor_Motion:LIS3DH", "LIS3DH", "Package_LGA:LGA-16_3x3mm_P0.5mm_LayoutBorder3x5y",
              {"1": "+3V3", "14": "+3V3", "2": NC, "3": NC, "4": "I2C_SCL", "5": "GND", "10": "GND", "12": "GND",
               "6": "I2C_SDA", "7": "ACC_SA0", "8": "+3V3", "9": NC, "11": "ACC_INT1", "13": NC, "15": NC, "16": NC},
              note="I2C address 0x19 (SDO high)."),
         C("10uF", "+3V3", fp="C0805"), C("100nF", "+3V3"), R("10k", "+3V3", "ACC_SA0"),
         Part("U", "Analog_ADC:ADS1115IDGS", "ADS1115IDGS", "Package_SO:TSSOP-10_3x3mm_P0.5mm",
              {"1": "GND", "2": "ADC_ALERT", "3": "GND", "4": "WL1", "5": "WL2", "6": "AIN2", "7": "AIN3",
               "8": "+3V3", "9": "I2C_SDA", "10": "I2C_SCL"}, note="I2C address 0x48."),
         C("100nF", "+3V3"), R("10k", "+3V3", "ADC_ALERT"),
         Part("J", "Connector_Generic:Conn_01x04", "AUX ADC", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
              {"1": "AIN2", "2": "AIN3", "3": "+3V3", "4": "GND"})],
    ]
    for n in (1, 2):
        groups.append([
            TERM(2, [f"WSIG{n}", "GND"], f"WATER {n}"),
            JMP(f"WSIG{n}", f"WPU{n}", f"W{n} RESISTIVE"), R("470", f"WPU{n}", "+3V3"),
            JMP(f"WSIG{n}", f"WSH{n}", f"W{n} 4-20mA"), R("150", f"WSH{n}", "GND", fp="R"),
            R("10k", f"WSIG{n}", f"WL{n}"),
            JMP(f"WL{n}", f"WDV{n}", f"W{n} 0-5V"), R("15k", f"WDV{n}", "GND"),
            C("100nF", f"WL{n}"), BAT54S(f"WL{n}"),
        ])
    fuse = {f"{4 + i}": f"RLY{i + 1}_FUSE" for i in range(6)}
    fuse.update({f"{13 + i}": f"DIM{i + 1}_FUSE" for i in range(6)})
    fuse.update({"1": "EXP_INT", "2": "GND", "3": "GND", "21": "+3V3", "10": "EXP_LED", "11": "GPS_RESET",
                 "12": "GND", "19": NC, "20": NC, "22": "I2C_SCL", "23": "I2C_SDA", "24": "+3V3"})
    groups.append([
        Part("U", "Interface_Expansion:TCA9535PWR", "TCA9535PWR", "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm", fuse,
             note="I2C address 0x21 (A0 high). P00-P05 relay fuse sense, P10-P15 dimmer fuse sense."),
        C("100nF", "+3V3"), R("10k", "+3V3", "EXP_INT"),
        R("1k", "EXP_LED", "EXP_LED_A"), LED("Yellow", "EXP_LED_A"),
    ])
    notes = ("Sensors. Water inputs: fit ONE jumper per input: RESISTIVE (470 R pull-up, e.g. 0-190 R sender), "
             "4-20mA (150 R shunt, loop powered externally), or 0-5V (10k/15k divider). No jumper = direct 0-3.3 V.")
    return groups, notes


# --------------------------------------------------------------------------- hierarchy
RLY = [f"RLY{i}" for i in range(1, 7)]
DIM = [f"DIM{i}" for i in range(1, 7)]

ROOT_SHEETS = [
    # name, file, x, y, width, left pins, right pins
    ("Power", "power.kicad_sch", 50.8, 30.48, 40.64, [], [("VIN_SENSE", "output")]),
    ("MCU", "mcu.kicad_sch", 139.7, 30.48, 50.8,
     [("VIN_SENSE", "input"), ("CAN_RX", "input"), ("RS485_RX", "input"), ("GPS_RX", "input"),
      ("GPS_PPS", "input"), ("ACC_INT1", "input"), ("ADC_ALERT", "input"), ("EXP_INT", "input"),
      ("I2C_SDA", "bidirectional"), ("I2C_SCL", "bidirectional")],
     [(n, "output") for n in RLY + DIM] + [("CAN_TX", "output"), ("RS485_TX", "output"),
                                           ("RS485_DE", "output"), ("GPS_TX", "output")]),
    ("Relays", "relays.kicad_sch", 266.7, 30.48, 45.72,
     [(n, "input") for n in RLY], [(n + "_FUSE", "output") for n in RLY]),
    ("Dimmers", "dimmers.kicad_sch", 266.7, 63.5, 45.72,
     [(n, "input") for n in DIM], [(n + "_FUSE", "output") for n in DIM]),
    ("Comms", "comms.kicad_sch", 266.7, 96.52, 45.72,
     [("CAN_TX", "input"), ("RS485_TX", "input"), ("RS485_DE", "input")],
     [("CAN_RX", "output"), ("RS485_RX", "output")]),
    ("Sensors", "sensors.kicad_sch", 50.8, 76.2, 50.8,
     [("GPS_TX", "input")] + [(n + "_FUSE", "input") for n in RLY + DIM],
     [("GPS_RX", "output"), ("GPS_PPS", "output"), ("ACC_INT1", "output"), ("ADC_ALERT", "output"),
      ("EXP_INT", "output"), ("I2C_SDA", "bidirectional"), ("I2C_SCL", "bidirectional")]),
]
LEAF = {
    "power.kicad_sch": ("Power", power_sheet),
    "mcu.kicad_sch": ("MCU", mcu_sheet),
    "comms.kicad_sch": ("Comms", comms_sheet),
    "sensors.kicad_sch": ("Sensors", sensors_sheet),
    "relay_channel.kicad_sch": ("Relay channel", relay_channel),
    "dimmer_channel.kicad_sch": ("Dimmer channel", dimmer_channel),
}
CHANNEL_INTERFACE = {"CTRL": "input", "FUSE_SENSE": "output"}


def interface_of(file):
    for name, f, *_rest in ROOT_SHEETS:
        if f == file:
            left, right = _rest[3], _rest[4]
            return dict(left + right)
    return CHANNEL_INTERFACE


# --------------------------------------------------------------------------- S-expression helpers
def S(*items):
    return [Sym(items[0])] + list(items[1:])


def num(v):
    return Sym(f"{round(v, 4):g}")


def at(x, y, a=0):
    return S("at", num(x), num(y), num(a))


def effects(justify=None, hide=False, size=1.27):
    e = S("effects", S("font", S("size", num(size), num(size))))
    if justify:
        e.append(S("justify", *[Sym(j) for j in justify.split()]))
    if hide:
        e.append(S("hide", Sym("yes")))
    return e


def yesno(b):
    return Sym("yes" if b else "no")


def wire(x1, y1, x2, y2, key):
    return S("wire", S("pts", S("xy", num(x1), num(y1)), S("xy", num(x2), num(y2))),
             S("stroke", S("width", num(0)), S("type", Sym("default"))), S("uuid", U(key)))


def label_node(kind, name, x, y, ox, oy, key, shape=None):
    # ox/oy: outward direction (schematic coords)
    if ox > 0:
        ang, just = 0, "left"
    elif ox < 0:
        ang, just = 180, "right"
    elif oy < 0:
        ang, just = 90, "left"
    else:
        ang, just = 270, "right"
    if kind == "label":
        n = S("label", name, at(x, y, ang), effects(just + " bottom" if ang in (0, 180) else just + " bottom"),
              S("uuid", U(key)))
    else:
        n = S("hierarchical_label", name, S("shape", Sym(shape)), at(x, y, ang), effects(just), S("uuid", U(key)))
    return n


def text_node(s, x, y, key, size=1.27):
    return S("text", s, S("exclude_from_sim", Sym("no")), at(x, y), effects("left top", size=size),
             S("uuid", U(key)))


def outward(angle):
    a = math.radians(angle)
    return round(-math.cos(a)), round(math.sin(a))


def label_len(name):
    return len(name) * 1.15 + 2.0


# --------------------------------------------------------------------------- symbol placement
class Ctx:
    def __init__(self):
        self.refcount = {}
        self.pwr = 0

    def next_ref(self, prefix):
        if prefix.startswith("#"):
            self.pwr += 1
            return f"{prefix}{self.pwr:03d}"
        self.refcount[prefix] = self.refcount.get(prefix, 0) + 1
        return f"{prefix}{self.refcount[prefix]}"


SYMCACHE = {}


def libsym(lib_id):
    if lib_id not in SYMCACHE:
        SYMCACHE[lib_id] = k.flat_symbol(lib_id)
    return SYMCACHE[lib_id]


def part_extent(part):
    s = libsym(part.lib_id)
    ps = k.pins(s)
    xs = [p["x"] for p in ps] + [-2.54, 2.54]
    ys = [-p["y"] for p in ps] + [-2.54, 2.54]
    l, r, t, b = min(xs), max(xs), min(ys), max(ys)
    ml = mr = mt = mb = 2.54
    for p in ps:
        net = part.pins.get(p["number"], NC)
        if net is None:
            continue
        ox, oy = outward(p["angle"])
        ext = G + (4.5 if net in POWER else label_len(net) + (2.5 if net else 0))
        if ox < 0:
            ml = max(ml, ext)
        elif ox > 0:
            mr = max(mr, ext)
        elif oy < 0:
            mt = max(mt, ext)
        else:
            mb = max(mb, ext)
    return l - ml - 3, r + mr + 3, t - mt - 4, b + mb + 4


def snap(v):
    return round(v / G) * G


def place_symbol(file, part, local_id, X, Y, refs, inst_paths, iface):
    """Return list of nodes: the symbol plus its stubs/labels/power symbols/no-connects."""
    s = libsym(part.lib_id)
    ps = k.pins(s)
    names = {p["number"] for p in ps}
    missing = names - set(part.pins)
    extra = set(part.pins) - names
    if missing or extra:
        raise SystemExit(f"{file} {part.lib_id}: pins missing {sorted(missing)} extra {sorted(extra)}")
    nodes = []
    key = f"{file}/{local_id}"
    sym = S("symbol", S("lib_id", part.lib_id), at(X, Y, 0), S("unit", Sym("1")),
            S("exclude_from_sim", Sym("no")),
            S("in_bom", k.first(s, "in_bom")[1] if k.first(s, "in_bom") else Sym("yes")),
            S("on_board", k.first(s, "on_board")[1] if k.first(s, "on_board") else Sym("yes")),
            S("dnp", Sym("no")), S("uuid", U(key)))
    for p in k.find(s, "property"):
        p = copy.deepcopy(p)
        a = k.first(p, "at")
        a[1], a[2] = num(X + float(a[1])), num(Y - float(a[2]))
        if p[1] == "Reference":
            p[2] = refs[0]
        elif p[1] == "Value":
            p[2] = part.value
        elif p[1] == "Footprint" and part.fp:
            p[2] = part.fp
        sym.append(p)
    extra_props = []
    if part.mpn:
        extra_props.append(("MPN", part.mpn))
    if part.note:
        extra_props.append(("Note", part.note))
    for nm, val in extra_props:
        sym.append(S("property", nm, val, at(X, Y), effects(hide=True)))
    for p in ps:
        sym.append(S("pin", p["number"], S("uuid", U(key, "pin", p["number"]))))
    inst = S("project", PROJECT)
    for path, ref in zip(inst_paths, refs):
        inst.append(S("path", path, S("reference", ref), S("unit", Sym("1"))))
    sym.append(S("instances", inst))
    nodes.append(sym)

    for p in ps:
        net = part.pins[p["number"]]
        px, py = X + p["x"], Y - p["y"]
        pkey = f"{key}/{p['number']}"
        if net is None:
            if p["type"] != "no_connect":
                nodes.append(S("no_connect", at(px, py)[:3], S("uuid", U(pkey, "nc"))))
            continue
        ox, oy = outward(p["angle"])
        ex, ey = px + ox * G, py + oy * G
        nodes.append(wire(px, py, ex, ey, pkey + "/w"))
        if net in POWER:
            nodes.append(("POWER", net, ex, ey, pkey, ox, oy))
        elif net in iface:
            nodes.append(label_node("hier", net, ex, ey, ox, oy, pkey + "/l", iface[net]))
        else:
            nodes.append(label_node("label", net, ex, ey, ox, oy, pkey + "/l"))
    return nodes


def power_symbol(net, x, y, key, ox, oy, refs, inst_paths):
    lib_id = POWER[net]
    s = libsym(lib_id)
    # GND hangs down, rails point up; rotate so the symbol body points away from the pin stub
    if net == "GND":
        rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[(ox, oy)]
    else:
        rot = {(0, -1): 0, (0, 1): 180, (1, 0): 270, (-1, 0): 90}[(ox, oy)]
    sym = S("symbol", S("lib_id", lib_id), at(x, y, rot), S("unit", Sym("1")),
            S("exclude_from_sim", Sym("no")), S("in_bom", Sym("no")), S("on_board", Sym("yes")),
            S("dnp", Sym("no")), S("uuid", U(key, "pwr")))
    for p in k.find(s, "property"):
        p = copy.deepcopy(p)
        a = k.first(p, "at")
        dx, dy = float(a[1]), -float(a[2])
        r = math.radians(-rot)
        rx, ry = dx * math.cos(r) - dy * math.sin(r), dx * math.sin(r) + dy * math.cos(r)
        a[1], a[2] = num(x + rx), num(y + ry)
        if p[1] == "Reference":
            p[2] = refs[0]
            if not k.first(p, "hide"):
                p.append(S("hide", Sym("yes")))
        sym.append(p)
    sym.append(S("pin", "1", S("uuid", U(key, "pwrpin"))))
    inst = S("project", PROJECT)
    for path, ref in zip(inst_paths, refs):
        inst.append(S("path", path, S("reference", ref), S("unit", Sym("1"))))
    sym.append(S("instances", inst))
    return sym


def sheet_header(file, title, paper):
    return [Sym("kicad_sch"), S("version", Sym("20250610")), S("generator", "eeschema"),
            S("generator_version", "10.0"), S("uuid", U("file", file)), S("paper", paper),
            S("title_block", S("title", title), S("date", DATE), S("rev", REV), S("company", "VanController"))]


def write_sch(file, tree):
    with open(os.path.join(OUT, file), "w", encoding="utf-8", newline="\n") as f:
        f.write(k.dump(tree) + "\n")


# --------------------------------------------------------------------------- build
ROOT_UUID = U("file", f"{PROJECT}.kicad_sch")


def sheet_symbol(name, file, x, y, w, left, right, parent_path, page, key, labelled):
    rows = max(len(left), len(right), 1)
    h = (rows + 1) * G
    su = U(key, "sheet", name)
    node = S("sheet", at(x, y)[:3], S("size", num(w), num(h)), S("exclude_from_sim", Sym("no")),
             S("in_bom", Sym("yes")), S("on_board", Sym("yes")), S("dnp", Sym("no")),
             S("fields_autoplaced", Sym("yes")),
             S("stroke", S("width", num(0.1524)), S("type", Sym("solid"))),
             S("fill", S("color", Sym("0"), Sym("0"), Sym("0"), Sym("0.0000"))),
             S("uuid", su),
             S("property", "Sheetname", name, at(x, y - 0.7116),
               S("effects", S("font", S("size", num(1.27), num(1.27)), S("bold", Sym("yes"))),
                 S("justify", Sym("left"), Sym("bottom")))),
             S("property", "Sheetfile", file, at(x, y + h + 0.5846), effects("left top")))
    extras = []
    for side, pins in (("L", left), ("R", right)):
        for i, (pn, shape) in enumerate(pins):
            py = y + (i + 1) * G
            px, ang, just = (x, 180, "left") if side == "L" else (x + w, 0, "right")
            node.append(S("pin", pn, Sym(shape), at(px, py, ang), S("uuid", U(su, "pin", pn)), effects(just)))
            ox = -1 if side == "L" else 1
            ex = px + ox * 2 * G
            extras.append(wire(px, py, ex, py, f"{su}/{pn}/w"))
            if labelled == "label":
                extras.append(label_node("label", pn, ex, py, ox, 0, f"{su}/{pn}/l"))
            else:
                extras.append(label_node("hier", labelled[pn][0], ex, py, ox, 0, f"{su}/{pn}/l", labelled[pn][1]))
    node.append(S("instances", S("project", PROJECT, S("path", parent_path, S("page", str(page))))))
    return node, extras, su


def build():
    ctx = Ctx()
    # ---- hierarchy: (file -> list of (instance path, page))
    page = 1
    root_nodes = sheet_header(f"{PROJECT}.kicad_sch", "VanController: ESP32-S3 12 V controller", "A3")
    root_nodes.append(S("lib_symbols"))
    instances = {}  # file -> [path]
    order = []
    sheet_uuid = {}
    for name, file, x, y, w, left, right in ROOT_SHEETS:
        page += 1
        node, extras, su = sheet_symbol(name, file, x, y, w, left, right, "/" + ROOT_UUID, page, "root", "label")
        root_nodes.append(node)
        root_nodes.extend(extras)
        sheet_uuid[name] = su
        path = f"/{ROOT_UUID}/{su}"
        if file in LEAF:
            instances.setdefault(file, []).append(path)
            order.append(file)
        else:
            # channel container sheet
            chfile, chname = ("relay_channel.kicad_sch", "Relay") if name == "Relays" else \
                ("dimmer_channel.kicad_sch", "Dimmer")
            nets_in = RLY if name == "Relays" else DIM
            cont = sheet_header(file, f"{name} (6 channels)", "A4")
            cont.append(S("lib_symbols"))
            for i in range(6):
                page += 1
                cx, cy = 76.2 + (i % 2) * 76.2, 38.1 + (i // 2) * 30.48
                lab = {"CTRL": (nets_in[i], "input"), "FUSE_SENSE": (nets_in[i] + "_FUSE", "output")}
                node, extras, csu = sheet_symbol(f"{chname}{i + 1}", chfile, cx, cy, 30.48,
                                                 [("CTRL", "input")], [("FUSE_SENSE", "output")],
                                                 path, page, file, lab)
                cont.append(node)
                cont.extend(extras)
                instances.setdefault(chfile, []).append(f"{path}/{csu}")
            cont.append(text_node(f"Six identical instances of {chfile}. Edit that file once to change every channel.",
                                  25.4, 20.32, file + "/note"))
            cont.append(S("embedded_fonts", Sym("no")))
            write_sch(file, cont)
            order.append(chfile)
    root_nodes.append(text_node(
        "VanController rev 0.2. 12 V vehicle controller: ESP32-S3, 6 fused relays, 6 fused PWM dimmers, CAN, RS485, "
        "GPS, accelerometer, 2 water-level inputs.\nSee DESIGN_SPEC.md for the GPIO map, I2C addresses and design notes.",
        50.8, 190.5, "root/note", 1.524))
    root_nodes.append(S("sheet_instances", S("path", "/", S("page", "1"))))
    root_nodes.append(S("embedded_fonts", Sym("no")))
    write_sch(f"{PROJECT}.kicad_sch", root_nodes)

    # ---- leaf sheets
    bom_notes = []
    for file in order:
        title, fn = LEAF[file]
        groups, notes = fn()
        paths = instances[file]
        iface = interface_of(file)
        placed = []
        y = 30.48
        x0, maxw = 20.32, 0
        rows = []
        for g in groups:
            row, x, rowh = [], x0, 0
            for part in g:
                l, r, t, b = part_extent(part)
                w = r - l
                if x + w > 390 and row:
                    rows.append(row)
                    row, x = [], x0
                row.append((part, snap(x - l), t, b))
                x += w
            rows.append(row)
        nodes, power_nodes = [], []
        local_seq = {}
        for row in rows:
            top = min(t for _, _, t, _ in row)
            bot = max(b for _, _, _, b in row)
            Y = snap(y - top)
            for part, X, _, _ in row:
                prefix = part.ref
                local_seq[prefix] = local_seq.get(prefix, 0) + 1
                local_id = f"{prefix}{local_seq[prefix]}"
                refs = [ctx.next_ref(prefix) for _ in paths]
                for n in place_symbol(file, part, local_id, X, Y, refs, paths, iface):
                    if isinstance(n, tuple):
                        _, net, ex, ey, pkey, ox, oy = n
                        prefs = [ctx.next_ref("#PWR") for _ in paths]
                        power_nodes.append(power_symbol(net, ex, ey, pkey, ox, oy, prefs, paths))
                    else:
                        nodes.append(n)
                if part.mpn or part.note:
                    bom_notes.append((refs, part.value, part.mpn, part.note))
            y = Y + bot + 5.08
        height = y + 20
        width = max(X for row in rows for _, X, _, _ in row) + 60
        paper = "A4" if width <= 287 and height <= 200 else "A3" if width <= 410 and height <= 287 else "A2"
        tree = sheet_header(file, title, paper)
        lib = S("lib_symbols")
        used = sorted({p.lib_id for g in groups for p in g} |
                      {POWER[n] for g in groups for p in g for n in p.pins.values() if n in POWER})
        for lid in used:
            lib.append(copy.deepcopy(libsym(lid)))
        tree.append(lib)
        tree.append(text_node(notes, 20.32, 15.24, file + "/note"))
        tree.extend(nodes)
        tree.extend(power_nodes)
        tree.append(S("embedded_fonts", Sym("no")))
        write_sch(file, tree)
        print(f"{file:28s} {len(paths)} inst, paper {paper}, {sum(len(g) for g in groups)} parts")
    return bom_notes


if __name__ == "__main__":
    build()
