import json
import uuid
from pathlib import Path

KICAD_SYMBOLS_DIR = "D:/Kicad/share/kicad/symbols"

COMPONENT_DEFS = {
    "LED":      {"lib": "Device", "part": "LED",      "ref_prefix": "D"},
    "Resistor": {"lib": "Device", "part": "R",        "ref_prefix": "R"},
    "Battery":  {"lib": "Device", "part": "Battery",  "ref_prefix": "BT"},
    "NPN":      {"lib": "Device", "part": "Q_NPN",    "ref_prefix": "Q"},
    "Capacitor":{"lib": "Device", "part": "C",        "ref_prefix": "C"},
    "Switch":   {"lib": "Device", "part": "SW_Push",  "ref_prefix": "SW"},
}

# Maps user-facing pin names → KiCad pin numbers in the .kicad_sym file
PIN_ALIASES = {
    "LED":      {"anode": "2", "a": "2", "A": "2", "cathode": "1", "k": "1", "K": "1"},
    "Resistor": {"pin1": "1", "1": "1", "pin2": "2", "2": "2"},
    "Battery":  {"positive": "1", "plus": "1", "+": "1", "1": "1",
                 "negative": "2", "minus": "2", "-": "2", "2": "2"},
    "NPN":      {"base": "B", "b": "B", "B": "B",
                 "collector": "C", "c": "C", "C": "C",
                 "emitter": "E", "e": "E", "E": "E"},
    "Capacitor":{"pin1": "1", "1": "1", "pin2": "2", "2": "2"},
    "Switch":   {"pin1": "1", "1": "1", "pin2": "2", "2": "2"},
}

# Pin XY offsets from component origin, extracted from Device.kicad_sym
PIN_POSITIONS = {
    "LED":       {"1": (-3.81, 0.0),  "2": (3.81, 0.0)},
    "Resistor":  {"1": (0.0, 3.81),   "2": (0.0, -3.81)},
    "Battery":   {"1": (0.0, 5.08),   "2": (0.0, -5.08)},
    "NPN":       {"B": (-5.08, 0.0),  "C": (2.54, 5.08), "E": (2.54, -5.08)},
    "Capacitor": {"1": (0.0, 3.81),   "2": (0.0, -3.81)},
    "Switch":    {"1": (-3.81, 0.0),  "2": (3.81, 0.0)},
}


def gen_uuid():
    return str(uuid.uuid4())


def extract_symbol(lib_name, part_name):
    """Extract one symbol definition from a .kicad_sym library file."""
    lib_path = Path(KICAD_SYMBOLS_DIR) / f"{lib_name}.kicad_sym"
    content = lib_path.read_text(encoding="utf-8")
    search = f'\t(symbol "{part_name}"'
    idx = content.find(search)
    if idx == -1:
        return None
    depth = 0
    for i, c in enumerate(content[idx:]):
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return content[idx : idx + i + 1]


def base_type(comp_name):
    stripped = comp_name.rstrip("0123456789").rstrip("_")
    return stripped if stripped in COMPONENT_DEFS else comp_name


def normalize_netlist(netlist):
    """Convert our test format (components as strings + connections) to
    the team format (components as {id,type} objects + nets with nodes).
    If the netlist already uses the team format, return it unchanged."""
    if "nets" in netlist:
        return netlist

    ref_counters = {}
    comp_map = {}
    components = []
    for name in netlist["components"]:
        t = base_type(name)
        prefix = COMPONENT_DEFS[t]["ref_prefix"]
        ref_counters[prefix] = ref_counters.get(prefix, 0) + 1
        comp_id = f"{prefix}{ref_counters[prefix]}"
        comp_map[name] = comp_id
        components.append({"id": comp_id, "type": t})

    node_to_net = {}
    nets_dict = {}
    net_counter = [0]

    def get_or_create(node):
        if node not in node_to_net:
            net_counter[0] += 1
            nid = f"N{net_counter[0]}"
            node_to_net[node] = nid
            nets_dict[nid] = [node]
        return node_to_net[node]

    def merge(a, b):
        if a == b:
            return a
        for node in nets_dict[b]:
            node_to_net[node] = a
            nets_dict[a].append(node)
        del nets_dict[b]
        return a

    for conn in netlist["connections"]:
        fc, fa = conn["from"].split(".", 1)
        tc, ta = conn["to"].split(".", 1)
        ft = base_type(fc)
        tt = base_type(tc)
        fp = PIN_ALIASES[ft].get(fa, fa)
        tp = PIN_ALIASES[tt].get(ta, ta)
        merge(get_or_create(f"{comp_map[fc]}.{fp}"), get_or_create(f"{comp_map[tc]}.{tp}"))

    nets = [{"id": k, "nodes": v} for k, v in nets_dict.items()]
    return {"components": components, "nets": nets}


def generate_schematic(netlist, output_file="circuit.kicad_sch"):
    netlist = normalize_netlist(netlist)
    comp_types = {c["id"]: c["type"] for c in netlist["components"]}

    # Extract and rename symbol definitions from the KiCad library
    lib_symbols = {}
    for comp in netlist["components"]:
        t = comp["type"]
        if t not in COMPONENT_DEFS:
            continue
        defn = COMPONENT_DEFS[t]
        lib_id = f"{defn['lib']}:{defn['part']}"
        if lib_id not in lib_symbols:
            sym = extract_symbol(defn["lib"], defn["part"])
            if sym is None:
                continue
            # Only rename the top-level symbol name; subsymbols keep their original names
            sym = sym.replace(f'\t(symbol "{defn["part"]}"', f'\t\t(symbol "{lib_id}"', 1)
            lib_symbols[lib_id] = sym

    # Place components on a grid (3 columns, 50 mm spacing)
    COLS, SPACING = 3, 50.0
    OX, OY = 50.0, 50.0
    known = [c for c in netlist["components"] if c["type"] in COMPONENT_DEFS]
    positions = {}
    for i, comp in enumerate(known):
        positions[comp["id"]] = (OX + (i % COLS) * SPACING, OY + (i // COLS) * SPACING)

    # Build symbol instance blocks
    symbol_blocks = []
    for comp in known:
        cid, t = comp["id"], comp["type"]
        defn = COMPONENT_DEFS[t]
        lib_id = f"{defn['lib']}:{defn['part']}"
        if lib_id not in lib_symbols:
            continue
        x, y = positions[cid]
        pin_lines = "\n".join(
            f'    (pin "{p}" (uuid "{gen_uuid()}"))'
            for p in PIN_POSITIONS.get(t, {})
        )
        symbol_blocks.append(
            f'  (symbol (lib_id "{lib_id}") (at {x} {y} 0) (unit 1)\n'
            f'    (in_bom yes) (on_board yes) (dnp no)\n'
            f'    (uuid "{gen_uuid()}")\n'
            f'    (property "Reference" "{cid}" (at {x+2} {y-2} 0)\n'
            f'      (effects (font (size 1.27 1.27)))\n'
            f'    )\n'
            f'    (property "Value" "{t}" (at {x+2} {y+2} 0)\n'
            f'      (effects (font (size 1.27 1.27)))\n'
            f'    )\n'
            f'{pin_lines}\n'
            f'  )'
        )

    # Build net label blocks (one label per pin per net)
    label_blocks = []
    for net in netlist["nets"]:
        nid = net["id"]
        for node in net["nodes"]:
            cid, pin_ref = node.split(".", 1)
            t = comp_types.get(cid)
            if not t or t not in COMPONENT_DEFS or cid not in positions:
                continue
            pin_num = PIN_ALIASES.get(t, {}).get(pin_ref, pin_ref)
            pin_pos = PIN_POSITIONS.get(t, {})
            if pin_num not in pin_pos:
                continue
            cx, cy = positions[cid]
            dx, dy = pin_pos[pin_num]
            if dx != 0 or dy != 0:
                mag = (dx**2 + dy**2) ** 0.5
                lx = cx + dx + (dx / mag) * 2.0
                ly = cy + dy + (dy / mag) * 2.0
            else:
                lx, ly = cx + dx, cy + dy
            label_blocks.append(
                f'  (label "{nid}" (at {lx} {ly} 0)\n'
                f'    (effects (font (size 1.27 1.27)) (justify left bottom))\n'
                f'    (uuid "{gen_uuid()}")\n'
                f'  )'
            )

    schematic = (
        f'(kicad_sch\n'
        f'  (version 20250114)\n'
        f'  (generator "schematic_generator")\n'
        f'  (generator_version "1.0")\n'
        f'  (uuid "{gen_uuid()}")\n'
        f'  (paper "A4")\n'
        f'  (lib_symbols\n'
        + "\n".join(lib_symbols.values()) + "\n"
        f'  )\n'
        + "\n".join(symbol_blocks) + "\n"
        + "\n".join(label_blocks) + "\n"
        f')\n'
    )

    Path(output_file).write_text(schematic, encoding="utf-8")
    print(f"Generated: {output_file}")


if __name__ == "__main__":
    with open("test_netlist.json") as f:
        netlist = json.load(f)
    generate_schematic(netlist)
