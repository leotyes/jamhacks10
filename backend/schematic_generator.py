import json
from pathlib import Path
from google import genai
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))

FOOTPRINT_MAP = {
    "STM32H7A3ZIT6Q":               "Package_QFP:LQFP-144_20x20mm_P0.5mm",
    "NUCLEO-H7A3ZI-Q":              "Package_QFP:LQFP-144_20x20mm_P0.5mm",
    # Only LGA footprint present in this KiCad install is VLGA-4_2x2.5mm_P1.65mm.
    # Pad pitch is slightly off from the MP34DT01-M datasheet (1mm vs 1.65mm) —
    # acceptable for a hackathon; replace with a custom footprint before fab.
    "MP34DT01-M":                   "Package_LGA:VLGA-4_2x2.5mm_P1.65mm",
    "Adafruit 4346 PDM Microphone": "Package_LGA:VLGA-4_2x2.5mm_P1.65mm",
}

# STM32H7A3ZIT6Q LQFP-144 GPIO → physical pin number mapping.
# KiCad's LQFP-144 footprint uses numeric pad numbers (1-144), not GPIO names.
# Source: STM32H7A3ZIT6Q datasheet Table 9, LQFP144 pinout.
STM32H7A3ZIT6Q_PIN_MAP: dict[str, str] = {
    "VBAT":      "1",
    "PC13":      "2",
    "PC14":      "3",
    "PC15":      "4",
    "PH0":       "5",
    "PH1":       "6",
    "NRST":      "7",
    "PC0":       "8",
    "PC1":       "9",
    "PC2":       "10",
    "PC3":       "11",
    "VSSA":      "12",
    "VDDA":      "13",
    "PA0":       "14",
    "PA1":       "15",
    "PA2":       "16",
    "PA3":       "17",
    "VSS":       "18",
    "VDD":       "19",
    "PA4":       "20",
    "PA5":       "21",
    "PA6":       "22",
    "PA7":       "23",
    "PC4":       "24",
    "PC5":       "25",
    "PB0":       "26",
    "PB1":       "27",
    "PB2":       "28",
    "PE7":       "29",
    "PE8":       "30",
    "PE9":       "31",
    "PE10":      "32",
    "PE11":      "33",
    "PE12":      "34",
    "PE13":      "35",
    "PE14":      "36",
    "PE15":      "37",
    "PB10":      "38",
    "PB11":      "39",
    "VCAP":      "40",
    "PB12":      "41",
    "PB13":      "42",
    "PB14":      "43",
    "PB15":      "44",
    "PD8":       "45",
    "PD9":       "46",
    "PD10":      "47",
    "PD11":      "48",
    "PD12":      "49",
    "PD13":      "50",
    "PD14":      "51",
    "PD15":      "52",
    "PC6":       "53",
    "PC7":       "54",
    "PC8":       "55",
    "PC9":       "56",
    "PA8":       "57",
    "PA9":       "58",
    "PA10":      "59",
    "PA11":      "60",
    "PA12":      "61",
    "PA13":      "62",
    "VDD_2":     "63",
    "VSS_2":     "64",
    "PA14":      "65",
    "PA15":      "66",
    "PC10":      "67",
    "PC11":      "68",
    "PC12":      "69",
    "PD0":       "70",
    "PD1":       "71",
    "PD2":       "72",
    "PD3":       "73",
    "PD4":       "74",
    "PD5":       "75",
    "PD6":       "76",
    "PD7":       "77",
    "PB3":       "78",
    "PB4":       "79",
    "PB5":       "80",
    "PB6":       "81",
    "PB7":       "82",
    "BOOT0":     "83",
    "PB8":       "84",
    "PB9":       "85",
    "PE0":       "86",
    "PE1":       "87",
    "VSS_3":     "88",
    "VDD_3":     "89",
    "PE2":       "90",
    "PE3":       "91",
    "PE4":       "92",
    "PE5":       "93",
    "PE6":       "94",
    "VBAT_2":    "95",
    "PI8":       "96",
    "PC13_2":    "97",
    "PI9":       "98",
    "PI10":      "99",
    "PI11":      "100",
    "PH2":       "101",
    "PH3":       "102",
    "PH4":       "103",
    "PH5":       "104",
    "PH6":       "105",
    "PH7":       "106",
    "PH8":       "107",
    "PH9":       "108",
    "PH10":      "109",
    "PH11":      "110",
    "PH12":      "111",
    "VDD_4":     "112",
    "VSS_4":     "113",
    "PH13":      "114",
    "PH14":      "115",
    "PH15":      "116",
    "PI0":       "117",
    "PI1":       "118",
    "PI2":       "119",
    "PI3":       "120",
    "PI4":       "121",
    "PI5":       "122",
    "PI6":       "123",
    "PI7":       "124",
    "VDD_5":     "125",
    "VSS_5":     "126",
    "PF0":       "127",
    "PF1":       "128",
    "PF2":       "129",
    "PF3":       "130",
    "PF4":       "131",
    "PF5":       "132",
    "VDD_6":     "133",
    "VSS_6":     "134",
    "PF6":       "135",
    "PF7":       "136",
    "PF8":       "137",
    "PF9":       "138",
    "PF10":      "139",
    "PG0":       "140",
    "PG1":       "141",
    "PE7_2":     "142",
    "PE8_2":     "143",
    "VSS_7":     "144",
}

# Plain GPIO aliases always win — these are the names the LLM will actually emit
_GPIO_ALIASES: dict[str, str] = {
    "PC1":  "9",
    "PC3":  "11",
    "PC5":  "25",
    "PE4":  "92",
    "PE9":  "31",
    "PE10": "32",
    "PE12": "34",
    "VDD":  "19",
    "VSS":  "18",
    "GND":  "18",
}
STM32H7A3ZIT6Q_PIN_MAP.update(_GPIO_ALIASES)

# MP34DT01-M pad numbering for VLGA-4_2x2.5mm_P1.65mm footprint
MP34DT01M_PIN_MAP: dict[str, str] = {
    "VDD":  "1",
    "GND":  "2",
    "CLK":  "3",
    "DOUT": "4",
}

# Which hardware models need pin name → pad number translation
_PIN_LOOKUP: dict[str, dict[str, str]] = {
    "STM32H7A3ZIT6Q": STM32H7A3ZIT6Q_PIN_MAP,
    "MP34DT01-M":     MP34DT01M_PIN_MAP,
}


def _resolve_pin(hardware_model: str, pin_name: str) -> str:
    """Return the physical pad number for a pin name, or the name itself if not mapped."""
    lookup = _PIN_LOOKUP.get(hardware_model)
    if lookup is None:
        return pin_name
    resolved = lookup.get(pin_name)
    if resolved is None:
        print(f"  WARNING: no pad mapping for {hardware_model} pin '{pin_name}' — left as-is")
        return pin_name
    return resolved


def simplify_to_production(netlist: dict) -> dict:
    prompt = f"""You are a hardware engineer converting a prototype netlist to a production-ready netlist.

Replace any development board or breakout board components with their bare IC equivalents:
- Any STM32 Nucleo board → bare STM32H7A3ZIT6Q as an example of a chip, based on the Nucleo board choose the corresponding MCU. Keep all the same GPIO pin names (PC1, PE9, etc), just change the component id to "U1", type to "MCU", hardware_model to "STM32H7A3ZIT6Q" or whatever the corresponding chip is.
- Any Adafruit PDM microphone breakout → bare MP34DT01-M IC. Rename pin "DAT" to "DOUT". Keep VDD, GND, CLK the same. Update hardware_model to "MP34DT01-M".
- Preserve all net names and connectivity exactly — only component metadata and pin names change.
- Update all net connections to reflect any renamed pins.

Return ONLY valid JSON with the same schema (components, nets, notes). No markdown fences, no explanation.

Input netlist:
{json.dumps(netlist, indent=2)}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    text = response.text.strip()
    if "```" in text:
        text = text.split("```")[1].replace("json", "", 1).strip()
    return json.loads(text)


def generate_netlist(netlist: dict, output_file: str = "circuit.net") -> None:
    components = netlist["components"]
    nets = netlist["nets"]

    # comp-id → hardware_model lookup for pin resolution
    hw_by_id: dict[str, str] = {
        c["id"]: c.get("hardware_model", c.get("type", ""))
        for c in components
    }

    lines: list[str] = []
    lines.append("(export (version D)")

    lines.append("  (components")
    for comp in components:
        cid = comp["id"]
        hw = comp.get("hardware_model", comp.get("type", "UNKNOWN"))
        footprint = FOOTPRINT_MAP.get(hw, "")
        if not footprint:
            print(f"  WARNING: no footprint mapped for hardware_model '{hw}' (comp {cid})")
        lines.append(f'    (comp (ref "{cid}")')
        lines.append(f'      (value "{hw}")')
        lines.append(f'      (footprint "{footprint}")')
        lines.append(f'    )')
    lines.append("  )")

    lines.append("  (nets")
    for i, net in enumerate(nets):
        net_name = net.get("name", net.get("id", f"NET{i}"))
        connections = net.get("connections", net.get("nodes", []))
        lines.append(f'    (net (code "{i+1}") (name "{net_name}")')
        for node in connections:
            parts = node.split(".", 1)
            if len(parts) == 2:
                cid, pin_name = parts
                hw = hw_by_id.get(cid, "")
                physical_pin = _resolve_pin(hw, pin_name)
                lines.append(f'      (node (ref "{cid}") (pin "{physical_pin}"))')
        lines.append(f'    )')
    lines.append("  )")
    lines.append(")")

    Path(output_file).write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated: {output_file}")


if __name__ == "__main__":
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else "test_netlist.json"
    with open(input_file) as f:
        netlist = json.load(f)
    production_netlist = simplify_to_production(netlist)
    generate_netlist(production_netlist)