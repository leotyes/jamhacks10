from skidl import *

# Kicad location/get all the components
set_default_tool(KICAD6)
lib_search_paths[KICAD6] = ['D:/Kicad/share/kicad/symbols']

# Create two components
r = Part('Device', 'R', footprint='Resistor_SMD:R_0805_2012Metric')
led = Part('Device', 'LED', footprint='LED_SMD:LED_0805_2012Metric')

# Connect resistor pin 1 to LED anode
r[1] += led['A']

# Export netlist
generate_netlist()