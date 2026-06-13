import json
from skidl import *

set_default_tool(KICAD6)
lib_search_paths[KICAD6] = ['D:/Kicad/share/kicad/symbols']

COMPONENT_DEFS = {
    "LED":      {"lib": "Device", "part": "LED",       "footprint": "LED_SMD:LED_0805_2012Metric"},
    "Resistor": {"lib": "Device", "part": "R",         "footprint": "Resistor_SMD:R_0805_2012Metric"},
    "Battery":  {"lib": "Device", "part": "Battery",   "footprint": "Battery:BatteryHolder_Keystone_1042_1x12mm"},
    "NPN":      {"lib": "Device", "part": "Q_NPN",     "footprint": "Package_TO_SOT_THT:TO-92_Inline"},
    "Capacitor":{"lib": "Device", "part": "C",         "footprint": "Capacitor_SMD:C_0805_2012Metric"},
    "Switch":   {"lib": "Device", "part": "SW_Push",   "footprint": "Button_Switch_THT:SW_PUSH_6mm"},
}

PIN_ALIASES = {
    "LED":      {"anode": "A", "a": "A", "cathode": "K", "k": "K"},
    "Resistor": {"pin1": "1", "1": "1", "pin2": "2", "2": "2"},
    "Battery":  {"positive": "+", "plus": "+", "+": "+", "negative": "-", "minus": "-", "-": "-"},
    "NPN":      {"base": "B", "b": "B", "collector": "C", "c": "C", "emitter": "E", "e": "E"},
    "Capacitor":{"pin1": "1", "1": "1", "pin2": "2", "2": "2"},
    "Switch":   {"pin1": "1", "1": "1", "pin2": "2", "2": "2"},
}


def base_type(comp_name):
    stripped = comp_name.rstrip("0123456789").rstrip("_")
    return stripped if stripped in COMPONENT_DEFS else comp_name


def generate_schematic(netlist, output_file="schematic_generator.net"):
    reset()

    instances = {}
    for comp_name in netlist["components"]:
        t = base_type(comp_name)
        defn = COMPONENT_DEFS[t]
        instances[comp_name] = Part(defn["lib"], defn["part"], footprint=defn["footprint"])

    endpoint_to_net = {}
    wired = set()

    for conn in netlist["connections"]:
        from_ep, to_ep = conn["from"], conn["to"]
        from_net = endpoint_to_net.get(from_ep)
        to_net   = endpoint_to_net.get(to_ep)

        if from_net and to_net and from_net is not to_net:
            from_net += to_net
            for ep, n in endpoint_to_net.items():
                if n is to_net:
                    endpoint_to_net[ep] = from_net
            net = from_net
        else:
            net = from_net or to_net or Net(f"NET_{from_ep.replace('.','_')}")

        endpoint_to_net[from_ep] = net
        endpoint_to_net[to_ep]   = net

        for ep in (from_ep, to_ep):
            if ep in wired:
                continue
            comp_name, pin_alias = ep.split(".", 1)
            t = base_type(comp_name)
            pin_id = PIN_ALIASES[t][pin_alias.lower()]
            net += instances[comp_name][pin_id]
            wired.add(ep)

    generate_netlist(file_=output_file)
    print(f"Generated: {output_file}")


if __name__ == "__main__":
    with open("test_netlist.json") as f:
        netlist = json.load(f)
    generate_schematic(netlist)
