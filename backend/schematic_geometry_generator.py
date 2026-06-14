"""
kicad_generator.py

Takes a production netlist (same schema as schematic_generator.py) plus a CV result dict,
asks an LLM to infer component placement geometry from the CV description, then writes a
.kicad_pcb file with footprints pre-positioned and nets assigned.

No manual routing — import into KiCad and run FreeRouting or route by hand.
"""

import json
import math
import os
from pathlib import Path
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))

# ── Footprint map (same as schematic_generator.py) ───────────────────────────
FOOTPRINT_MAP = {
    "STM32H7A3ZIT6Q":               "Package_QFP:LQFP-144_20x20mm_P0.5mm",
    "NUCLEO-H7A3ZI-Q":              "Package_QFP:LQFP-144_20x20mm_P0.5mm",
    "MP34DT01-M":                   "Package_LGA:VLGA-4_2x2.5mm_P1.65mm",
    "Adafruit 4346 PDM Microphone": "Package_LGA:VLGA-4_2x2.5mm_P1.65mm",
}

# ── Pin maps (same as schematic_generator.py) ────────────────────────────────
STM32H7A3ZIT6Q_PIN_MAP: dict[str, str] = {
    "VBAT":"1","PC13":"2","PC14":"3","PC15":"4","PH0":"5","PH1":"6","NRST":"7",
    "PC0":"8","PC1":"9","PC2":"10","PC3":"11","VSSA":"12","VDDA":"13",
    "PA0":"14","PA1":"15","PA2":"16","PA3":"17","VSS":"18","VDD":"19",
    "PA4":"20","PA5":"21","PA6":"22","PA7":"23","PC4":"24","PC5":"25",
    "PB0":"26","PB1":"27","PB2":"28","PE7":"29","PE8":"30","PE9":"31",
    "PE10":"32","PE11":"33","PE12":"34","PE13":"35","PE14":"36","PE15":"37",
    "PB10":"38","PB11":"39","VCAP":"40","PB12":"41","PB13":"42","PB14":"43",
    "PB15":"44","PD8":"45","PD9":"46","PD10":"47","PD11":"48","PD12":"49",
    "PD13":"50","PD14":"51","PD15":"52","PC6":"53","PC7":"54","PC8":"55",
    "PC9":"56","PA8":"57","PA9":"58","PA10":"59","PA11":"60","PA12":"61",
    "PA13":"62","VDD_2":"63","VSS_2":"64","PA14":"65","PA15":"66",
    "PC10":"67","PC11":"68","PC12":"69","PD0":"70","PD1":"71","PD2":"72",
    "PD3":"73","PD4":"74","PD5":"75","PD6":"76","PD7":"77","PB3":"78",
    "PB4":"79","PB5":"80","PB6":"81","PB7":"82","BOOT0":"83","PB8":"84",
    "PB9":"85","PE0":"86","PE1":"87","VSS_3":"88","VDD_3":"89","PE2":"90",
    "PE3":"91","PE4":"92","PE5":"93","PE6":"94","VBAT_2":"95","PI8":"96",
    "PC13_2":"97","PI9":"98","PI10":"99","PI11":"100","PH2":"101","PH3":"102",
    "PH4":"103","PH5":"104","PH6":"105","PH7":"106","PH8":"107","PH9":"108",
    "PH10":"109","PH11":"110","PH12":"111","VDD_4":"112","VSS_4":"113",
    "PH13":"114","PH14":"115","PH15":"116","PI0":"117","PI1":"118","PI2":"119",
    "PI3":"120","PI4":"121","PI5":"122","PI6":"123","PI7":"124","VDD_5":"125",
    "VSS_5":"126","PF0":"127","PF1":"128","PF2":"129","PF3":"130","PF4":"131",
    "PF5":"132","VDD_6":"133","VSS_6":"134","PF6":"135","PF7":"136","PF8":"137",
    "PF9":"138","PF10":"139","PG0":"140","PG1":"141","PE7_2":"142",
    "PE8_2":"143","VSS_7":"144",
    # GPIO aliases
    "GND":"18","PC1":"9","PC3":"11","PC5":"25","PE4":"92",
    "PE9":"31","PE10":"32","PE12":"34",
}

MP34DT01M_PIN_MAP: dict[str, str] = {
    "VDD":"1","GND":"2","CLK":"3","DOUT":"4",
}

ADAFRUIT4346_PIN_MAP: dict[str, str] = {
    "VDD":"1","GND":"2","CLK":"3","DAT":"4",
}

# NUCLEO board exposes GPIO names identical to the bare MCU, plus "3V3" which
# is the 3.3 V header rail — routes to LQFP-144 pad 19 (VDD).
NUCLEO_H7A3ZI_Q_PIN_MAP: dict[str, str] = {
    **STM32H7A3ZIT6Q_PIN_MAP,
    "3V3": "19",
}

_PIN_LOOKUP: dict[str, dict[str, str]] = {
    "STM32H7A3ZIT6Q":               STM32H7A3ZIT6Q_PIN_MAP,
    "MP34DT01-M":                   MP34DT01M_PIN_MAP,
    "Adafruit 4346 PDM Microphone": ADAFRUIT4346_PIN_MAP,
    "NUCLEO-H7A3ZI-Q":              NUCLEO_H7A3ZI_Q_PIN_MAP,
}


def _resolve_pin(hardware_model: str, pin_name: str) -> str:
    lookup = _PIN_LOOKUP.get(hardware_model)
    if not lookup:
        return pin_name
    resolved = lookup.get(pin_name)
    if resolved is None:
        print(f"  WARNING: no pad mapping for {hardware_model} pin '{pin_name}' — left as-is")
        return pin_name
    return resolved


# ── Footprint geometry ────────────────────────────────────────────────────────

def _lqfp144_pad_xy(pad_num: int) -> tuple[float, float]:
    """(x, y) mm offset from footprint origin for LQFP-144 pad (1-indexed)."""
    SPAN  = 8.75   # ±8.75 mm: 36 pads × 0.5 mm pitch centred
    PITCH = 0.5
    DIST  = 11.5   # pad-centre distance from chip centre

    if 1 <= pad_num <= 36:       # bottom row, left → right
        return (round(-SPAN + (pad_num - 1) * PITCH, 3), DIST)
    elif 37 <= pad_num <= 72:    # right column, top → bottom
        return (DIST, round(SPAN - (pad_num - 37) * PITCH, 3))
    elif 73 <= pad_num <= 108:   # top row, right → left
        return (round(SPAN - (pad_num - 73) * PITCH, 3), -DIST)
    elif 109 <= pad_num <= 144:  # left column, bottom → top
        return (-DIST, round(-SPAN + (pad_num - 109) * PITCH, 3))
    return (0.0, 0.0)


def _vlga4_pad_xy(pad_num: int) -> tuple[float, float]:
    """(x, y) mm offset for VLGA-4 2×2 pad grid."""
    positions = {1: (-0.55, -0.825), 2: (0.55, -0.825),
                 3: (-0.55,  0.825), 4: (0.55,  0.825)}
    return positions.get(pad_num, (0.0, 0.0))


_LQFP_MODELS  = ("STM32H7A3ZIT6Q", "NUCLEO-H7A3ZI-Q")
_LGA4_MODELS  = ("MP34DT01-M", "Adafruit 4346 PDM Microphone")
_HEX_MIC_IDS  = ["HEX_N", "HEX_NE", "HEX_SE", "HEX_S", "HEX_SW", "HEX_NW"]
_HEX_DAT_PINS = ["PC1", "PC3", "PC5", "PE4", "PE10", "PE12"]


def _pad_xy(hardware_model: str, pad_num: int) -> tuple[float, float]:
    if hardware_model in _LQFP_MODELS:
        return _lqfp144_pad_xy(pad_num)
    if hardware_model in _LGA4_MODELS:
        return _vlga4_pad_xy(pad_num)
    return (0.0, 0.0)


def _pad_size_rot(hardware_model: str, pad_num: int) -> tuple[float, float, int]:
    """Return (width_mm, height_mm, rotation_deg)."""
    if hardware_model in _LQFP_MODELS:
        # Left/right columns: rotate 90° so long axis is horizontal
        if 37 <= pad_num <= 72 or 109 <= pad_num <= 144:
            return (0.3, 1.5, 90)
        return (0.3, 1.5, 0)
    if hardware_model in _LGA4_MODELS:
        return (0.4, 0.65, 0)
    return (0.5, 0.5, 0)


def _emit_rect(lines: list[str], x1: float, y1: float, x2: float, y2: float,
               layer: str, width: float) -> None:
    corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    for i in range(4):
        ax, ay = corners[i]
        bx, by = corners[(i + 1) % 4]
        lines.append(f'    (fp_line (start {ax} {ay}) (end {bx} {by}) (layer "{layer}") (width {width}))')


def _emit_fp_graphics(lines: list[str], hardware_model: str) -> None:
    """Emit F.Fab, F.Courtyard, and F.SilkS outlines for the footprint."""
    if hardware_model in _LQFP_MODELS:
        # Chip body on F.Fab (20 × 20 mm) — same outline for bare MCU and Nucleo
        _emit_rect(lines, -10, -10, 10, 10, "F.Fab", 0.1)
        # Pin-1 corner marker on F.Fab
        lines.append('    (fp_line (start -10 9) (end -10 10) (layer "F.Fab") (width 0.2))')
        lines.append('    (fp_line (start -10 10) (end -9 10) (layer "F.Fab") (width 0.2))')
        # Courtyard (encloses all 144 pads)
        _emit_rect(lines, -13.5, -13.5, 13.5, 13.5, "F.CrtYd", 0.05)
        # Silkscreen body outline
        _emit_rect(lines, -10.5, -10.5, 10.5, 10.5, "F.SilkS", 0.12)
    elif hardware_model in _LGA4_MODELS:
        # Chip body on F.Fab (2 × 2.5 mm)
        _emit_rect(lines, -1.0, -1.25, 1.0, 1.25, "F.Fab", 0.1)
        # Courtyard
        _emit_rect(lines, -1.5, -1.75, 1.5, 1.75, "F.CrtYd", 0.05)
        # Silkscreen
        _emit_rect(lines, -1.0, -1.25, 1.0, 1.25, "F.SilkS", 0.12)


# ── LLM geometry inference ────────────────────────────────────────────────────

def infer_placement(cv_result: dict, components: list[dict]) -> dict[str, tuple[float, float]]:
    """
    Ask the LLM to estimate (x, y) positions in mm for each component,
    given the CV circuit description and component list.

    Returns {component_id: (x_mm, y_mm)}
    """
    comp_ids = [c["id"] for c in components]
    comp_types = {c["id"]: c.get("type", "") for c in components}

    prompt = f"""You are a PCB layout engineer. Given a CV description of a physical circuit and a list of components, estimate reasonable (x, y) placement coordinates in millimeters for a KiCad PCB layout.

CV circuit description:
{json.dumps(cv_result.get("circuit_description", ""), indent=2)}

Component list (id → type):
{json.dumps(comp_types, indent=2)}

Rules:
- Place the board origin at (0, 0), use positive coordinates only.
- If the CV description implies a geometric array (e.g. hexagonal mic array), place components in that geometry. Use a radius of 30mm for mic arrays unless the description implies otherwise.
- Place the MCU (type MCU or MCU_BOARD) offset from the array center, e.g. at (80, 50) for a hex array centered at (50, 50).
- Keep components far enough apart to avoid overlap: mics need ~10mm clearance, MCU needs ~25mm clearance.
- Return ONLY a JSON object mapping component id to [x, y] in mm. No explanation, no markdown fences.

Example output format:
{{"HEX_N": [50, 20], "HEX_NE": [76, 35], "U1": [120, 50]}}

Component ids to place: {comp_ids}"""

    # response = client.models.generate_content(
    #     model="gemini-2.5-flash",
    #     contents=prompt
    # )
    # text = response.text.strip()
    text = """{"NUCLEO": [101, 50], "HEX_N": [50, 80], "HEX_NE": [76, 65], "HEX_SE": [76, 35], "HEX_S": [50, 20], "HEX_SW": [24, 35], "HEX_NW": [24, 65]}"""
    if text.startswith("```"):
        text = "\n".join(text.splitlines()[1:-1])

    try:
        raw = json.loads(text)
        return {k: (float(v[0]), float(v[1])) for k, v in raw.items()}
    except Exception as e:
        print(f"  WARNING: LLM placement parse failed ({e}), falling back to default hex layout")
        return _default_hex_placement(components)


def _default_hex_placement(components: list[dict]) -> dict[str, tuple[float, float]]:
    """Fallback: deterministic hex layout if LLM fails."""
    HEX_ORDER = _HEX_MIC_IDS
    ANGLES    = [90,       30,        -30,       -90,      -150,      150]
    CENTER = (50.0, 50.0)
    RADIUS = 30.0
    MCU_POS = (120.0, 50.0)

    positions: dict[str, tuple[float, float]] = {}
    for comp in components:
        cid = comp["id"]
        if cid in HEX_ORDER:
            idx = HEX_ORDER.index(cid)
            rad = math.radians(ANGLES[idx])
            x = CENTER[0] + RADIUS * math.cos(rad)
            y = CENTER[1] - RADIUS * math.sin(rad)  # KiCad Y is flipped
            positions[cid] = (round(x, 3), round(y, 3))
        else:
            # MCU or unknown — place at MCU_POS
            positions[cid] = MCU_POS

    return positions


# ── Net index helpers ─────────────────────────────────────────────────────────

def _build_net_index(nets: list[dict]) -> dict[str, int]:
    """Returns {net_name: net_code} (1-indexed)."""
    return {net["name"]: i + 1 for i, net in enumerate(nets)}


def _pad_net(comp_id: str, pin_name: str, nets: list[dict]) -> tuple[str, int]:
    """Given a comp.pin string, find the net name and code it belongs to."""
    node_str = f"{comp_id}.{pin_name}"
    for i, net in enumerate(nets):
        if node_str in net.get("connections", []):
            return net["name"], i + 1
    return "", 0


def _emit_all_pads(
    lines:     list[str],
    hw:        str,
    pins:      dict[str, str],
    net_index: dict[str, int],
) -> None:
    """
    Emit EVERY physical pad of the footprint — connected and unconnected.

    Connected pads carry their net assignment; unconnected pads are written
    bare so the full 144-pin LQFP ring or 4-pin LGA grid renders in KiCad
    instead of just the handful of actively-wired GPIO pins.
    """
    total = 144 if hw in _LQFP_MODELS else 4

    # Build pad_number_str → net_name from the component's connected pins
    pad_to_net: dict[str, str] = {}
    for pin_name, net_name in pins.items():
        pad_str = _resolve_pin(hw, pin_name)
        if pad_str.isdigit():
            pad_to_net[pad_str] = net_name

    for pad_num in range(1, total + 1):
        pad_str  = str(pad_num)
        net_name = pad_to_net.get(pad_str, "")
        net_code = net_index.get(net_name, 0) if net_name else 0

        px, py       = _pad_xy(hw, pad_num)
        pw, ph, prot = _pad_size_rot(hw, pad_num)
        rot_str      = f" {prot}" if prot else ""

        lines.append(f'    (pad "{pad_str}" smd rect (at {px} {py}{rot_str}) (size {pw} {ph}) (layers "F.Cu" "F.Paste" "F.Mask")')
        if net_code:
            lines.append(f'      (net {net_code} "{net_name}")')
        lines.append(f'    )')


# ── .kicad_pcb writer ────────────────────────────────────────────────────────

def generate_kicad_pcb(
    netlist: dict,
    cv_result: dict,
    output_file: str = "circuit.kicad_pcb",
) -> None:
    components = netlist["components"]
    nets = netlist["nets"]

    hw_by_id = {c["id"]: c.get("hardware_model", c.get("type", "")) for c in components}
    net_index = _build_net_index(nets)  # {name: code}

    # ── 1. Infer positions ───────────────────────────────────────────────────
    print("Inferring component placement from CV description...")
    positions = infer_placement(cv_result, components)

    # ── 2. Board outline ────────────────────────────────────────────────────
    # Compute bounding box of all positions + 15mm margin
    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    margin = 15.0
    x_min, x_max = min(xs) - margin, max(xs) + margin
    y_min, y_max = min(ys) - margin, max(ys) + margin

    lines: list[str] = []

    # ── 3. File header ───────────────────────────────────────────────────────
    lines.append('(kicad_pcb (version 20221018) (generator pcbnew)')
    lines.append('')
    lines.append('  (general')
    lines.append('    (thickness 1.6)')
    lines.append('  )')
    lines.append('')
    lines.append('  (paper "A4")')
    lines.append('')

    # ── 4. Layers ────────────────────────────────────────────────────────────
    lines.append('  (layers')
    for num, name, ltype in [
        (0,  "F.Cu",      "signal"),
        (31, "B.Cu",      "signal"),
        (32, "B.Adhes",   "user"),
        (33, "F.Adhes",   "user"),
        (34, "B.Paste",   "user"),
        (35, "F.Paste",   "user"),
        (36, "B.SilkS",   "user"),
        (37, "F.SilkS",   "user"),
        (38, "B.Mask",    "user"),
        (39, "F.Mask",    "user"),
        (44, "Edge.Cuts", "user"),
        (45, "Margin",    "user"),
        (46, "B.CrtYd",  "user"),
        (47, "F.CrtYd",  "user"),
        (48, "B.Fab",    "user"),
        (49, "F.Fab",    "user"),
    ]:
        lines.append(f'    ({num} "{name}" {ltype})')
    lines.append('  )')
    lines.append('')

    # ── 5. Net declarations ──────────────────────────────────────────────────
    lines.append('  (net 0 "")')
    for net in nets:
        code = net_index[net["name"]]
        lines.append(f'  (net {code} "{net["name"]}")')
    lines.append('')

    # ── 6. Footprints ────────────────────────────────────────────────────────
    for comp in components:
        cid   = comp["id"]
        hw    = hw_by_id[cid]
        fp    = FOOTPRINT_MAP.get(hw, "")
        pins  = comp.get("pins", {})
        x, y  = positions.get(cid, (50.0, 50.0))

        if not fp:
            print(f"  WARNING: no footprint for {cid} ({hw}), skipping")
            continue

        if cid in _HEX_MIC_IDS:
            rotation = _HEX_MIC_IDS.index(cid) * 60
            at_str = f'{x} {y} {rotation}'
        else:
            at_str = f'{x} {y}'

        lines.append(f'  (footprint "{fp}"')
        lines.append(f'    (layer "F.Cu")')
        lines.append(f'    (at {at_str})')
        lines.append(f'    (property "Reference" "{cid}" (at 0 -3) (layer "F.SilkS"))')
        lines.append(f'    (property "Value" "{hw}" (at 0 3) (layer "F.Fab"))')

        # Chip outline graphics (silkscreen, courtyard, fab layer)
        _emit_fp_graphics(lines, hw)

        # All physical pads — full 144-pin LQFP ring or 4-pin LGA grid.
        # Connected pads carry their net; unconnected pads are bare.
        _emit_all_pads(lines, hw, pins, net_index)

        lines.append('  )')
        lines.append('')

    # ── 7. Board outline (Edge.Cuts) ─────────────────────────────────────────
    # Rectangle drawn as 4 line segments
    corners = [
        (x_min, y_min), (x_max, y_min),
        (x_max, y_max), (x_min, y_max),
    ]
    for i in range(4):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % 4]
        lines.append(f'  (gr_line (start {x1} {y1}) (end {x2} {y2}) (layer "Edge.Cuts") (width 0.05))')

    lines.append('')
    lines.append(')')  # close kicad_pcb

    Path(output_file).write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated: {output_file}")


# ── Hex mic array — circuit builder, netlist writer, public API ───────────────

def _build_hex_circuit() -> dict:
    """Build the hex mic array circuit dict (NUCLEO + 6 Adafruit 4346 mics)."""
    components: list[dict] = []
    nets_acc: dict[str, list[str]] = {}

    def wire(comp_id: str, pin: str, net: str) -> None:
        nets_acc.setdefault(net, []).append(f"{comp_id}.{pin}")

    mcu_pins: dict[str, str] = {}
    for mcu_pin, net_name in [("3V3", "VCC_3V3"), ("GND", "GND"), ("PE9", "DFSDM1_CKOUT")]:
        mcu_pins[mcu_pin] = net_name
        wire("NUCLEO", mcu_pin, net_name)
    for i, dat_pin in enumerate(_HEX_DAT_PINS):
        net_name = f"DFSDM1_DATIN{i}"
        mcu_pins[dat_pin] = net_name
        wire("NUCLEO", dat_pin, net_name)
    components.append({
        "id": "NUCLEO", "type": "MCU_BOARD",
        "hardware_model": "NUCLEO-H7A3ZI-Q", "pins": mcu_pins,
    })

    for i, mic_id in enumerate(_HEX_MIC_IDS):
        dat_net = f"DFSDM1_DATIN{i}"
        mic_pins: dict[str, str] = {
            "VDD": "VCC_3V3", "GND": "GND", "CLK": "DFSDM1_CKOUT", "DAT": dat_net,
        }
        for pin, net_name in mic_pins.items():
            wire(mic_id, pin, net_name)
        components.append({
            "id": mic_id, "type": "MICROPHONE",
            "hardware_model": "Adafruit 4346 PDM Microphone", "pins": mic_pins,
        })

    nets = [{"name": name, "connections": conns} for name, conns in nets_acc.items()]
    return {"components": components, "nets": nets}


def _write_hex_netlist(circuit: dict, output_path: str) -> None:
    """Write a KiCad .net file for the hex mic circuit."""
    hw_by_id = {c["id"]: c["hardware_model"] for c in circuit["components"]}
    lines: list[str] = ["(export (version D)"]
    lines.append("  (components")
    for comp in circuit["components"]:
        hw = comp["hardware_model"]
        fp = FOOTPRINT_MAP.get(hw, "")
        lines.append(f'    (comp (ref "{comp["id"]}")')
        lines.append(f'      (value "{hw}")')
        lines.append(f'      (footprint "{fp}")')
        lines.append( '    )')
    lines.append("  )")
    lines.append("  (nets")
    for i, net in enumerate(circuit["nets"]):
        lines.append(f'    (net (code "{i + 1}") (name "{net["name"]}")')
        for node in net["connections"]:
            comp_id, pin_name = node.split(".", 1)
            hw  = hw_by_id.get(comp_id, "")
            pad = _resolve_pin(hw, pin_name)
            lines.append(f'      (node (ref "{comp_id}") (pin "{pad}"))')
        lines.append('    )')
    lines.append("  )")
    lines.append(")")
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")


def generate_hex_mic_board(
    output_dir: str = "schematics",
    uid: str | None = None,
) -> tuple[str, str]:
    """
    Full pipeline for the hex mic array: build circuit → write .net → write .kicad_pcb.

    Returns (net_path, pcb_path) as absolute paths.
    Placement uses the hardcoded positions from infer_placement().
    """
    import uuid as _uuid
    os.makedirs(output_dir, exist_ok=True)
    suffix   = uid or _uuid.uuid4().hex[:8]
    net_path = os.path.join(output_dir, f"hex_mic_{suffix}.net")
    pcb_path = os.path.join(output_dir, f"hex_mic_{suffix}.kicad_pcb")
    circuit  = _build_hex_circuit()
    _write_hex_netlist(circuit, net_path)
    generate_kicad_pcb(circuit, {}, output_file=pcb_path)
    return (os.path.abspath(net_path), os.path.abspath(pcb_path))


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from schematic_generator import simplify_to_production

    netlist_file = sys.argv[1] if len(sys.argv) > 1 else "test_netlist.json"
    cv_file      = sys.argv[2] if len(sys.argv) > 2 else "test_cv.json"

    with open(netlist_file) as f:
        raw_netlist = json.load(f)
    with open(cv_file) as f:
        cv_result = json.load(f)

    production_netlist = simplify_to_production(raw_netlist)
    generate_kicad_pcb(production_netlist, cv_result)