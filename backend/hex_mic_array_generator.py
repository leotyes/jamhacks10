#!/usr/bin/env python3
"""
hex_mic_array_generator.py
==========================
Generates a KiCad netlist (.net) AND physical PCB layout (.kicad_pcb)
for a hexagonal six-microphone MEMS array wired to an STM32H7A3ZIT6Q MCU.

Architecture
------------
  ① build_circuit()        Pure-Python circuit dict — single source of truth.
  ② _write_netlist_skidl() SKiDL defines parts/nets and calls generate_netlist().
     _write_netlist_manual()  Fallback when SKiDL is not installed — identical output.
  ③ _write_kicad_pcb()     Standalone writer: hexagonal math + proper footprint
                            geometry (outlines, courtyard, silkscreen, pad positions).

Hexagonal geometry
------------------
  Six mics are placed at equal 60° increments around a central origin using:

      x = cx + r · cos(θ)
      y = cy − r · sin(θ)     ← minus because KiCad Y-axis points downward

  The MCU sits at a fixed offset to the right of the array.

Usage — standalone
------------------
  python hex_mic_array_generator.py [output_dir]

Usage — FastAPI / backend
-------------------------
  from hex_mic_array_generator import generate_hex_mic_board
  net_path, pcb_path = generate_hex_mic_board(output_dir="schematics")

Dependencies
------------
  Required : Python ≥ 3.9, pathlib, math (stdlib only for .kicad_pcb output)
  Optional : skidl  (pip install skidl)  — used for .net output;
             falls back to a manual KiCad netlist writer if absent.
"""

from __future__ import annotations

import math
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# SKiDL — imported lazily; the module loads cleanly even without it
# ─────────────────────────────────────────────────────────────────────────────
try:
    from skidl import Part, Pin, Net, SKIDL, generate_netlist, reset
    _SKIDL_OK = True
except ImportError:
    _SKIDL_OK = False


# =============================================================================
# ① CONFIGURATION
# =============================================================================

# ── Hexagonal array geometry ─────────────────────────────────────────────────
CENTER_X   = 100.0   # mm  geometric centre of the six-mic hex ring
CENTER_Y   = 100.0   # mm
HEX_RADIUS =  50.0   # mm  centre-to-mic radial distance

MCU_POS = (180.0, 100.0)   # mm  MCU placed to the right of the array

# Angles for the six hex vertices in standard-math convention.
# 90° = North (top of board), then clockwise in 60° steps.
# KiCad Y-axis points downward, so sin() is negated inside mic_position().
HEX_ANGLES_DEG = [90, 30, -30, -90, -150, 150]
MIC_IDS        = ["MIC_N", "MIC_NE", "MIC_SE", "MIC_S", "MIC_SW", "MIC_NW"]
NUM_MICS       = len(MIC_IDS)   # 6

# ── STM32H7A3ZIT6Q DFSDM pin assignments ─────────────────────────────────────
# Each mic has its own independent DATIN line; all six share one CKOUT clock.
MCU_CLK_PIN  = "PE9"    # DFSDM1_CKOUT   — LQFP-144 pad 31
MCU_VDD_PIN  = "VDD"    # 3.3 V supply   — LQFP-144 pad 19
MCU_GND_PIN  = "GND"    # Ground         — LQFP-144 pad 18
MCU_DAT_PINS = [
    "PC1",   # pad  9  DFSDM1_DATIN0 → MIC_N
    "PC3",   # pad 11  DFSDM1_DATIN1 → MIC_NE
    "PC5",   # pad 25  DFSDM1_DATIN2 → MIC_SE
    "PE4",   # pad 92  DFSDM1_DATIN3 → MIC_S
    "PE10",  # pad 32  DFSDM1_DATIN4 → MIC_SW
    "PE12",  # pad 34  DFSDM1_DATIN5 → MIC_NW
]

# ── KiCad footprint identifiers ───────────────────────────────────────────────
MCU_FOOTPRINT = "Package_QFP:LQFP-144_20x20mm_P0.5mm"
MIC_FOOTPRINT = "Package_LGA:VLGA-4_2x2.5mm_P1.65mm"

# ── Pin name → physical pad number maps ──────────────────────────────────────
# Used by both the manual .net writer and the .kicad_pcb pad-position logic.
MCU_PAD_MAP: dict[str, str] = {
    "VDD":  "19", "GND": "18", "VSS": "18",
    "PE9":  "31",
    "PC1":   "9", "PC3":  "11", "PC5":  "25",
    "PE4":  "92", "PE10": "32", "PE12": "34",
}
MIC_PAD_MAP: dict[str, str] = {
    "VDD": "1", "GND": "2", "CLK": "3", "DOUT": "4",
}


# =============================================================================
# ② GEOMETRY — explicit hexagonal placement math
# =============================================================================

def mic_position(angle_deg: float) -> tuple[float, float]:
    """
    Compute board-space (x, y) in mm for a microphone at *angle_deg*.

    Standard polar-to-Cartesian, adapted for KiCad's downward Y-axis:

        x = CENTER_X + HEX_RADIUS · cos(θ)
        y = CENTER_Y − HEX_RADIUS · sin(θ)   ← negated for KiCad Y-flip

    At 90° the mic appears directly above the centre; successive 60°
    decrements step clockwise: NE (30°) → SE (−30°) → S (−90°) etc.
    """
    theta = math.radians(angle_deg)
    x = CENTER_X + HEX_RADIUS * math.cos(theta)
    y = CENTER_Y - HEX_RADIUS * math.sin(theta)
    return (round(x, 3), round(y, 3))


def compute_positions() -> dict[str, tuple[float, float]]:
    """
    Return {component_id: (x_mm, y_mm)} for every component.

    Iterates over all six angles in 60° increments (0 → 5 × 60°) to
    build the symmetric hexagonal arrangement.
    """
    positions: dict[str, tuple[float, float]] = {"MCU": MCU_POS}

    for i, (mic_id, angle) in enumerate(zip(MIC_IDS, HEX_ANGLES_DEG)):
        # Explicit hex loop: i=0..5, angle = 90 + i*(-60) equivalent
        positions[mic_id] = mic_position(angle)

    return positions


# =============================================================================
# ③ CIRCUIT DEFINITION — single source of truth for both file writers
# =============================================================================

def build_circuit() -> dict:
    """
    Return a circuit dict:

        {
          "components": [
              {
                "id":             str,   # "MCU", "MIC_N", …
                "type":           str,   # "MCU" | "MIC"
                "hardware_model": str,   # exact model string
                "pins": {pin_name: net_name, …}
              },
              …
          ],
          "nets": [
              {"name": str, "connections": ["comp_id.pin_name", …]},
              …
          ],
        }

    Both the SKiDL writer and the manual .net / .kicad_pcb writers
    consume this dict directly, guaranteeing a single definition of
    the circuit topology.
    """
    components: list[dict] = []
    nets_acc:   dict[str, list[str]] = {}   # net_name → list of "comp.pin"

    def wire(comp_id: str, pin: str, net: str) -> None:
        """Register one pin-to-net connection in the accumulator."""
        nets_acc.setdefault(net, []).append(f"{comp_id}.{pin}")

    # ── MCU ──────────────────────────────────────────────────────────────────
    mcu_pins: dict[str, str] = {}

    for mcu_pin, net_name in [
        (MCU_VDD_PIN, "VCC_3V3"),
        (MCU_GND_PIN, "GND"),
        (MCU_CLK_PIN, "DFSDM1_CKOUT"),
    ]:
        mcu_pins[mcu_pin] = net_name
        wire("MCU", mcu_pin, net_name)

    # One dedicated data net per mic, mirrored on both the MCU and the mic
    for i, dat_pin in enumerate(MCU_DAT_PINS):
        net_name = f"DFSDM1_DATIN{i}"
        mcu_pins[dat_pin] = net_name
        wire("MCU", dat_pin, net_name)

    components.append({
        "id":             "MCU",
        "type":           "MCU",
        "hardware_model": "STM32H7A3ZIT6Q",
        "pins":           mcu_pins,
    })

    # ── Six MP34DT01-M microphones ────────────────────────────────────────────
    for i, mic_id in enumerate(MIC_IDS):
        dat_net = f"DFSDM1_DATIN{i}"
        mic_pins: dict[str, str] = {
            "VDD":  "VCC_3V3",
            "GND":  "GND",
            "CLK":  "DFSDM1_CKOUT",   # shared clock bus
            "DOUT": dat_net,           # individual data line
        }
        for pin, net_name in mic_pins.items():
            wire(mic_id, pin, net_name)

        components.append({
            "id":             mic_id,
            "type":           "MIC",
            "hardware_model": "MP34DT01-M",
            "pins":           mic_pins,
        })

    nets = [
        {"name": name, "connections": conns}
        for name, conns in nets_acc.items()
    ]
    return {"components": components, "nets": nets}


# =============================================================================
# ④a .net WRITER — SKiDL path (primary)
# =============================================================================

def _write_netlist_skidl(circuit: dict, output_path: str) -> bool:
    """
    Use SKiDL to define parts inline (no KiCad library files required),
    wire them into nets, and call generate_netlist() to write the .net.

    Returns True on success, False if SKiDL is unavailable or raises.
    """
    if not _SKIDL_OK:
        return False

    try:
        reset()   # clear any residual SKiDL state from previous calls

        # ── Part templates (defined inline with tool=SKIDL) ───────────────────
        # Defining parts inline means the script has zero dependency on KiCad
        # library files being installed on the host machine.

        mcu_tmpl = Part(
            name      = "STM32H7A3ZIT6Q",
            tool      = SKIDL,
            footprint = MCU_FOOTPRINT,
            pins      = [
                Pin(num="19",  name="VDD",   func=Pin.types.PWRIN),   # 3.3 V
                Pin(num="18",  name="GND",   func=Pin.types.PWRIN),   # Ground
                Pin(num="31",  name="PE9",   func=Pin.types.BIDIR),   # DFSDM1_CKOUT
                Pin(num="9",   name="PC1",   func=Pin.types.BIDIR),   # DFSDM1_DATIN0
                Pin(num="11",  name="PC3",   func=Pin.types.BIDIR),   # DFSDM1_DATIN1
                Pin(num="25",  name="PC5",   func=Pin.types.BIDIR),   # DFSDM1_DATIN2
                Pin(num="92",  name="PE4",   func=Pin.types.BIDIR),   # DFSDM1_DATIN3
                Pin(num="32",  name="PE10",  func=Pin.types.BIDIR),   # DFSDM1_DATIN4
                Pin(num="34",  name="PE12",  func=Pin.types.BIDIR),   # DFSDM1_DATIN5
            ],
        )

        mic_tmpl = Part(
            name      = "MP34DT01-M",
            tool      = SKIDL,
            footprint = MIC_FOOTPRINT,
            pins      = [
                Pin(num="1", name="VDD",  func=Pin.types.PWRIN),
                Pin(num="2", name="GND",  func=Pin.types.PWRIN),
                Pin(num="3", name="CLK",  func=Pin.types.INPUT),
                Pin(num="4", name="DOUT", func=Pin.types.OUTPUT),
            ],
        )

        # ── Instantiate components ────────────────────────────────────────────
        mcu  = mcu_tmpl(ref="U1")
        mics = [mic_tmpl(ref=f"MIC{i + 1}") for i in range(NUM_MICS)]

        # ── Create nets ───────────────────────────────────────────────────────
        vcc      = Net("VCC_3V3")
        gnd      = Net("GND")
        clk      = Net("DFSDM1_CKOUT")
        dat_nets = [Net(f"DFSDM1_DATIN{i}") for i in range(NUM_MICS)]

        # ── Wire MCU power and clock ──────────────────────────────────────────
        mcu["VDD"] += vcc
        mcu["GND"] += gnd
        mcu["PE9"] += clk   # DFSDM1_CKOUT — shared clock to all six mics

        # ── Wire MCU data pins: each mic gets its own unique GPIO channel ─────
        # MCU_DAT_PINS = [PC1, PC3, PC5, PE4, PE10, PE12] → DATIN0..5
        # dat_nets[i] is a distinct Net, so no two mics share a data line.
        for i, dat_pin in enumerate(MCU_DAT_PINS):
            mcu[dat_pin] += dat_nets[i]

        # ── Wire each microphone in ring order (N→NE→SE→S→SW→NW) ────────────
        # Connecting VDD/GND sequentially around the perimeter keeps the
        # ratsnest as a ring rather than a star, eliminating criss-crossing
        # airwires across the board centre.
        for i, mic in enumerate(mics):
            mic["VDD"]  += vcc           # ring order: N first, NW last
            mic["GND"]  += gnd           # same sequential order
            mic["CLK"]  += clk           # shared DFSDM1_CKOUT clock bus
            mic["DOUT"] += dat_nets[i]   # unique: DATIN0..5, one per mic

        # ── Generate KiCad .net ───────────────────────────────────────────────
        generate_netlist(file_=output_path)
        print(f"[SKiDL]   .net written  → {output_path}")
        return True

    except Exception as exc:
        print(f"[SKiDL]   Failed ({exc}) — falling back to manual writer")
        return False


# =============================================================================
# ④b .net WRITER — manual fallback (pure Python, no SKiDL)
# =============================================================================

def _write_netlist_manual(circuit: dict, output_path: str) -> None:
    """
    Write a KiCad-format .net file directly from the circuit dict.
    Output is equivalent to SKiDL's generate_netlist() for this circuit.
    """
    fp_map: dict[str, str] = {
        "STM32H7A3ZIT6Q": MCU_FOOTPRINT,
        "MP34DT01-M":     MIC_FOOTPRINT,
    }
    pad_map: dict[str, dict[str, str]] = {
        "STM32H7A3ZIT6Q": MCU_PAD_MAP,
        "MP34DT01-M":     MIC_PAD_MAP,
    }
    hw_by_id = {c["id"]: c["hardware_model"] for c in circuit["components"]}

    lines: list[str] = ["(export (version D)"]

    # Component list
    lines.append("  (components")
    for comp in circuit["components"]:
        hw = comp["hardware_model"]
        fp = fp_map.get(hw, "")
        lines.append(f'    (comp (ref "{comp["id"]}")')
        lines.append(f'      (value "{hw}")')
        lines.append(f'      (footprint "{fp}")')
        lines.append( '    )')
    lines.append("  )")

    # Net list with physical pad numbers
    lines.append("  (nets")
    for i, net in enumerate(circuit["nets"]):
        lines.append(f'    (net (code "{i + 1}") (name "{net["name"]}")')
        for node in net["connections"]:
            comp_id, pin_name = node.split(".", 1)
            hw  = hw_by_id.get(comp_id, "")
            pad = pad_map.get(hw, {}).get(pin_name, pin_name)
            lines.append(f'      (node (ref "{comp_id}") (pin "{pad}"))')
        lines.append('    )')
    lines.append("  )")
    lines.append(")")

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"[manual]  .net written  → {output_path}")


# =============================================================================
# ⑤ FOOTPRINT GEOMETRY — pad positions and chip outline graphics
# =============================================================================

def _lqfp144_pad_xy(pad_num: int) -> tuple[float, float]:
    """
    Return the (x, y) mm offset from footprint origin for LQFP-144 pad N.

    Physical layout (36 pads per side, 0.5 mm pitch, ±8.75 mm span,
    pad centres at ±11.5 mm from chip centre):

        Side A  pins   1– 36  bottom row  left  → right
        Side B  pins  37– 72  right col   top   → bottom
        Side C  pins  73–108  top row     right → left
        Side D  pins 109–144  left col    bottom → top
    """
    SPAN  = 8.75    # half-span: (36−1) × 0.5 / 2
    PITCH = 0.5     # mm between pad centres
    DIST  = 11.5    # mm from chip centre to pad centre (body/2 + lead)

    if 1 <= pad_num <= 36:         # bottom row, left → right
        return (round(-SPAN + (pad_num -   1) * PITCH, 3),  DIST)
    elif 37 <= pad_num <= 72:      # right column, top → bottom
        return ( DIST, round( SPAN - (pad_num -  37) * PITCH, 3))
    elif 73 <= pad_num <= 108:     # top row, right → left
        return (round( SPAN - (pad_num -  73) * PITCH, 3), -DIST)
    elif 109 <= pad_num <= 144:    # left column, bottom → top
        return (-DIST, round(-SPAN + (pad_num - 109) * PITCH, 3))
    return (0.0, 0.0)


def _vlga4_pad_xy(pad_num: int) -> tuple[float, float]:
    """
    (x, y) mm offset for VLGA-4 2×2 grid.

        Pad 1 (VDD)  top-left   │  Pad 2 (GND)  top-right
        ─────────────────────────┼──────────────────────────
        Pad 3 (CLK)  btm-left   │  Pad 4 (DOUT) btm-right
    """
    table = {
        1: (-0.55, -0.825),
        2: ( 0.55, -0.825),
        3: (-0.55,  0.825),
        4: ( 0.55,  0.825),
    }
    return table.get(pad_num, (0.0, 0.0))


def _pad_xy(hw: str, pad_num: int) -> tuple[float, float]:
    """Dispatch to the correct pad-position function for this hardware model."""
    if hw == "STM32H7A3ZIT6Q":
        return _lqfp144_pad_xy(pad_num)
    return _vlga4_pad_xy(pad_num)   # MP34DT01-M and any other LGA-4


def _pad_size_rot(hw: str, pad_num: int) -> tuple[float, float, int]:
    """
    Return (width_mm, height_mm, rotation_deg) for a pad.

    LQFP-144 side-column pads (right: 37–72, left: 109–144) are rotated
    90° so their long axis runs horizontally, matching the physical leads.
    Top/bottom row pads are upright (rotation 0°).
    """
    if hw == "STM32H7A3ZIT6Q":
        if 37 <= pad_num <= 72 or 109 <= pad_num <= 144:
            return (0.3, 1.5, 90)   # side column — long axis horizontal
        return (0.3, 1.5, 0)        # top/bottom row — long axis vertical
    return (0.4, 0.65, 0)           # VLGA-4 mic pad


def _emit_rect(lines: list[str], x1: float, y1: float,
               x2: float, y2: float, layer: str, w: float) -> None:
    """Append four fp_line segments forming a closed rectangle on *layer*."""
    corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    for i in range(4):
        ax, ay = corners[i]
        bx, by = corners[(i + 1) % 4]
        lines.append(
            f'    (fp_line (start {ax} {ay}) (end {bx} {by})'
            f' (layer "{layer}") (width {w}))'
        )


def _emit_footprint_graphics(lines: list[str], hw: str) -> None:
    """
    Emit the chip-outline graphics that KiCad renders as the visible
    component body: F.Fab (fabrication outline), F.SilkS (silkscreen),
    and F.Courtyard (keep-out zone).

    Without these, KiCad shows only pad dots with no component shape.
    """
    if hw == "STM32H7A3ZIT6Q":
        # Body on F.Fab: 20 × 20 mm square centred at footprint origin
        _emit_rect(lines, -10, -10, 10, 10, "F.Fab", 0.10)
        # Pin-1 corner marker (L-shaped notch at bottom-left of body)
        lines.append('    (fp_line (start -10 9)  (end -10 10) (layer "F.Fab") (width 0.2))')
        lines.append('    (fp_line (start -10 10) (end  -9 10) (layer "F.Fab") (width 0.2))')
        # Courtyard: encloses all 144 pads (centre ±11.5 mm + 2 mm margin)
        _emit_rect(lines, -13.5, -13.5, 13.5, 13.5, "F.Courtyard", 0.05)
        # Silkscreen: chip body outline with slight clearance from pads
        _emit_rect(lines, -10.5, -10.5, 10.5, 10.5, "F.SilkS", 0.12)
    else:
        # MP34DT01-M VLGA-4: body 2 × 2.5 mm
        _emit_rect(lines, -1.0, -1.25, 1.0,  1.25, "F.Fab",      0.10)
        _emit_rect(lines, -1.5, -1.75, 1.5,  1.75, "F.Courtyard", 0.05)
        _emit_rect(lines, -1.0, -1.25, 1.0,  1.25, "F.SilkS",    0.12)


def _emit_all_pads(
    lines:     list[str],
    hw:        str,
    pins:      dict[str, str],
    pmap:      dict[str, str],
    net_index: dict[str, int],
) -> None:
    """
    Emit EVERY physical pad of the footprint — connected and unconnected.

    Connected pads carry their net assignment so ratsnest lines appear.
    Unconnected pads are written bare (no net sub-element) so the full
    144-pin LQFP ring or 4-pin LGA grid renders in KiCad rather than just
    the handful of GPIO pins that are actively wired.
    """
    # Build pad_number_str → net_name from the component's connected pins
    pad_to_net: dict[str, str] = {}
    for pin_name, net_name in pins.items():
        pad_str = pmap.get(pin_name, pin_name)
        if pad_str.isdigit():
            pad_to_net[pad_str] = net_name

    total = 144 if hw == "STM32H7A3ZIT6Q" else 4

    for pad_num in range(1, total + 1):
        pad_str  = str(pad_num)
        net_name = pad_to_net.get(pad_str, "")
        net_code = net_index.get(net_name, 0) if net_name else 0

        px, py       = _pad_xy(hw, pad_num)
        pw, ph, prot = _pad_size_rot(hw, pad_num)
        rot_str      = f" {prot}" if prot else ""

        lines.append(
            f'    (pad "{pad_str}" smd rect'
            f' (at {px} {py}{rot_str}) (size {pw} {ph})'
            f' (layers "F.Cu" "F.Paste" "F.Mask")'
        )
        if net_code:
            lines.append(f'      (net {net_code} "{net_name}")')
        lines.append('    )')


# =============================================================================
# ⑥ .kicad_pcb WRITER
# =============================================================================

def _write_kicad_pcb(
    circuit:   dict,
    positions: dict[str, tuple[float, float]],
    output_path: str,
) -> None:
    """
    Write a complete .kicad_pcb file with:
      • Layer stack declaration
      • Net declarations (one per electrical signal)
      • One footprint per component, each containing:
          – Correct board-space placement (at x y)
          – F.Fab / F.SilkS / F.Courtyard outlines (visible chip body)
          – Per-pad positions computed from the footprint geometry
          – Net assignments on each connected pad
      • Board outline (Edge.Cuts) sized to the component bounding box

    Import the result into KiCad PCBnew, run FreeRouting or manual
    routing, and adjust clearances as needed for production.
    """
    fp_map: dict[str, str] = {
        "STM32H7A3ZIT6Q": MCU_FOOTPRINT,
        "MP34DT01-M":     MIC_FOOTPRINT,
    }
    pad_map: dict[str, dict[str, str]] = {
        "STM32H7A3ZIT6Q": MCU_PAD_MAP,
        "MP34DT01-M":     MIC_PAD_MAP,
    }

    # Net code index (1-based, net 0 = unconnected)
    net_index: dict[str, int] = {
        net["name"]: i + 1 for i, net in enumerate(circuit["nets"])
    }

    # Board outline: bounding box of all component positions + 20 mm margin
    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    margin = 20.0
    x_min, x_max = min(xs) - margin, max(xs) + margin
    y_min, y_max = min(ys) - margin, max(ys) + margin

    L: list[str] = []   # output line buffer

    # ── File header ───────────────────────────────────────────────────────────
    L.append('(kicad_pcb (version 20221018) (generator hex_mic_array_generator)')
    L.append('')
    L.append('  (general')
    L.append('    (thickness 1.6)')
    L.append('  )')
    L.append('')
    L.append('  (paper "A3")')
    L.append('')

    # ── Layer stack ───────────────────────────────────────────────────────────
    L.append('  (layers')
    for num, name, ltype in [
        ( 0,  "F.Cu",        "signal"),
        (31,  "B.Cu",        "signal"),
        (32,  "B.Adhes",     "user"),
        (33,  "F.Adhes",     "user"),
        (34,  "B.Paste",     "user"),
        (35,  "F.Paste",     "user"),
        (36,  "B.SilkS",     "user"),
        (37,  "F.SilkS",     "user"),
        (38,  "B.Mask",      "user"),
        (39,  "F.Mask",      "user"),
        (44,  "Edge.Cuts",   "user"),
        (45,  "Margin",      "user"),
        (49,  "F.Courtyard", "user"),
        (50,  "B.Courtyard", "user"),
        (51,  "F.Fab",       "user"),
        (52,  "B.Fab",       "user"),
    ]:
        L.append(f'    ({num} "{name}" {ltype})')
    L.append('  )')
    L.append('')

    # ── Net declarations ──────────────────────────────────────────────────────
    L.append('  (net 0 "")')
    for net in circuit["nets"]:
        code = net_index[net["name"]]
        L.append(f'  (net {code} "{net["name"]}")')
    L.append('')

    # ── Footprints ────────────────────────────────────────────────────────────
    for comp in circuit["components"]:
        cid  = comp["id"]
        hw   = comp["hardware_model"]
        fp   = fp_map.get(hw, "")
        pins = comp.get("pins", {})
        x, y = positions.get(cid, (CENTER_X, CENTER_Y))
        pmap = pad_map.get(hw, {})

        if not fp:
            print(f"  WARNING: no footprint for {cid} ({hw}) — skipped")
            continue

        # Dynamic rotation: each mic rotates i×60° so its connector edge
        # steps progressively inward around the ring.  MCU stays at 0°.
        if cid in MIC_IDS:
            rotation = MIC_IDS.index(cid) * 60
        else:
            rotation = 0

        # Footprint header
        L.append(f'  (footprint "{fp}"')
        L.append(f'    (layer "F.Cu")')
        L.append(f'    (at {x} {y} {rotation})')
        L.append(f'    (property "Reference" "{cid}" (at 0 -3) (layer "F.SilkS"))')
        L.append(f'    (property "Value" "{hw}" (at 0 3) (layer "F.Fab"))')

        # Chip outline graphics — these are what makes chips look like chips
        _emit_footprint_graphics(L, hw)

        # All physical pads (connected + unconnected) — full 144-pin LQFP ring
        # or 4-pin LGA grid so the chip renders completely in KiCad.
        _emit_all_pads(L, hw, pins, pmap, net_index)

        L.append('  )')
        L.append('')

    # ── Board outline — Edge.Cuts rectangle ───────────────────────────────────
    corners = [
        (x_min, y_min), (x_max, y_min),
        (x_max, y_max), (x_min, y_max),
    ]
    for i in range(4):
        ax, ay = corners[i]
        bx, by = corners[(i + 1) % 4]
        L.append(
            f'  (gr_line (start {ax} {ay}) (end {bx} {by})'
            f' (layer "Edge.Cuts") (width 0.05))'
        )

    L.append('')
    L.append(')')   # close kicad_pcb

    Path(output_path).write_text("\n".join(L), encoding="utf-8")
    print(f"[PCB]     .kicad_pcb written → {output_path}")


# =============================================================================
# ⑦ PUBLIC API — call this from FastAPI or any other backend
# =============================================================================

def generate_hex_mic_board(
    output_dir: str = "schematics",
    uid: Optional[str] = None,
) -> tuple[str, str]:
    """
    Full pipeline: build circuit → write .net → write .kicad_pcb.

    Parameters
    ----------
    output_dir : str
        Directory where both output files are written (created if absent).
    uid : str, optional
        Unique filename suffix.  Auto-generated (UUID 8-char hex) if omitted.

    Returns
    -------
    (net_path, pcb_path)
        Absolute paths of the two generated files.
    """
    os.makedirs(output_dir, exist_ok=True)
    suffix   = uid or uuid.uuid4().hex[:8]
    net_path = os.path.join(output_dir, f"hex_mic_{suffix}.net")
    pcb_path = os.path.join(output_dir, f"hex_mic_{suffix}.kicad_pcb")

    # ── Build shared circuit representation ───────────────────────────────────
    circuit   = build_circuit()
    positions = compute_positions()

    # Print placement summary for diagnostics
    print(f"\n[hex_mic] Hexagonal array — centre ({CENTER_X}, {CENTER_Y}) mm,"
          f" radius {HEX_RADIUS} mm")
    print(f"[hex_mic] MCU at {MCU_POS} mm")
    print("[hex_mic] Mic positions:")
    for i, (mic_id, angle) in enumerate(zip(MIC_IDS, HEX_ANGLES_DEG)):
        x, y = positions[mic_id]
        print(f"  [{i}] {mic_id:<8s}  θ={angle:+4d}°"
              f"  → ({x:7.2f}, {y:7.2f}) mm"
              f"  data={MCU_DAT_PINS[i]}")

    # ── Netlist (.net) ────────────────────────────────────────────────────────
    skidl_ok = _write_netlist_skidl(circuit, net_path)
    if not skidl_ok:
        print("[SKiDL]   Not available — using built-in manual writer")
        _write_netlist_manual(circuit, net_path)

    # ── Board layout (.kicad_pcb) ─────────────────────────────────────────────
    _write_kicad_pcb(circuit, positions, pcb_path)

    return (os.path.abspath(net_path), os.path.abspath(pcb_path))


# =============================================================================
# ⑧ ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    out_dir  = sys.argv[1] if len(sys.argv) > 1 else "schematics"
    net, pcb = generate_hex_mic_board(output_dir=out_dir)

    print()
    print("=" * 64)
    print(f"  Netlist      : {net}")
    print(f"  PCB layout   : {pcb}")
    print("=" * 64)
    print()
    print("  Open the .kicad_pcb in KiCad PCBnew to inspect placement.")
    print("  Run FreeRouting or route traces manually.")
    print("  Import the .net into KiCad Schematic to annotate the design.")
