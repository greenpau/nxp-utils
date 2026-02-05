from typing import Dict, Any, List
from logging import Logger
from .pin_entry import PinEntry
from .generate_pinctrl_entry import generate_pinctrl_entry
from .generate_gpio_logic_nodes import generate_gpio_logic_nodes
from .parse_peripheral_groups import parse_peripheral_groups
from .generate_node_uart import generate_uart_node
from .generate_node_i2s import generate_i2s_node


def generate_board_dtsi(board_config: dict, signal_to_pin_map: Dict[str, Any], log=Logger) -> str:
    """
    Generates a full DTSI content including pinctrl and functional GPIO nodes.
    """
    dtsi_content = []

    # First, parse the raw data into organized groups of PinEntry objects
    # This centralizes the lookup logic so you only do it once.
    peripheral_groups = parse_peripheral_groups(board_config, signal_to_pin_map, log)

    # Build the Pinctrl section. This defines the "Hardware Wiring".
    dtsi_content.append("&pinctrl {")
    for peri_id, pins in peripheral_groups.items():
        node_name = f"{peri_id.lower()}_default"
        dtsi_content.append(generate_pinctrl_entry(node_name, pins))
    dtsi_content.append("};\n")

    # Build the GPIO Functional section (LEDs/Buttons). This defines the "Software Logic" (Init states, Interrupts).
    # Flatten the peripheral_groups list to give the GPIO generator all pins at once.
    all_pins: List[PinEntry] = []
    for pins in peripheral_groups.values():
        all_pins.extend(pins)
    gpio_logic = generate_gpio_logic_nodes(all_pins)
    dtsi_content.append(gpio_logic)

    # Generate Peripheral Nodes (I2S, UART, etc.)
    for peri_id, pins in peripheral_groups.items():
        if "I2S" in peri_id:
            dtsi_content.append(generate_i2s_node(peri_id, pins))
        elif "UART" in peri_id:
            dtsi_content.append(generate_uart_node(peri_id, pins))

    return "\n".join(dtsi_content)
